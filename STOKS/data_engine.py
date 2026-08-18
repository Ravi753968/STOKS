"""
STOKS Data Engine V4.1
Loads IPO universe from live internet sources (live_ipo_fetcher.py).
Falls back to Excel if internet is unavailable.
"""
import yfinance as yf
import pandas as pd
import datetime
from config import EXCEL_IPO_FILE, CACHE_DIR, IPO_START_DATE, IPO_END_DATE

# ─────────────────────────────────────────────────────────────────────────────
# Public API: load_ipo_universe_5y
# ─────────────────────────────────────────────────────────────────────────────
def load_ipo_universe_5y(force_refresh=False):
    """
    Load BSE & NSE Main Board IPOs listed from 2022 onwards.
    Uses live_ipo_fetcher (internet) with 24h cache.
    Falls back to Excel if internet fails.

    Returns:
        dict: {company_name: (ticker, listing_date, exchange_label)}
    """
    # Try live internet fetcher first
    try:
        from live_ipo_fetcher import fetch_live_ipo_universe
        universe = fetch_live_ipo_universe(force_refresh=force_refresh)
        if universe:
            return universe
        print("[DataEngine] Live fetcher returned empty. Trying Excel fallback...")
    except Exception as e:
        print(f"[DataEngine] Live fetcher error: {e}. Trying Excel fallback...")

    # Excel fallback
    return _load_from_excel()


def _load_from_excel():
    """Emergency fallback: load IPO list from local Excel file."""
    import os, re
    import requests
    from concurrent.futures import ThreadPoolExecutor, as_completed

    all_targets = {}
    if not os.path.exists(EXCEL_IPO_FILE):
        print("[DataEngine] Excel file not found. No IPO data available.")
        return all_targets

    try:
        df_raw = pd.read_excel(EXCEL_IPO_FILE)
        df_raw.columns = [str(c).strip() for c in df_raw.iloc[0]]
        df_ipo = df_raw.iloc[1:].reset_index(drop=True)
        df_ipo["Listed On"] = pd.to_datetime(df_ipo["Listed On"], errors="coerce")

        start_dt = pd.to_datetime(IPO_START_DATE)
        end_dt = pd.to_datetime(IPO_END_DATE)
        filtered = df_ipo[
            (df_ipo["Listed On"] >= start_dt) & (df_ipo["Listed On"] <= end_dt)
        ].copy()

        ipo_list = []
        for idx, row in filtered.iterrows():
            c_name = str(row["Company Name"]).strip()
            l_date = row["Listed On"].strftime("%Y-%m-%d") if pd.notnull(row["Listed On"]) else "N/A"
            if c_name and c_name != "nan":
                clean_n = _clean_name(c_name)
                ipo_list.append((idx, c_name, clean_n, l_date))

        print(f"[DataEngine] Excel fallback: resolving tickers for {len(ipo_list)} IPOs...")

        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(_search_ticker, (c[0], c[1], c[2])) for c in ipo_list]
            for f in as_completed(futures):
                idx, orig_name, ticker = f.result()
                if ticker:
                    l_date = next((item[3] for item in ipo_list if item[1] == orig_name), "N/A")
                    exch = "NSE Main Board" if ticker.endswith(".NS") else "BSE Main Board"
                    all_targets[orig_name] = (ticker, l_date, exch)

        print(f"[DataEngine] Excel fallback resolved {len(all_targets)} tickers.")
    except Exception as e:
        print(f"[DataEngine] Excel fallback error: {e}")

    return all_targets


def _clean_name(name):
    import re
    name = re.sub(r'\(.*?\)', '', name)
    stopwords = ['LIMITED', 'LTD', 'INDUSTRIES', 'SOLUTIONS', 'TECHNOLOGIES',
                 'LOGISTICS', 'HEALTHCARE', 'SCIENCES', 'ENERGY', 'SYSTEMS', 'CORPORATION']
    cleaned = name.upper()
    for w in stopwords:
        cleaned = re.sub(r'\b' + w + r'\b', '', cleaned)
    cleaned = ' '.join(cleaned.split())
    return cleaned if cleaned else name.split()[0]


def _search_ticker(comp_info):
    import requests
    idx, orig_name, clean_name = comp_info
    for q in [clean_name, orig_name.split()[0]]:
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(q)}&quotesCount=10"
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
            for item in res.get("quotes", []):
                sym = item.get("symbol", "")
                if sym.endswith(".NS") or sym.endswith(".BO"):
                    return idx, orig_name, sym
        except Exception:
            pass
    return idx, orig_name, None


# ─────────────────────────────────────────────────────────────────────────────
# Market Data Fetcher
# ─────────────────────────────────────────────────────────────────────────────
def fetch_market_data(tickers, period="60d", interval="1d"):
    """Fetch OHLCV market data for a list of tickers via yfinance."""
    if not tickers:
        return None
    try:
        data = yf.download(
            tickers, period=period, interval=interval,
            progress=False, auto_adjust=True, threads=True,
        )
        return data
    except Exception as e:
        print(f"[DataEngine] Fetch error: {e}")
        return None
