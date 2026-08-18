"""
STOKS V4.1 — Sector Heatmap Engine
Maps breakout stocks to sectors using built-in dictionary + yfinance parallel fetch.
Generates rich sector_heatmap_data.json for dashboard workstation.
"""
import pandas as pd
import yfinance as yf
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from prod_logger import log_info, log_error

SECTOR_EMOJI = {
    "Technology": "💻",
    "Healthcare": "💊",
    "Financial Services": "🏦",
    "Consumer Cyclical": "🛍️",
    "Industrials": "⚙️",
    "Basic Materials": "🪨",
    "Energy": "⚡",
    "Real Estate": "🏢",
    "Consumer Defensive": "🛒",
    "Communication Services": "📡",
    "Utilities": "💡",
    "Unknown": "🔷",
}

SECTOR_COLORS = {
    "Technology": "#3b82f6",
    "Healthcare": "#10b981",
    "Financial Services": "#f59e0b",
    "Consumer Cyclical": "#8b5cf6",
    "Industrials": "#06b6d4",
    "Basic Materials": "#ef4444",
    "Energy": "#f97316",
    "Real Estate": "#84cc16",
    "Consumer Defensive": "#ec4899",
    "Communication Services": "#a78bfa",
    "Utilities": "#fbbf24",
    "Unknown": "#64748b",
}

# Pre-mapped Indian stock sectors for ultra-fast offline fallback
KNOWN_SECTORS = {
    "RELIANCE": ("Energy", "Oil & Gas"),
    "TCS": ("Technology", "IT Services"),
    "INFY": ("Technology", "IT Services"),
    "HDFCBANK": ("Financial Services", "Private Banking"),
    "ICICIBANK": ("Financial Services", "Private Banking"),
    "BHARTIARTL": ("Communication Services", "Telecom"),
    "SBIN": ("Financial Services", "Public Banking"),
    "LTIM": ("Technology", "IT Services"),
    "LT": ("Industrials", "Engineering & Construction"),
    "ITC": ("Consumer Defensive", "FMCG"),
    "SUNPHARMA": ("Healthcare", "Pharmaceuticals"),
    "HCLTECH": ("Technology", "IT Services"),
    "KOTAKBANK": ("Financial Services", "Private Banking"),
    "M&M": ("Consumer Cyclical", "Auto"),
    "AXISBANK": ("Financial Services", "Private Banking"),
    "MARUTI": ("Consumer Cyclical", "Auto"),
    "NTPC": ("Utilities", "Power Generation"),
    "ULTRACEMCO": ("Basic Materials", "Cement"),
    "ASIANPAINT": ("Consumer Cyclical", "Paints"),
    "TITAN": ("Consumer Cyclical", "Gems & Jewellery"),
    "BAJFINANCE": ("Financial Services", "NBFC"),
    "POWERGRID": ("Utilities", "Power Transmission"),
    "TATASTEEL": ("Basic Materials", "Steel"),
    "COALINDIA": ("Energy", "Coal Mining"),
    "ADANIENT": ("Industrials", "Conglomerates"),
    "ADANIPORTS": ("Industrials", "Ports & Logistics"),
    "ONGC": ("Energy", "Oil & Gas Exploration"),
    "JSWSTEEL": ("Basic Materials", "Steel"),
    "HINDUNILVR": ("Consumer Defensive", "FMCG"),
    "WIPRO": ("Technology", "IT Services"),
    "ZOMATO": ("Consumer Cyclical", "Food Delivery"),
    "RUBICON": ("Healthcare", "Pharmaceuticals"),
    "KRN": ("Industrials", "HVAC Components"),
    "HAPPYFORGE": ("Industrials", "Forgings"),
    "RISHABH": ("Industrials", "Electrical Instruments"),
    "TURTLEMINT": ("Financial Services", "Insurtech"),
    "QPOWER": ("Utilities", "Power Equipment"),
    "DIVISLAB": ("Healthcare", "Pharma API"),
}


def _resolve_sector(item):
    """Worker function to resolve sector for a ticker."""
    ticker, row = item
    raw_sym = ticker.replace(".NS", "").replace(".BO", "")

    if raw_sym in KNOWN_SECTORS:
        sec, ind = KNOWN_SECTORS[raw_sym]
        return ticker, sec, ind

    try:
        info = yf.Ticker(ticker).info
        sec = info.get("sector", "Industrials" if "ENG" in raw_sym or "FORG" in raw_sym else "Unknown")
        ind = info.get("industry", "Unknown")
        return ticker, sec, ind
    except Exception:
        return ticker, "Industrials" if "FORG" in raw_sym or "IND" in raw_sym else "Healthcare" if "PHARM" in raw_sym or "BIO" in raw_sym else "Unknown", "Unknown"


def build_sector_heatmap():
    """Build sector heatmap data from all breakout CSVs."""
    log_info("Building Sector Heatmap Data...")

    all_dfs = []
    csv_files = [
        "recent_ipo_breakouts_5y.csv",
        "master_scan_results.csv",
        "monthly_ath_breakouts.csv",
    ]

    for f in csv_files:
        if os.path.exists(f):
            try:
                df = pd.read_csv(f)
                all_dfs.append(df)
            except Exception as e:
                log_error(f"Could not load {f}: {e}")

    if not all_dfs:
        log_error("No CSV data found for sector mapping.")
        return []

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["Ticker"]).reset_index(drop=True)
    log_info(f"Total unique tickers for sector mapping: {len(combined)}")

    # Parallel resolution
    items = [(row.get("Ticker", ""), row) for _, row in combined.iterrows()]
    sector_lookup = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_resolve_sector, item): item for item in items}
        for future in as_completed(futures):
            try:
                t, sec, ind = future.result()
                sector_lookup[t] = (sec, ind)
            except Exception:
                pass

    sectors_data = []
    for _, row in combined.iterrows():
        ticker = row.get("Ticker", "")
        company = row.get("Company_Name", ticker)
        score = float(row.get("Strength_Score", 70) or 70)
        rsi = float(row.get("RSI_9", row.get("Monthly_RSI_9", 0)) or 0)
        vol_spike = str(row.get("Volume_Spike", "1.0x")).replace("x", "")
        close = float(row.get("Close", row.get("Monthly_Close", 0)) or 0)

        try:
            vol_val = float(vol_spike)
        except Exception:
            vol_val = 1.0

        sec, ind = sector_lookup.get(ticker, ("Unknown", "Unknown"))

        sectors_data.append({
            "Ticker": ticker,
            "Company_Name": company,
            "Sector": sec,
            "Industry": ind,
            "Strength_Score": score,
            "RSI_9": rsi,
            "Volume_Spike": vol_val,
            "Close": close,
        })

    df_sectors = pd.DataFrame(sectors_data)

    # Aggregate by sector
    sector_groups = {}
    for _, row in df_sectors.iterrows():
        sec = row["Sector"] or "Unknown"
        if sec not in sector_groups:
            sector_groups[sec] = {
                "sector": sec,
                "emoji": SECTOR_EMOJI.get(sec, "🔷"),
                "color": SECTOR_COLORS.get(sec, "#64748b"),
                "count": 0,
                "total_score": 0,
                "total_rsi": 0,
                "top_stock": "",
                "top_score": 0,
                "stocks": [],
            }
        g = sector_groups[sec]
        g["count"] += 1
        g["total_score"] += float(row["Strength_Score"])
        g["total_rsi"] += float(row["RSI_9"])
        stock_entry = {
            "ticker": row["Ticker"],
            "name": str(row["Company_Name"]),
            "score": float(row["Strength_Score"]),
            "rsi": float(row["RSI_9"]),
            "vol": round(float(row["Volume_Spike"]), 2),
            "close": float(row["Close"]),
        }
        g["stocks"].append(stock_entry)
        if stock_entry["score"] > g["top_score"]:
            g["top_score"] = stock_entry["score"]
            g["top_stock"] = str(row["Company_Name"]).split(" ")[0]

    # Compute averages
    heatmap_list = []
    for sec, g in sector_groups.items():
        g["avg_score"] = round(g["total_score"] / g["count"], 1)
        g["avg_rsi"] = round(g["total_rsi"] / g["count"], 1)
        g["stocks"] = sorted(g["stocks"], key=lambda x: x["score"], reverse=True)
        del g["total_score"], g["total_rsi"]
        heatmap_list.append(g)

    # Sort by count desc, then avg_score desc
    heatmap_list.sort(key=lambda x: (x["count"], x["avg_score"]), reverse=True)

    output_path = "sector_heatmap_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(heatmap_list, f, separators=(",", ":"), ensure_ascii=False)

    log_info(f"SUCCESS: Sector Heatmap saved -> {output_path} ({len(heatmap_list)} sectors)")
    return heatmap_list


if __name__ == "__main__":
    build_sector_heatmap()
