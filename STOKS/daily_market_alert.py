import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import os
import requests
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration (Optional: User can set token & chat_id)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

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
    """Calculate RSI with period = 9 (Fast Momentum)."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def send_telegram_alert(message, token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID):
    if not token or not chat_id:
        print("[Telegram Info] Token/Chat_ID not set. Daily alert summary preview below:")
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        res = requests.post(url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")
        return False

def run_daily_market_close_alert():
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    date_filename = datetime.datetime.now().strftime('%Y-%m-%d')
    
    print("=" * 80)
    print(" DAILY MARKET CLOSE BREAKOUT SCANNER (RSI 9 > 60 & UPPER BB) ")
    print(" Universes: BSE Main Board IPOs (2022-2026) + NSE Main Board IPOs (2022-2026)")
    print(f" Timestamp: {now_str}")
    print("=" * 80)

    os.makedirs("alerts", exist_ok=True)

    excel_path = r'd:\STOKS\BSE MAIN BOARD IPO.xlsx'
    df_raw = pd.read_excel(excel_path)
    df_raw.columns = [str(c).strip() for c in df_raw.iloc[0]]
    df_ipo = df_raw.iloc[1:].reset_index(drop=True)
    df_ipo['Listed On'] = pd.to_datetime(df_ipo['Listed On'], errors='coerce')
    
    # Filter 2022 to 2026 IPOs
    filtered_ipo = df_ipo[(df_ipo['Listed On'] >= '2022-01-01') & (df_ipo['Listed On'] <= '2026-08-16')].copy()
    print(f"Total BSE/NSE Main Board IPOs (2022-2026) loaded: {len(filtered_ipo)}")
    
    company_list = []
    for idx, row in filtered_ipo.iterrows():
        c_name = str(row['Company Name']).strip()
        l_date = row['Listed On'].strftime('%Y-%m-%d') if pd.notnull(row['Listed On']) else 'N/A'
        if c_name and c_name != 'nan':
            clean_n = clean_company_name(c_name)
            company_list.append((idx, c_name, clean_n, l_date))

    print("Resolving BSE & NSE exchange tickers...")
    all_targets = {}
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(search_ticker, (c[0], c[1], c[2])) for c in company_list]
        for f in as_completed(futures):
            idx, orig_name, ticker = f.result()
            if ticker:
                l_date = next((item[3] for item in company_list if item[1] == orig_name), 'N/A')
                exch_label = "NSE Main Board IPO" if ticker.endswith('.NS') else "BSE Main Board IPO"
                all_targets[ticker] = (orig_name, l_date, exch_label)

    unique_tickers = list(all_targets.keys())
    print(f"Downloading price & volume data for {len(unique_tickers)} IPO tickers...")

    data = yf.download(unique_tickers, period="60d", interval="1d", progress=False)
    if 'Close' not in data or 'Volume' not in data:
        print("Failed to download price data.")
        return

    closes = data['Close']
    highs = data['High']
    lows = data['Low']
    volumes = data['Volume']

    alerts = []

    for ticker, (disp_name, l_date, u_name) in all_targets.items():
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

        # RSI (9) FAST MOMENTUM
        rsi9 = calculate_rsi(s_close, period=9)
        rsi9_curr = float(rsi9.iloc[-1])
        rsi9_prev = float(rsi9.iloc[-2])

        vol_sma20 = s_vol.rolling(20).mean()
        v_curr = float(s_vol.iloc[-1])
        v_sma_curr = float(vol_sma20.iloc[-1])
        vol_mult = (v_curr / v_sma_curr) if v_sma_curr > 0 else 1.0

        if np.isnan(c_curr) or np.isnan(ubb_curr) or np.isnan(rsi9_curr):
            continue

        # Crossover & Active Conditions
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

            alerts.append({
                "Date": date_filename,
                "Company_Name": disp_name,
                "Ticker": ticker,
                "Universe": u_name,
                "Listed_Date": l_date,
                "Close": round(c_curr, 2),
                "Upper_BB": round(ubb_curr, 2),
                "RSI_9": round(rsi9_curr, 2),
                "Prev_RSI_9": round(rsi9_prev, 2),
                "Volume_Spike": f"{round(vol_mult, 2)}x",
                "Stop_Loss": sl_price,
                "Target_1": target_1,
                "Target_1_Gain_%": f"+{t1_gain}%",
                "Target_2": target_2,
                "Target_2_Gain_%": f"+{t2_gain}%",
                "Strength_Score": score
            })

    if not alerts:
        print("No breakout alerts triggered today with RSI(9) > 60 & Upper BB.")
        return

    alert_df = pd.DataFrame(alerts).sort_values(by=["Strength_Score", "RSI_9"], ascending=[False, False])
    alert_csv = f"alerts/alert_{date_filename}.csv"
    
    try:
        alert_df.to_csv(alert_csv, index=False)
        alert_df.to_csv("price_action_targets.csv", index=False)
    except Exception as e:
        alert_df.to_csv(f"alerts/alert_rsi9_{date_filename}.csv", index=False)

    print(f"\nSaved {len(alert_df)} IPO breakout alerts (RSI 9 > 60) to '{alert_csv}'")

    print("\n" + "=" * 80)
    print(" BSE & NSE MAIN BOARD IPO (2022-2026) BREAKOUT ALERTS (RSI 9 > 60):")
    print("=" * 80)
    cols = ["Company_Name", "Ticker", "Universe", "Close", "Upper_BB", "RSI_9", "Volume_Spike", "Stop_Loss", "Target_1", "Target_1_Gain_%"]
    print(alert_df[cols].to_string(index=False))

if __name__ == "__main__":
    run_daily_market_close_alert()
