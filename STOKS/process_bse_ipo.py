import pandas as pd
import numpy as np
import yfinance as yf
import requests
import datetime
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

def clean_company_name(name):
    """Clean company name for better search matching."""
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
    
    # Try searching clean name first, then original
    for q in [clean_name, orig_name.split()[0]]:
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(q)}&quotesCount=10"
            res = requests.get(url, headers=headers, timeout=5).json()
            quotes = res.get('quotes', [])
            
            # Prefer .NS or .BO
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
    print(" SCANNER FOR BSE MAIN BOARD IPO STOCKS ")
    print(" Criteria: Close > Upper Bollinger Band (20,2) AND RSI (14) > 60")
    print(f" Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    excel_path = r'd:\STOKS\BSE MAIN BOARD IPO.xlsx'
    df_raw = pd.read_excel(excel_path)
    df_raw.columns = [str(c).strip() for c in df_raw.iloc[0]]
    df_ipo = df_raw.iloc[1:].reset_index(drop=True)
    
    company_list = []
    for idx, row in df_ipo.iterrows():
        c_name = str(row['Company Name']).strip()
        if c_name and c_name != 'nan':
            clean_n = clean_company_name(c_name)
            company_list.append((idx, c_name, clean_n))
            
    print(f"Total IPO Companies in Excel: {len(company_list)}")
    print("Resolving tickers via Yahoo Finance API...")
    
    resolved_tickers = {}
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(search_ticker, c) for c in company_list]
        for f in as_completed(futures):
            idx, orig_name, ticker = f.result()
            if ticker:
                resolved_tickers[orig_name] = ticker

    print(f"Successfully resolved {len(resolved_tickers)} valid tickers!")
    
    if not resolved_tickers:
        print("No valid tickers resolved.")
        return

    unique_tickers = list(set(resolved_tickers.values()))
    print(f"Downloading market data for {len(unique_tickers)} tickers...")
    
    data = yf.download(unique_tickers, period="60d", interval="1d", progress=True)
    if 'Close' not in data:
        print("Failed to download price data.")
        return
        
    closes = data['Close']
    
    results = []
    
    for orig_name, ticker in resolved_tickers.items():
        if ticker not in closes.columns:
            continue
            
        s_close = closes[ticker].dropna()
        if len(s_close) < 25:
            continue
            
        # Indicators
        sma20 = s_close.rolling(window=20).mean()
        std20 = s_close.rolling(window=20).std()
        upper_bb = sma20 + (2.0 * std20)
        rsi = calculate_rsi(s_close, period=14)
        
        c_curr = float(s_close.iloc[-1])
        c_prev = float(s_close.iloc[-2])
        
        ubb_curr = float(upper_bb.iloc[-1])
        ubb_prev = float(upper_bb.iloc[-2])
        
        rsi_curr = float(rsi.iloc[-1])
        rsi_prev = float(rsi.iloc[-2])
        
        if np.isnan(c_curr) or np.isnan(ubb_curr) or np.isnan(rsi_curr):
            continue
            
        bb_cross = (c_prev <= ubb_prev) and (c_curr > ubb_curr)
        bb_above = c_curr > ubb_curr
        
        rsi_cross = (rsi_prev <= 60.0) and (rsi_curr > 60.0)
        rsi_above = rsi_curr > 60.0
        
        if bb_above and rsi_above:
            bb_diff_pct = ((c_curr - ubb_curr) / ubb_curr) * 100.0
            
            if bb_cross and rsi_cross:
                category = "PERFECT DUAL CROSSOVER (BB & RSI 60)"
                priority = 1
            elif bb_cross and rsi_above:
                category = "FRESH BB CROSSOVER (RSI > 60)"
                priority = 2
            elif rsi_cross and bb_above:
                category = "FRESH RSI 60 CROSSOVER (CLOSE > UPPER BB)"
                priority = 3
            else:
                category = "ACTIVE BREAKOUT (CLOSE > UPPER BB & RSI > 60)"
                priority = 4
                
            results.append({
                "Company_Name": orig_name,
                "Ticker": ticker,
                "Close": round(c_curr, 2),
                "Upper_BB": round(ubb_curr, 2),
                "BB_Diff_%": round(bb_diff_pct, 2),
                "RSI": round(rsi_curr, 2),
                "Prev_RSI": round(rsi_prev, 2),
                "BB_Crossed_Today": "YES" if bb_cross else "NO",
                "RSI_Crossed_Today": "YES" if rsi_cross else "NO",
                "Category": category,
                "Priority": priority
            })

    if not results:
        print("\nNo stocks from the BSE IPO list currently match the criteria (Close > Upper BB AND RSI > 60).")
        return

    res_df = pd.DataFrame(results)
    res_df = res_df.sort_values(by=["Priority", "RSI"], ascending=[True, False])
    res_df.to_csv("bse_ipo_scan_results.csv", index=False)
    
    print("\n" + "=" * 80)
    print(f" TOTAL MATCHING IPO STOCKS FOUND: {len(res_df)}")
    print(" Results saved to 'bse_ipo_scan_results.csv'")
    print("=" * 80)
    print(res_df[["Company_Name", "Ticker", "Close", "Upper_BB", "BB_Diff_%", "RSI", "Prev_RSI", "Category"]].to_string(index=False))

if __name__ == "__main__":
    main()
