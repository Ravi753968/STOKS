import pandas as pd
import numpy as np

def calculate_rsi(series, period=9):
    """Calculate Relative Strength Index with period=9 (Fast Momentum)."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)

def calculate_atr(df, period=14):
    """Calculate Average True Range (ATR)."""
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean().fillna(0.0)

def analyze_stock_quant(s_close, s_high, s_low, s_vol, ticker, orig_name, l_date, u_name):
    """Production Quantitative Analysis for single ticker."""
    if len(s_close) < 20:
        return None

    c_curr = float(s_close.iloc[-1])
    c_prev = float(s_close.iloc[-2])

    sma20 = s_close.rolling(20).mean()
    std20 = s_close.rolling(20).std()
    upper_bb = sma20 + (2.0 * std20)
    lower_bb = sma20 - (2.0 * std20)

    ubb_curr = float(upper_bb.iloc[-1])
    ubb_prev = float(upper_bb.iloc[-2])
    sma20_curr = float(sma20.iloc[-1])

    # BB Bandwidth Squeeze & Expansion Ratio
    bb_width = (upper_bb - lower_bb) / sma20
    bb_width_curr = float(bb_width.iloc[-1])
    bb_width_min20 = float(bb_width.rolling(20).min().iloc[-1])
    is_expanding = bb_width_curr > bb_width_min20

    # RSI (9) Fast Momentum + Slope
    rsi9 = calculate_rsi(s_close, period=9)
    rsi9_curr = float(rsi9.iloc[-1])
    rsi9_prev = float(rsi9.iloc[-2])
    rsi_slope = rsi9_curr - rsi9_prev

    # Volume Spike & Z-Score
    vol_sma20 = s_vol.rolling(20).mean()
    vol_std20 = s_vol.rolling(20).std()
    v_curr = float(s_vol.iloc[-1])
    v_sma_curr = float(vol_sma20.iloc[-1])
    vol_mult = (v_curr / v_sma_curr) if v_sma_curr > 0 else 1.0
    vol_zscore = ((v_curr - v_sma_curr) / vol_std20.iloc[-1]) if vol_std20.iloc[-1] > 0 else 0.0

    if np.isnan(c_curr) or np.isnan(ubb_curr) or np.isnan(rsi9_curr):
        return None

    # Core Breakout Signals
    bb_cross = (c_prev <= ubb_prev) and (c_curr > ubb_curr)
    bb_above = c_curr > ubb_curr
    rsi_above = rsi9_curr > 60.0

    if bb_above and rsi_above:
        # Dynamic ATR Trailing Stop Loss
        df_tmp = pd.DataFrame({'High': s_high, 'Low': s_low, 'Close': s_close})
        atr14 = float(calculate_atr(df_tmp, 14).iloc[-1])
        
        sl_sma = sma20_curr
        sl_atr = c_curr - (2.0 * atr14)
        sl_price = round(max(sl_sma, sl_atr, c_curr * 0.93), 2)
        risk = round(c_curr - sl_price, 2)
        if risk <= 0:
            risk = round(c_curr * 0.04, 2)

        vol_boost = 1.15 if vol_mult >= 5.0 else (1.08 if vol_mult >= 2.0 else 1.0)
        
        target_1 = round(c_curr + (1.5 * risk * vol_boost), 2)
        t1_gain = round(((target_1 - c_curr) / c_curr) * 100.0, 2)

        target_2 = round(c_curr + (2.5 * risk * vol_boost), 2)
        t2_gain = round(((target_2 - c_curr) / c_curr) * 100.0, 2)

        target_3 = round(c_curr + (4.0 * risk * vol_boost), 2)
        t3_gain = round(((target_3 - c_curr) / c_curr) * 100.0, 2)

        rr_ratio = round((target_1 - c_curr) / max(risk, 0.01), 2)

        # Production Composite Institutional Score (0 to 100)
        score = 50
        if bb_cross: score += 15
        if rsi9_curr >= 75.0: score += 15
        elif rsi9_curr >= 65.0: score += 10
        if rsi_slope > 0: score += 5
        if vol_mult >= 5.0: score += 15
        elif vol_mult >= 2.0: score += 10
        if is_expanding: score += 5
        score = min(score, 100)

        return {
            "Company_Name": orig_name,
            "Ticker": ticker,
            "Universe": u_name,
            "Listed_Date": l_date,
            "Close": round(c_curr, 2),
            "Upper_BB": round(ubb_curr, 2),
            "RSI_9": round(rsi9_curr, 2),
            "RSI_Slope": round(rsi_slope, 2),
            "Volume_Spike": f"{round(vol_mult, 2)}x",
            "Vol_ZScore": round(vol_zscore, 2),
            "ATR_14": round(atr14, 2),
            "Stop_Loss": sl_price,
            "Target_1": target_1,
            "Target_1_Gain_%": f"+{t1_gain}%",
            "Target_2": target_2,
            "Target_2_Gain_%": f"+{t2_gain}%",
            "Target_3": target_3,
            "Target_3_Gain_%": f"+{t3_gain}%",
            "Risk_Reward": f"1:{rr_ratio}",
            "Strength_Score": score
        }
    return None
