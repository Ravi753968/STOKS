import pandas as pd
import numpy as np
import yfinance as yf
import requests
import datetime
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

def clean_company_name(name):
    """Clean company name for search matching."""
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

def main():
    print("=" * 80)
    print(" BSE MAIN BOARD IPO ALL-TIME HIGH (ATH) BREAKOUT SCANNER ")
    print(" Date Range: 01-Jan-2022 to 16-Aug-2026")
    print(f" Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    excel_path = r'd:\STOKS\BSE MAIN BOARD IPO.xlsx'
    df_raw = pd.read_excel(excel_path)
    df_raw.columns = [str(c).strip() for c in df_raw.iloc[0]]
    df_ipo = df_raw.iloc[1:].reset_index(drop=True)
    df_ipo['Listed On'] = pd.to_datetime(df_ipo['Listed On'], errors='coerce')
    
    # Filter 2022 to 2026
    filtered_ipo = df_ipo[(df_ipo['Listed On'] >= '2022-01-01') & (df_ipo['Listed On'] <= '2026-08-16')].copy()
    print(f"Total BSE Main Board IPOs listed between 2022 & 2026: {len(filtered_ipo)}")
    
    company_list = []
    for idx, row in filtered_ipo.iterrows():
        c_name = str(row['Company Name']).strip()
        l_date = row['Listed On'].strftime('%Y-%m-%d') if pd.notnull(row['Listed On']) else 'N/A'
        if c_name and c_name != 'nan':
            clean_n = clean_company_name(c_name)
            company_list.append((idx, c_name, clean_n, l_date))
            
    print("Resolving exchange tickers via Yahoo Finance API...")
    resolved_tickers = {}
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(search_ticker, (c[0], c[1], c[2])) for c in company_list]
        for f in as_completed(futures):
            idx, orig_name, ticker = f.result()
            if ticker:
                # Find listing date
                l_date = next((item[3] for item in company_list if item[1] == orig_name), 'N/A')
                resolved_tickers[orig_name] = (ticker, l_date)

    print(f"Successfully resolved {len(resolved_tickers)} valid tickers!")
    
    unique_tickers = list(set([t[0] for t in resolved_tickers.values()]))
    print(f"Downloading historical price data (period='max') for {len(unique_tickers)} tickers...")
    
    data = yf.download(unique_tickers, period="max", interval="1d", progress=True)
    if 'Close' not in data or 'High' not in data:
        print("Failed to download price data.")
        return
        
    closes = data['Close']
    highs = data['High']
    
    ath_breakouts = []
    
    for orig_name, (ticker, l_date) in resolved_tickers.items():
        if ticker not in closes.columns or ticker not in highs.columns:
            continue
            
        s_close = closes[ticker].dropna()
        s_high = highs[ticker].dropna()
        
        if len(s_close) < 10:
            continue
            
        curr_close = float(s_close.iloc[-1])
        curr_high = float(s_high.iloc[-1])
        
        # Historical max prior to latest candle
        prev_max_close = float(s_close.iloc[:-1].max())
        prev_max_high = float(s_high.iloc[:-1].max())
        all_time_max_high = max(prev_max_high, curr_high)
        
        # Calculate % distance to All Time High High/Close
        pct_from_ath_high = ((curr_close - prev_max_high) / prev_max_high) * 100.0
        pct_from_ath_close = ((curr_close - prev_max_close) / prev_max_close) * 100.0
        
        # ATH Breakout Conditions:
        # 1. Fresh ATH Breakout: Current Close > Prev All-Time High Price (or Close)
        is_fresh_ath_close_breakout = curr_close >= prev_max_close
        is_fresh_ath_high_breakout = curr_close >= prev_max_high or curr_high >= prev_max_high
        
        if is_fresh_ath_close_breakout or is_fresh_ath_high_breakout or (pct_from_ath_high >= -1.0):
            if is_fresh_ath_close_breakout and is_fresh_ath_high_breakout:
                category = "[NEW ATH] NEW ALL-TIME HIGH (FRESH ATH CLOSE & HIGH BREAKOUT)"
                priority = 1
            elif is_fresh_ath_close_breakout:
                category = "[ATH CLOSE] FRESH ATH CLOSE BREAKOUT"
                priority = 2
            elif is_fresh_ath_high_breakout:
                category = "[ATH HIGH] FRESH ATH HIGH BREAKOUT"
                priority = 3
            else:
                category = "[ATH NEAR] AT ATH RESISTANCE (WITHIN 1% OF ATH)"
                priority = 4
                
            ath_breakouts.append({
                "Company_Name": orig_name,
                "Ticker": ticker,
                "Listed_Date": l_date,
                "Current_Close": round(curr_close, 2),
                "Today_High": round(curr_high, 2),
                "Prev_ATH_High": round(prev_max_high, 2),
                "Prev_ATH_Close": round(prev_max_close, 2),
                "ATH_Diff_%": round(pct_from_ath_high, 2),
                "Breakout_Type": category,
                "Priority": priority
            })

    if not ath_breakouts:
        print("\nNo IPO stocks currently at or above All-Time High.")
        return

    df_res = pd.DataFrame(ath_breakouts)
    df_res = df_res.sort_values(by=["Priority", "ATH_Diff_%"], ascending=[True, False])
    df_res.to_csv("bse_ipo_ath_breakouts.csv", index=False)
    
    print("\n" + "=" * 80)
    print(f" TOTAL IPOs WITH ALL-TIME HIGH (ATH) BREAKOUT: {len(df_res)}")
    print(" Results saved to 'bse_ipo_ath_breakouts.csv'")
    print("=" * 80)
    print(df_res[["Company_Name", "Ticker", "Listed_Date", "Current_Close", "Prev_ATH_High", "ATH_Diff_%", "Breakout_Type"]].to_string(index=False))

if __name__ == "__main__":
    main()
