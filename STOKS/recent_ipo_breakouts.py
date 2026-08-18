import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import os
import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

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

def calculate_rsi(series, period=9):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def main():
    print("=" * 80)
    print(" SCANNER FOR STOCKS LISTED WITHIN 5 YEARS AND BELOW (2021-2026) ")
    print(" Criteria: Close > Upper BB (20,2) AND RSI(9) > 60 AND Volume Spike")
    print(f" Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 1. Load Excel File
    excel_path = r'd:\STOKS\BSE MAIN BOARD IPO.xlsx'
    df_raw = pd.read_excel(excel_path)
    df_raw.columns = [str(c).strip() for c in df_raw.iloc[0]]
    df_ipo = df_raw.iloc[1:].reset_index(drop=True)
    df_ipo['Listed On'] = pd.to_datetime(df_ipo['Listed On'], errors='coerce')
    
    # Strictly Filter 5 Years and Below: Listed between 16-Aug-2021 and 16-Aug-2026
    five_years_ago = pd.to_datetime('2021-08-16')
    today_date = pd.to_datetime('2026-08-16')
    
    filtered_ipo = df_ipo[(df_ipo['Listed On'] >= five_years_ago) & (df_ipo['Listed On'] <= today_date)].copy()
    print(f"Total Main Board IPOs listed within last 5 years (2021 to 2026): {len(filtered_ipo)}")
    
    ipo_list = []
    for idx, row in filtered_ipo.iterrows():
        c_name = str(row['Company Name']).strip()
        l_date = row['Listed On'].strftime('%Y-%m-%d') if pd.notnull(row['Listed On']) else 'N/A'
        if c_name and c_name != 'nan':
            clean_n = clean_company_name(c_name)
            ipo_list.append((idx, c_name, clean_n, l_date))

    print("Resolving exchange tickers via Yahoo Finance API...")
    resolved_tickers = {}
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(search_ticker, (c[0], c[1], c[2])) for c in ipo_list]
        for f in as_completed(futures):
            idx, orig_name, ticker = f.result()
            if ticker:
                l_date = next((item[3] for item in ipo_list if item[1] == orig_name), 'N/A')
                exch_label = "NSE Main Board" if ticker.endswith('.NS') else "BSE Main Board"
                resolved_tickers[orig_name] = (ticker, l_date, exch_label)

    unique_tickers = list(set([t[0] for t in resolved_tickers.values()]))
    print(f"Downloading daily market data for {len(unique_tickers)} tickers...")

    data = yf.download(unique_tickers, period="60d", interval="1d", progress=True)
    if 'Close' not in data or 'Volume' not in data:
        print("Failed to download price data.")
        return

    closes = data['Close']
    highs = data['High']
    lows = data['Low']
    volumes = data['Volume']

    results = []

    for orig_name, (ticker, l_date, u_name) in resolved_tickers.items():
        if ticker not in closes.columns or ticker not in volumes.columns:
            continue

        s_close = closes[ticker].dropna()
        s_high = highs[ticker].dropna()
        s_low = lows[ticker].dropna()
        s_vol = volumes[ticker].dropna()

        if len(s_close) < 20:
            continue

        c_curr = float(s_close.iloc[-1])
        c_prev = float(s_close.iloc[-2])

        sma20 = s_close.rolling(20).mean()
        std20 = s_close.rolling(20).std()
        upper_bb = sma20 + (2.0 * std20)

        ubb_curr = float(upper_bb.iloc[-1])
        ubb_prev = float(upper_bb.iloc[-2])
        sma20_curr = float(sma20.iloc[-1])

        rsi9 = calculate_rsi(s_close, period=9)
        rsi9_curr = float(rsi9.iloc[-1])
        rsi9_prev = float(rsi9.iloc[-2])

        vol_sma20 = s_vol.rolling(20).mean()
        v_curr = float(s_vol.iloc[-1])
        v_sma_curr = float(vol_sma20.iloc[-1])
        vol_mult = (v_curr / v_sma_curr) if v_sma_curr > 0 else 1.0

        if np.isnan(c_curr) or np.isnan(ubb_curr) or np.isnan(rsi9_curr):
            continue

        bb_cross = (c_prev <= ubb_prev) and (c_curr > ubb_curr)
        bb_above = c_curr > ubb_curr

        rsi9_cross = (rsi9_prev <= 60.0) and (rsi9_curr > 60.0)
        rsi9_above = rsi9_curr > 60.0

        if bb_above and rsi9_above:
            sl_price = round(max(sma20_curr, c_curr * 0.94), 2)
            risk = round(c_curr - sl_price, 2)
            
            vol_boost = 1.15 if vol_mult >= 5.0 else (1.08 if vol_mult >= 2.0 else 1.0)
            target_1 = round(c_curr + (1.5 * risk * vol_boost), 2)
            t1_gain = round(((target_1 - c_curr) / c_curr) * 100.0, 2)

            target_2 = round(c_curr + (2.5 * risk * vol_boost), 2)
            t2_gain = round(((target_2 - c_curr) / c_curr) * 100.0, 2)

            score = 50
            if bb_cross: score += 15
            if rsi9_cross: score += 20
            if vol_mult >= 2.0: score += 15
            score = min(score, 100)

            results.append({
                "Company_Name": orig_name,
                "Ticker": ticker,
                "Exchange": u_name,
                "Listed_Date": l_date,
                "Close": round(c_curr, 2),
                "Upper_BB": round(ubb_curr, 2),
                "RSI_9": round(rsi9_curr, 2),
                "Volume_Spike": f"{round(vol_mult, 2)}x",
                "Stop_Loss": sl_price,
                "Target_1": target_1,
                "Target_1_Gain_%": f"+{t1_gain}%",
                "Target_2": target_2,
                "Target_2_Gain_%": f"+{t2_gain}%",
                "Strength_Score": score
            })

    if not results:
        print("\nNo stocks listed within 5 years currently match the breakout criteria.")
        return

    res_df = pd.DataFrame(results).sort_values(by=["Strength_Score", "RSI_9"], ascending=[False, False])
    
    # Save CSV
    output_csv = "recent_ipo_breakouts_5y.csv"
    res_df.to_csv(output_csv, index=False)
    
    print("\n" + "=" * 80)
    print(f" TOTAL BREAKOUT STOCKS LISTED WITHIN 5 YEARS AND BELOW: {len(res_df)}")
    print(f" Saved to '{output_csv}'")
    print("=" * 80)
    
    cols = ["Company_Name", "Ticker", "Listed_Date", "Close", "Upper_BB", "RSI_9", "Volume_Spike", "Stop_Loss", "Target_1", "Target_1_Gain_%"]
    print(res_df[cols].to_string(index=False))

if __name__ == "__main__":
    main()
