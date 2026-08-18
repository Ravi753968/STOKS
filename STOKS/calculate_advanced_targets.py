import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import os
import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def main():
    print("=" * 80)
    print(" ADVANCED TARGET CALCULATOR (PRICE ACTION + VOLUME MULTIPLIER + ATH) ")
    print(f" Date & Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Load master breakout results if available or scan
    if not os.path.exists("master_scan_results.csv"):
        print("master_scan_results.csv not found.")
        return

    df = pd.read_csv("master_scan_results.csv")
    tickers = df['Ticker'].unique().tolist()

    print(f"Downloading deep price action & volume data for {len(tickers)} stocks...")
    data = yf.download(tickers, period="6mo", interval="1d", progress=True)

    if 'Close' not in data or 'High' not in data or 'Low' not in data or 'Volume' not in data:
        print("Failed to download price data.")
        return

    closes = data['Close']
    highs = data['High']
    lows = data['Low']
    volumes = data['Volume']

    results = []

    for idx, row in df.iterrows():
        ticker = row['Ticker']
        c_name = row['Company_Name']

        if ticker not in closes.columns:
            continue

        s_close = closes[ticker].dropna()
        s_high = highs[ticker].dropna()
        s_low = lows[ticker].dropna()
        s_vol = volumes[ticker].dropna()

        if len(s_close) < 20:
            continue

        c_curr = float(s_close.iloc[-1])
        h_curr = float(s_high.iloc[-1])
        l_curr = float(s_low.iloc[-1])
        v_curr = float(s_vol.iloc[-1])

        # 20 SMA & Middle BB
        sma20 = float(s_close.rolling(20).mean().iloc[-1])
        std20 = float(s_close.rolling(20).std().iloc[-1])
        upper_bb = sma20 + (2.0 * std20)

        # Volume Multiplier
        v_sma20 = float(s_vol.rolling(20).mean().iloc[-1])
        vol_mult = (v_curr / v_sma20) if v_sma20 > 0 else 1.0

        # Price Action Metrics (Swing Range & ATR)
        recent_20_low = float(s_low.tail(20).min())
        recent_20_high = float(s_high.tail(20).max())
        swing_range = recent_20_high - recent_20_low

        # Stop Loss: 20 SMA or 3% below entry (whichever is safer)
        sl_price = round(max(sma20, c_curr * 0.94), 2)
        risk = round(c_curr - sl_price, 2)

        # Targets based on Price Action (Fib Extension + Volume Boost)
        # Base Reward = 1.5x Risk (Fibonacci 1.272)
        fib_boost = 1.0
        if vol_mult >= 5.0:
            fib_boost = 1.15  # +15% target boost for massive institutional volume
        elif vol_mult >= 2.0:
            fib_boost = 1.08  # +8% target boost for strong volume

        # Target 1 (Conservative Price Action Target: 1.5x R:R + Volume Boost)
        target_1 = round(c_curr + (1.5 * risk * fib_boost), 2)
        t1_upside_pct = round(((target_1 - c_curr) / c_curr) * 100.0, 2)

        # Target 2 (Aggressive Momentum / ATH Extension Target: 2.5x R:R + Volume Boost)
        target_2 = round(c_curr + (2.5 * risk * fib_boost), 2)
        t2_upside_pct = round(((target_2 - c_curr) / c_curr) * 100.0, 2)

        # Risk-to-Reward Ratio
        rr_ratio = round((target_1 - c_curr) / max(risk, 0.01), 2)

        results.append({
            "Company_Name": c_name,
            "Ticker": ticker,
            "Entry_Price": round(c_curr, 2),
            "Upper_BB": round(upper_bb, 2),
            "RSI": row['RSI'],
            "Volume_Spike": f"{round(vol_mult, 2)}x",
            "Stop_Loss": sl_price,
            "Risk_Per_Share": risk,
            "Target_1": target_1,
            "Target_1_Gain_%": f"+{t1_upside_pct}%",
            "Target_2": target_2,
            "Target_2_Gain_%": f"+{t2_upside_pct}%",
            "Risk_Reward": f"1:{rr_ratio}",
            "Strength_Score": row['Strength_Score'],
            "Signal_Tag": row['Signal_Tag']
        })

    res_df = pd.DataFrame(results)
    res_df = res_df.sort_values(by=["Strength_Score", "Entry_Price"], ascending=[False, False])
    res_df.to_csv("price_action_targets.csv", index=False)

    print("\n" + "=" * 80)
    print(" ADVANCED TARGET ANALYSIS (PRICE ACTION + VOLUME SPIKE + R:R) ")
    print(" Results saved to 'price_action_targets.csv'")
    print("=" * 80)
    
    cols = ["Company_Name", "Ticker", "Entry_Price", "Volume_Spike", "Stop_Loss", "Target_1", "Target_1_Gain_%", "Target_2", "Target_2_Gain_%", "Risk_Reward"]
    print(res_df[cols].head(15).to_string(index=False))

if __name__ == "__main__":
    main()
