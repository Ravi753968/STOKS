import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import os
import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# Top NSE Stocks Universe
NSE_STOCKS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "BHARTIARTL", "SBIN", "LTIM", "LT", "ITC",
    "SUNPHARMA", "HCLTECH", "KOTAKBANK", "M&M", "AXISBANK", "MARUTI", "NTPC", "ULTRACEMCO", "ASIANPAINT", "TITAN",
    "BAJFINANCE", "POWERGRID", "TATASTEEL", "COALINDIA", "ADANIENT", "ADANIPORTS", "ONGC", "JSWSTEEL", "HINDUNILVR", "WIPRO",
    "NESTLEIND", "TRENT", "BEL", "HAL", "SIEMENS", "ABB", "ZOMATO", "VBL", "CHOLAFIN", "IOC",
    "REC", "PFC", "DLF", "GAIL", "BPCL", "INDIGO", "CIPLA", "DRREDDY", "DIVISLAB", "EICHERMOT",
    "HEROMOTOCO", "BAJAJ-AUTO", "GRASIM", "BRITANNIA", "TECHM", "HDFCLIFE", "SBILIFE", "ICICIPRULI", "TATACONSUM", "APOLLOHOSP",
    "HINDALCO", "BANKBARODA", "PNB", "IDFCFIRSTB", "CANBK", "UNIONBANK", "BHEL", "HINDZINC", "NMDC", "SAIL",
    "VEDL", "INDUSTOWER", "POLYCAB", "KEI", "DIXON", "TATAELXSI", "PERSISTENT", "COFORGE", "MPHASIS", "OFSS",
    "HDFCAMC", "NAM-INDIA", "CDSL", "BSE", "MCX", "IRCTC", "IRFC", "RVNL", "RAILTEL", "MAZDOCK",
    "GRSE", "BDL", "SOLARINDS", "SCHAEFFLER", "TIMKEN", "SKFINDIA", "CUMMINSIND", "ASTRAL", "SUPREMEIND", "PIDILITIND",
    "BERGEPAINT", "JUBLFOOD", "DEVYANI", "MOTHERSON", "BALKRISIND", "MRF", "APOLLOTYRE", "CEATLTD", "EXIDEIND", "AMBER",
    "KAYNES", "SYRMA", "CYIENT", "KPITTECH", "SONACOMS", "PRESTIGE", "OBEROIRLTY", "PHOENIXLTD", "GODREJPROP", "LODHA",
    "MANKIND", "LUPIN", "ALKEM", "TORNTPHARM", "ABBOTINDIA", "AUROPHARMA", "BIOCON", "SYNGENE", "LAURUSLABS", "GLENMARK",
    "JBCHEPHARM", "AJANTPHARM", "IPCALAB", "NATCOPHARM", "GRANULES", "MEDANTA", "MAXHEALTH", "NH", "FORTS", "KIMS",
    "METROPOLIS", "LALPATHLAB", "TATACOMM", "IDEA", "RADICO", "UBL", "MCDOWELL-N", "PATANJALI", "TATACHEM", "DEEPAKNTR",
    "GUJGASLTD", "IGL", "MGL", "ATGL", "PETRONET", "OIL", "CHAMBLFERT", "COROMANDEL", "UPL", "PIIND",
    "SRF", "NAVINFLUOR", "ATUL", "AETHER", "FINEORG", "FLUOROCHEM", "CLEAN", "ANGELONE", "NUVAMA", "360ONE", "MOTILALOFS"
]

def clean_company_name(name):
    if not isinstance(name, str):
        return ""
    name = re.sub(r'\(.*?\)', '', name)
    words_to_remove = ['LIMITED', 'LTD', 'EXPORTS', 'INDUSTRIES', 'SOLUTIONS', 'TECHNOLOGIES', 'LOGISTICS', 'HEALTH', 'SCIENCE', 'ENERGY', 'SYSTEMS', 'CORP', 'CORPORATION']
    cleaned = name.upper()
    for word in words_to_remove:
        cleaned = re.sub(r'\b' + word + r'\b', '', cleaned)
    cleaned = ' '.join(cleaned.split())
    return cleaned if cleaned else name.split()[0]

def search_ticker(comp_info):
    idx, orig_name, clean_name = comp_info
    headers = {'User-Agent': 'Mozilla/5.0'}
    for q in [clean_name, orig_name.split()[0]]:
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(q)}&quotesCount=10"
            res = requests.get(url, headers=headers, timeout=5).json()
            quotes = res.get('quotes', [])
            for item in quotes:
                sym = item.get('symbol', '')
                if sym.endswith('.NS') or sym.endswith('.BO'):
                    return idx, orig_name, sym
        except Exception:
            pass
    return idx, orig_name, None

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def main():
    print("=" * 80)
    print(" MONTHLY TIMEFRAME ALL-TIME HIGH (ATH) BREAKOUT SCANNER ")
    print(" Universes: BSE Main Board IPOs (2022-2026) & NSE Top Stocks")
    print(f" Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 1. Load BSE IPO List (2022 - 2026)
    excel_path = r'd:\STOKS\BSE MAIN BOARD IPO.xlsx'
    df_raw = pd.read_excel(excel_path)
    df_raw.columns = [str(c).strip() for c in df_raw.iloc[0]]
    df_ipo = df_raw.iloc[1:].reset_index(drop=True)
    df_ipo['Listed On'] = pd.to_datetime(df_ipo['Listed On'], errors='coerce')
    filtered_ipo = df_ipo[(df_ipo['Listed On'] >= '2022-01-01') & (df_ipo['Listed On'] <= '2026-08-16')].copy()
    
    ipo_company_list = []
    for idx, row in filtered_ipo.iterrows():
        c_name = str(row['Company Name']).strip()
        l_date = row['Listed On'].strftime('%Y-%m-%d') if pd.notnull(row['Listed On']) else 'N/A'
        if c_name and c_name != 'nan':
            clean_n = clean_company_name(c_name)
            ipo_company_list.append((idx, c_name, clean_n, l_date))

    print(f"Resolving exchange tickers for {len(ipo_company_list)} BSE IPO stocks...")
    resolved_ipo_tickers = {}
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(search_ticker, (c[0], c[1], c[2])) for c in ipo_company_list]
        for f in as_completed(futures):
            idx, orig_name, ticker = f.result()
            if ticker:
                l_date = next((item[3] for item in ipo_company_list if item[1] == orig_name), 'N/A')
                resolved_ipo_tickers[orig_name] = (ticker, l_date, "BSE Main Board IPO")

    # 2. Add NSE Stocks Universe
    all_targets = {}  # ticker -> (display_name, listing_date, universe_name)
    for orig_name, (ticker, l_date, u_name) in resolved_ipo_tickers.items():
        all_targets[ticker] = (orig_name, l_date, u_name)

    for n_sym in NSE_STOCKS:
        t = f"{n_sym}.NS"
        if t not in all_targets:
            all_targets[t] = (n_sym, "Prior to 2022", "NSE Top Stock")

    unique_tickers = list(all_targets.keys())
    print(f"Total Combined Unique Tickers to Scan: {len(unique_tickers)}")
    print("Downloading Monthly Historical Data (interval='1mo', period='max')...")

    # Fetch Monthly data
    data = yf.download(unique_tickers, period="max", interval="1mo", progress=True)
    if 'Close' not in data or 'High' not in data:
        print("Failed to download monthly price data.")
        return

    closes = data['Close']
    highs = data['High']

    monthly_ath_matches = []

    for ticker, (disp_name, l_date, u_name) in all_targets.items():
        if ticker not in closes.columns or ticker not in highs.columns:
            continue

        s_close = closes[ticker].dropna()
        s_high = highs[ticker].dropna()

        if len(s_close) < 6: # need at least 6 months of data
            continue

        curr_close = float(s_close.iloc[-1])
        curr_high = float(s_high.iloc[-1])

        # Prior monthly historical max (excluding current active month)
        prev_max_close = float(s_close.iloc[:-1].max())
        prev_max_high = float(s_high.iloc[:-1].max())

        # Monthly RSI (14)
        m_rsi_series = calculate_rsi(s_close, period=14)
        m_rsi_val = float(m_rsi_series.iloc[-1]) if not m_rsi_series.empty and not np.isnan(m_rsi_series.iloc[-1]) else 0.0

        # Differences
        pct_diff_high = ((curr_close - prev_max_high) / prev_max_high) * 100.0
        pct_diff_close = ((curr_close - prev_max_close) / prev_max_close) * 100.0

        # Breakout Conditions:
        # 1. Fresh Monthly ATH High & Close Breakout: curr_close >= prev_max_high
        # 2. Fresh Monthly ATH Close Breakout: curr_close >= prev_max_close
        # 3. Monthly ATH High Touch: curr_high >= prev_max_high or within 1% of ATH
        is_fresh_high_breakout = curr_close >= prev_max_high or curr_high >= prev_max_high
        is_fresh_close_breakout = curr_close >= prev_max_close

        if is_fresh_high_breakout or is_fresh_close_breakout or (pct_diff_high >= -1.0):
            if curr_close >= prev_max_high:
                category = "[MONTHLY FRESH ATH] NEW ALL-TIME HIGH CLOSE & HIGH"
                priority = 1
            elif is_fresh_close_breakout:
                category = "[MONTHLY ATH CLOSE] FRESH ALL-TIME HIGH CLOSE"
                priority = 2
            elif is_fresh_high_breakout:
                category = "[MONTHLY ATH HIGH] ALL-TIME HIGH TOUCHED THIS MONTH"
                priority = 3
            else:
                category = "[MONTHLY ATH NEAR] WITHIN 1% OF MONTHLY ALL-TIME HIGH"
                priority = 4

            monthly_ath_matches.append({
                "Company_Name": disp_name,
                "Ticker": ticker,
                "Universe": u_name,
                "Listed_Date": l_date,
                "Monthly_Close": round(curr_close, 2),
                "Monthly_High": round(curr_high, 2),
                "Prev_Monthly_ATH_High": round(prev_max_high, 2),
                "Prev_Monthly_ATH_Close": round(prev_max_close, 2),
                "Monthly_ATH_Diff_%": round(pct_diff_high, 2),
                "Monthly_RSI": round(m_rsi_val, 2),
                "Breakout_Category": category,
                "Priority": priority
            })

    if not monthly_ath_matches:
        print("No stocks currently exhibit a Monthly All-Time High Breakout.")
        return

    df_res = pd.DataFrame(monthly_ath_matches)
    df_res = df_res.sort_values(by=["Priority", "Monthly_ATH_Diff_%"], ascending=[True, False])
    df_res.to_csv("monthly_ath_breakouts.csv", index=False)

    print("\n" + "=" * 80)
    print(f" MONTHLY ALL-TIME HIGH (ATH) BREAKOUT RESULTS: {len(df_res)} STOCKS FOUND")
    print(" Results saved to 'monthly_ath_breakouts.csv'")
    print("=" * 80)

    cols = ["Company_Name", "Ticker", "Universe", "Monthly_Close", "Prev_Monthly_ATH_High", "Monthly_ATH_Diff_%", "Monthly_RSI", "Breakout_Category"]
    print(df_res[cols].to_string(index=False))

if __name__ == "__main__":
    main()
