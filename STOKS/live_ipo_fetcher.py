"""
STOKS Live IPO Universe Fetcher V2.0
Fetches BSE Main Board + NSE Main Board IPOs (2022-present) from the internet.

Sources (in priority order):
  1. NSE Archives EQUITY_L.csv  — NSE listed securities with listing date (official)
  2. Chittorgarh.com            — BSE+NSE main board IPO list with issue price
  3. Excel File                 — Emergency local fallback

Cache: 24h local JSON to avoid repeat scraping on the same day.
"""
import requests
import json
import os
import re
import io
import time
import datetime
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

from config import BASE_DIR, CACHE_DIR, EXCEL_IPO_FILE, IPO_START_DATE

CACHE_FILE = os.path.join(CACHE_DIR, "ipo_universe_cache.json")
CACHE_TTL_HOURS = 24

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


# ─────────────────────────────────────────────────────────────────────────────
# Cache Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        mtime = os.path.getmtime(CACHE_FILE)
        age_h = (time.time() - mtime) / 3600
        if age_h > CACHE_TTL_HOURS:
            print(f"[LiveIPO] Cache expired ({age_h:.1f}h old). Refreshing from internet...")
            return None
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[LiveIPO] Cache hit: {len(data)} IPOs ({age_h:.1f}h old). Skipping web scrape.")
        return data
    except Exception as e:
        print(f"[LiveIPO] Cache read error: {e}")
        return None


def _save_cache(data):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        print(f"[LiveIPO] Saved {len(data)} IPOs to 24h cache.")
    except Exception as e:
        print(f"[LiveIPO] Cache save error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Source 1: NSE Archives — EQUITY_L.csv (Official NSE Listed Securities)
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_nse_equity_list():
    """
    Download NSE EQUITY_L.csv — contains all NSE-listed stocks with:
    SYMBOL, NAME OF COMPANY, DATE OF LISTING, ISIN NUMBER, etc.
    Filter by DATE OF LISTING >= IPO_START_DATE for Main Board IPOs.
    Returns list of {name, listing_date, ticker, exchange}
    """
    url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"[LiveIPO] NSE EQUITY_L.csv: HTTP {resp.status_code}")
            return []

        df = pd.read_csv(io.StringIO(resp.text))
        df.columns = [c.strip().upper() for c in df.columns]

        # Find the date column (various possible names)
        date_col = None
        for possible in ["DATE OF LISTING", "LISTING DATE", "DATE_OF_LISTING", "LISTINGDATE"]:
            if possible in df.columns:
                date_col = possible
                break

        # Find symbol and name columns
        sym_col  = next((c for c in df.columns if "SYMBOL" in c), None)
        name_col = next((c for c in df.columns if "NAME" in c or "COMPANY" in c), None)

        if not date_col or not sym_col:
            print(f"[LiveIPO] NSE CSV columns: {df.columns.tolist()}")
            print("[LiveIPO] NSE CSV: could not find required columns")
            return []

        df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
        start_dt = pd.to_datetime(IPO_START_DATE)
        end_dt   = pd.Timestamp.now()

        filtered = df[(df[date_col] >= start_dt) & (df[date_col] <= end_dt)].dropna(subset=[date_col])

        for _, row in filtered.iterrows():
            symbol = str(row[sym_col]).strip()
            name   = str(row[name_col]).strip() if name_col else symbol
            l_date = row[date_col].strftime("%Y-%m-%d")
            if symbol and symbol != "nan":
                ticker = symbol + ".NS"
                results.append({
                    "name":         name,
                    "listing_date": l_date,
                    "ticker":       ticker,
                    "issue_price":  0.0,
                    "source":       "nse_official",
                    "exchange":     "NSE Main Board",
                })

        print(f"[LiveIPO] NSE Official: {len(results)} listings since {IPO_START_DATE}")
        return results

    except Exception as e:
        print(f"[LiveIPO] NSE EQUITY_L.csv error: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Source 2: Chittorgarh — Main Board IPO List (with issue price)
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_chittorgarh():
    """
    Scrape Chittorgarh for BSE+NSE main board listed IPOs.
    Correct URL: /ipo/ipo-listed-in-stock-market/5/?year=YYYY
    Returns list of {name, listing_date, issue_price, source}
    """
    if not BS4_AVAILABLE:
        print("[LiveIPO] bs4 not available, skipping Chittorgarh.")
        return []

    results = []
    start_year = int(IPO_START_DATE[:4])
    current_year = datetime.datetime.now().year

    for year in range(start_year, current_year + 1):
        url = f"https://www.chittorgarh.com/ipo/ipo-listed-in-stock-market/5/?year={year}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                print(f"[LiveIPO] Chittorgarh {year}: HTTP {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            year_count = 0
            tables = soup.find_all("table")

            for table in tables:
                rows = table.find_all("tr")
                if len(rows) < 3:
                    continue

                # Detect header row
                header_row = rows[0]
                headers_text = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]

                # Find relevant column indices
                name_idx  = _find_col(headers_text, ["company", "name", "ipo"])
                date_idx  = _find_col(headers_text, ["listing", "listed", "date"])
                price_idx = _find_col(headers_text, ["price", "issue price", "offer"])

                if name_idx is None:
                    continue  # not the data table

                for row in rows[1:]:
                    cols = row.find_all("td")
                    if not cols:
                        continue
                    try:
                        name = cols[name_idx].get_text(strip=True) if name_idx < len(cols) else ""
                        if not name or len(name) < 3:
                            continue

                        date_text = cols[date_idx].get_text(strip=True) if (date_idx is not None and date_idx < len(cols)) else ""
                        listing_date = _parse_date(date_text) or f"{year}-01-01"

                        price_text = cols[price_idx].get_text(strip=True) if (price_idx is not None and price_idx < len(cols)) else "0"
                        issue_price = float(re.sub(r"[^\d.]", "", price_text) or "0")

                        results.append({
                            "name":         name,
                            "listing_date": listing_date,
                            "issue_price":  issue_price,
                            "source":       "chittorgarh",
                            "exchange":     "BSE/NSE Main Board",
                        })
                        year_count += 1
                    except Exception:
                        continue

            print(f"[LiveIPO] Chittorgarh {year}: {year_count} IPOs")
            time.sleep(0.6)

        except Exception as e:
            print(f"[LiveIPO] Chittorgarh {year} error: {e}")
            continue

    return results


def _find_col(headers_list, keywords):
    """Find column index by keyword match."""
    for kw in keywords:
        for i, h in enumerate(headers_list):
            if kw in h:
                return i
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Source 3: Excel Emergency Fallback
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_from_excel():
    results = []
    try:
        if not os.path.exists(EXCEL_IPO_FILE):
            return results
        df_raw = pd.read_excel(EXCEL_IPO_FILE)
        df_raw.columns = [str(c).strip() for c in df_raw.iloc[0]]
        df_ipo = df_raw.iloc[1:].reset_index(drop=True)
        df_ipo["Listed On"] = pd.to_datetime(df_ipo["Listed On"], errors="coerce")
        start_dt = pd.to_datetime(IPO_START_DATE)
        end_dt = pd.Timestamp.now()
        df_f = df_ipo[(df_ipo["Listed On"] >= start_dt) & (df_ipo["Listed On"] <= end_dt)]
        for _, row in df_f.iterrows():
            name = str(row.get("Company Name", "")).strip()
            l_date = row["Listed On"].strftime("%Y-%m-%d") if pd.notnull(row["Listed On"]) else ""
            if name and name != "nan":
                results.append({
                    "name":         name,
                    "listing_date": l_date,
                    "issue_price":  0.0,
                    "source":       "excel",
                    "exchange":     "BSE/NSE Main Board",
                })
        print(f"[LiveIPO] Excel fallback: {len(results)} IPOs")
    except Exception as e:
        print(f"[LiveIPO] Excel error: {e}")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Date Parser
# ─────────────────────────────────────────────────────────────────────────────
def _parse_date(text):
    if not text:
        return ""
    text = text.strip()
    formats = [
        "%d-%b-%Y", "%d/%b/%Y", "%b %d, %Y", "%d %b %Y",
        "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y",
        "%Y-%m-%d", "%B %d, %Y", "%d %B %Y",
        "%b-%y", "%d %b, %Y",
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    m = re.search(r"(\d{1,2})[\s/\-](\w+)[\s/\-](\d{2,4})", text)
    if m:
        try:
            s = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            for fmt in ["%d-%b-%Y", "%d-%B-%Y", "%d-%b-%y"]:
                try:
                    return datetime.datetime.strptime(s, fmt).strftime("%Y-%m-%d")
                except Exception:
                    continue
        except Exception:
            pass
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Merge + Dedup (NSE official takes priority — has real ticker)
# ─────────────────────────────────────────────────────────────────────────────
def _merge_sources(nse_list, cg_list, excel_list):
    """
    Merge all sources. NSE official already has tickers (.NS).
    Chittorgarh + Excel need ticker resolution.
    Priority: nse_official > chittorgarh > excel
    """
    # Build lookup by name (uppercase) from NSE official
    nse_by_name = {}
    for item in nse_list:
        key = item["name"].strip().upper()
        nse_by_name[key] = item

    # Build combined list — NSE official first (pre-resolved), then add CG/Excel extras
    merged = {}  # key: name_upper -> item

    # Start with NSE official (pre-resolved, highest quality)
    for item in nse_list:
        key = item["name"].strip().upper()
        merged[key] = item

    # Add Chittorgarh items not already in NSE list (these need ticker resolution)
    for item in cg_list:
        key = item["name"].strip().upper()
        if key not in merged:
            merged[key] = item

    # Add Excel items not already in any source
    for item in excel_list:
        key = item["name"].strip().upper()
        if key not in merged:
            merged[key] = item

    return list(merged.values())


# ─────────────────────────────────────────────────────────────────────────────
# Ticker Resolver (for items without pre-resolved tickers)
# ─────────────────────────────────────────────────────────────────────────────
def _clean_name(name):
    name = re.sub(r"\(.*?\)", "", name)
    stopwords = [
        "LIMITED", "LTD", "PRIVATE", "PVT", "INDUSTRIES", "INDUSTRY",
        "SOLUTIONS", "TECHNOLOGIES", "TECHNOLOGY", "LOGISTICS", "HEALTHCARE",
        "HEALTH", "SCIENCES", "SCIENCE", "ENERGY", "SYSTEMS", "SYSTEM",
        "CORPORATION", "CORP", "EXPORTS", "VENTURES", "HOLDINGS", "INDIA",
        "ENTERPRISES", "ENTERPRISE", "SERVICES", "SERVICE", "FINTECH",
        "FINANCIAL", "FINANCE", "INFRASTRUCTURE", "CAPITAL", "GROUP",
    ]
    cleaned = name.upper().strip()
    for w in stopwords:
        cleaned = re.sub(r"\b" + w + r"\b", "", cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned if len(cleaned) >= 2 else name.split()[0].upper()


def _resolve_ticker(job):
    idx, orig_name, clean_name = job
    queries = list(dict.fromkeys([clean_name, orig_name.split()[0].upper(), orig_name[:20]]))
    for q in queries:
        try:
            url = (
                "https://query2.finance.yahoo.com/v1/finance/search"
                f"?q={requests.utils.quote(q)}&quotesCount=10&newsCount=0"
            )
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            if resp.status_code == 200:
                for item in resp.json().get("quotes", []):
                    sym = item.get("symbol", "")
                    if sym.endswith(".NS"):
                        return idx, orig_name, sym, "NSE Main Board"
                    elif sym.endswith(".BO"):
                        return idx, orig_name, sym, "BSE Main Board"
        except Exception:
            pass
        time.sleep(0.04)
    return idx, orig_name, None, None


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────
def fetch_live_ipo_universe(force_refresh=False):
    """
    Main entry point. Returns dict:
        {company_name: (ticker, listing_date, exchange_label)}
    """
    print("[LiveIPO] ========================================")
    print("[LiveIPO]  STOKS Live IPO Universe Fetcher V2.0")
    print(f"[LiveIPO]  Date Range: {IPO_START_DATE} to Today")
    print("[LiveIPO]  Sources: NSE Official + Chittorgarh + Excel")
    print("[LiveIPO] ========================================")

    # 1. Try cache
    if not force_refresh:
        cached = _load_cache()
        if cached:
            return {k: tuple(v) for k, v in cached.items()}

    # 2. Fetch from all internet sources
    print("[LiveIPO] Fetching from internet sources...")

    nse_list   = _fetch_nse_equity_list()     # Source 1: NSE Official (has .NS tickers)
    cg_list    = _fetch_chittorgarh()          # Source 2: Chittorgarh (BSE+NSE, needs resolution)
    excel_list = _fetch_from_excel()           # Source 3: Local Excel (emergency)

    print(f"[LiveIPO] Raw counts — NSE: {len(nse_list)} | CG: {len(cg_list)} | Excel: {len(excel_list)}")

    # 3. Merge all sources
    merged = _merge_sources(nse_list, cg_list, excel_list)
    print(f"[LiveIPO] After merge+dedup: {len(merged)} unique IPOs")

    # 4. Resolve tickers for items that don't already have one (Chittorgarh + Excel)
    need_resolution = [(i, item) for i, item in enumerate(merged) if not item.get("ticker")]
    pre_resolved    = [(i, item) for i, item in enumerate(merged) if item.get("ticker")]

    print(f"[LiveIPO] Pre-resolved (NSE): {len(pre_resolved)} | Need resolution: {len(need_resolution)}")

    resolved = {}
    failed = 0

    # Add pre-resolved items directly
    for i, item in pre_resolved:
        resolved[item["name"]] = (item["ticker"], item["listing_date"], item["exchange"])

    # Resolve remaining via Yahoo Finance
    if need_resolution:
        print(f"[LiveIPO] Resolving {len(need_resolution)} additional tickers via Yahoo Finance...")
        jobs = [(i, item["name"], _clean_name(item["name"])) for i, item in need_resolution]

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(_resolve_ticker, job): job for job in jobs}
            for future in as_completed(futures):
                try:
                    idx, orig_name, ticker, exchange = future.result()
                    item = merged[idx]
                    if ticker:
                        resolved[orig_name] = (ticker, item["listing_date"], exchange)
                    else:
                        failed += 1
                except Exception:
                    failed += 1

    print(f"[LiveIPO] Resolved: {len(resolved)} tickers | Failed/Skipped: {failed}")

    # 5. Save cache
    cache_data = {k: list(v) for k, v in resolved.items()}
    _save_cache(cache_data)

    print(f"[LiveIPO] Universe ready: {len(resolved)} BSE+NSE Main Board IPOs ({IPO_START_DATE[:4]}-present)")
    print("[LiveIPO] ========================================")
    return resolved


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Force a fresh fetch (ignore cache)
    universe = fetch_live_ipo_universe(force_refresh=True)
    print(f"\n{'='*60}")
    print(f"TOTAL IPOs FETCHED: {len(universe)}")
    print(f"{'='*60}")

    # Group by year
    from collections import Counter
    year_counts = Counter()
    for name, (ticker, date, exch) in universe.items():
        try:
            year_counts[date[:4]] += 1
        except Exception:
            pass

    print("\nBreakdown by Year:")
    for yr in sorted(year_counts):
        print(f"  {yr}: {year_counts[yr]} IPOs")

    print(f"\nSample (first 15):")
    for name, (ticker, date, exch) in list(universe.items())[:15]:
        print(f"  {ticker:20s} | {date} | {exch:20s} | {name[:40]}")
