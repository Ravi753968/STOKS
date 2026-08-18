import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import os
import json
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
    print(" INSTITUTIONAL MASTER BREAKOUT SCANNER (BB + RSI + VOLUME + ATH) ")
    print(f" Date & Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Load Universe: BSE Main Board IPOs + Top NSE Stocks
    excel_path = r'd:\STOKS\BSE MAIN BOARD IPO.xlsx'
    df_raw = pd.read_excel(excel_path)
    df_raw.columns = [str(c).strip() for c in df_raw.iloc[0]]
    df_ipo = df_raw.iloc[1:].reset_index(drop=True)
    df_ipo['Listed On'] = pd.to_datetime(df_ipo['Listed On'], errors='coerce')
    
    company_list = []
    for idx, row in df_ipo.iterrows():
        c_name = str(row['Company Name']).strip()
        l_date = row['Listed On'].strftime('%Y-%m-%d') if pd.notnull(row['Listed On']) else 'N/A'
        if c_name and c_name != 'nan':
            clean_n = clean_company_name(c_name)
            company_list.append((idx, c_name, clean_n, l_date))
            
    print("Resolving exchange tickers...")
    resolved_tickers = {}
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(search_ticker, (c[0], c[1], c[2])) for c in company_list]
        for f in as_completed(futures):
            idx, orig_name, ticker = f.result()
            if ticker:
                l_date = next((item[3] for item in company_list if item[1] == orig_name), 'N/A')
                resolved_tickers[orig_name] = (ticker, l_date)

    tickers_to_scan = list(set([t[0] for t in resolved_tickers.values()]))
    print(f"Downloading historical daily data for {len(tickers_to_scan)} tickers...")

    data = yf.download(tickers_to_scan, period="1y", interval="1d", progress=True)
    if 'Close' not in data or 'Volume' not in data:
        print("Failed to download price/volume data.")
        return

    closes = data['Close']
    highs = data['High']
    volumes = data['Volume']

    results = []

    for orig_name, (ticker, l_date) in resolved_tickers.items():
        if ticker not in closes.columns or ticker not in volumes.columns:
            continue

        s_close = closes[ticker].dropna()
        s_high = highs[ticker].dropna()
        s_vol = volumes[ticker].dropna()

        if len(s_close) < 30:
            continue

        # Indicators
        sma20 = s_close.rolling(window=20).mean()
        std20 = s_close.rolling(window=20).std()
        upper_bb = sma20 + (2.0 * std20)
        rsi = calculate_rsi(s_close, period=14)
        vol_sma20 = s_vol.rolling(window=20).mean()

        c_curr = float(s_close.iloc[-1])
        c_prev = float(s_close.iloc[-2])

        ubb_curr = float(upper_bb.iloc[-1])
        ubb_prev = float(upper_bb.iloc[-2])

        sma20_curr = float(sma20.iloc[-1])

        rsi_curr = float(rsi.iloc[-1])
        rsi_prev = float(rsi.iloc[-2])

        v_curr = float(s_vol.iloc[-1])
        v_sma_curr = float(vol_sma20.iloc[-1])
        vol_mult = (v_curr / v_sma_curr) if v_sma_curr > 0 else 1.0

        prev_max_high = float(s_high.iloc[:-1].max())
        pct_from_ath = ((c_curr - prev_max_high) / prev_max_high) * 100.0

        if np.isnan(c_curr) or np.isnan(ubb_curr) or np.isnan(rsi_curr):
            continue

        bb_cross = (c_prev <= ubb_prev) and (c_curr > ubb_curr)
        bb_above = c_curr > ubb_curr

        rsi_cross = (rsi_prev <= 60.0) and (rsi_curr > 60.0)
        rsi_above = rsi_curr > 60.0

        vol_spike = vol_mult >= 1.5

        if bb_above and rsi_above:
            bb_diff_pct = ((c_curr - ubb_curr) / ubb_curr) * 100.0

            # Calculate Risk & Reward
            stop_loss = round(sma20_curr, 2)  # 20 SMA / Middle BB as Stop-Loss
            risk_per_share = round(c_curr - stop_loss, 2)
            target_1 = round(c_curr + (1.5 * risk_per_share), 2)  # 1.5 R:R Target
            target_2 = round(c_curr + (2.5 * risk_per_share), 2)  # 2.5 R:R Target
            risk_reward_ratio = round((target_1 - c_curr) / max(risk_per_share, 0.01), 2)

            # Institutional Strength Score (0 to 100)
            score = 50
            if bb_cross: score += 15
            if rsi_cross: score += 15
            if vol_mult >= 2.0: score += 15
            elif vol_mult >= 1.5: score += 10
            if pct_from_ath >= -0.5: score += 10

            score = min(score, 100)

            # Signal Tag
            if bb_cross and rsi_cross and vol_spike:
                signal_tag = "[INSTITUTIONAL DUAL CROSS] HIGH VOLUME BREAKOUT"
            elif bb_cross and rsi_cross:
                signal_tag = "[DUAL CROSS] BB & RSI 60 CROSSOVER"
            elif vol_spike:
                signal_tag = "[VOLUME SPIKE] BREAKOUT WITH 1.5x+ VOLUME"
            else:
                signal_tag = "[BULLISH BREAKOUT] ACTIVE CLOSE > UPPER BB & RSI > 60"

            results.append({
                "Company_Name": orig_name,
                "Ticker": ticker,
                "Listed_Date": l_date,
                "Close": round(c_curr, 2),
                "Upper_BB": round(ubb_curr, 2),
                "BB_Diff_%": round(bb_diff_pct, 2),
                "RSI": round(rsi_curr, 2),
                "Volume_Multiplier": round(vol_mult, 2),
                "Vol_Spike": "YES" if vol_spike else "NO",
                "ATH_Diff_%": round(pct_from_ath, 2),
                "Stop_Loss": stop_loss,
                "Target_1": target_1,
                "Target_2": target_2,
                "Strength_Score": score,
                "Signal_Tag": signal_tag
            })

    if not results:
        print("No matching breakout stocks found.")
        return

    df_res = pd.DataFrame(results)
    df_res = df_res.sort_values(by=["Strength_Score", "RSI"], ascending=[False, False])
    df_res.to_csv("master_scan_results.csv", index=False)

    print("\n" + "=" * 80)
    print(f" MASTER BREAKOUT SCAN RESULTS: {len(df_res)} STOCKS FOUND")
    print(" Results saved to 'master_scan_results.csv'")
    print("=" * 80)
    
    cols = ["Company_Name", "Ticker", "Close", "Upper_BB", "RSI", "Volume_Multiplier", "Stop_Loss", "Target_1", "Strength_Score", "Signal_Tag"]
    print(df_res[cols].head(15).to_string(index=False))

if __name__ == "__main__":
    main()
