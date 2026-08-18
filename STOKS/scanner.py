import yfinance as yf
import pandas as pd
import numpy as np
import datetime

# Universe of top NIFTY 100 / NIFTY 200 & F&O stocks on NSE
STOCKS = [
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

def calculate_rsi_series(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def main():
    print("=" * 80)
    print(" STOCK SCANNER: CLOSE > UPPER BOLLINGER BAND & RSI > 60 CROSSOVER ")
    print(" Universe: NSE Top 150+ Stocks")
    print(f" Date & Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    tickers = [f"{s}.NS" for s in STOCKS]
    print(f"Downloading historical daily data for {len(tickers)} stocks...")
    
    # Download batch data
    data = yf.download(tickers, period="60d", interval="1d", progress=True)
    if 'Close' not in data:
        print("Failed to retrieve Close price data.")
        return
        
    closes = data['Close']
    
    results = []
    
    for symbol in STOCKS:
        ticker = f"{symbol}.NS"
        if ticker not in closes.columns:
            continue
            
        s_close = closes[ticker].dropna()
        if len(s_close) < 25:
            continue
            
        # 1. Bollinger Bands (20, 2)
        sma20 = s_close.rolling(window=20).mean()
        std20 = s_close.rolling(window=20).std()
        upper_bb = sma20 + (2.0 * std20)
        
        # 2. RSI (14)
        rsi = calculate_rsi_series(s_close, period=14)
        
        # Get latest (t) and previous (t-1) values
        c_curr = float(s_close.iloc[-1])
        c_prev = float(s_close.iloc[-2])
        
        ubb_curr = float(upper_bb.iloc[-1])
        ubb_prev = float(upper_bb.iloc[-2])
        
        rsi_curr = float(rsi.iloc[-1])
        rsi_prev = float(rsi.iloc[-2])
        
        if np.isnan(c_curr) or np.isnan(ubb_curr) or np.isnan(rsi_curr):
            continue
            
        # Crossover Conditions:
        # A. Close Cross Above Upper BB
        bb_cross = (c_prev <= ubb_prev) and (c_curr > ubb_curr)
        bb_above = c_curr > ubb_curr
        
        # B. RSI Cross Above 60
        rsi_cross = (rsi_prev <= 60.0) and (rsi_curr > 60.0)
        rsi_above = rsi_curr > 60.0
        
        # Filter matching criteria
        if bb_above and rsi_above:
            # Calculate % above Upper BB
            bb_diff_pct = ((c_curr - ubb_curr) / ubb_curr) * 100.0
            
            # Classification
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
                "Symbol": symbol,
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
        print("\nNo stocks currently match both criteria (Close > Upper BB AND RSI > 60).")
        return
        
    res_df = pd.DataFrame(results)
    res_df = res_df.sort_values(by=["Priority", "RSI"], ascending=[True, False])
    
    # Save to CSV
    res_df.to_csv("scan_results.csv", index=False)
    
    # Format display
    dual_cross = res_df[res_df['Priority'] == 1]
    fresh_cross = res_df[res_df['Priority'].isin([2, 3])]
    active_breakouts = res_df[res_df['Priority'] == 4]
    
    print("\n" + "=" * 80)
    print(" 1. PERFECT DUAL CROSSOVERS (Both BB & RSI 60 Crossed On Latest Session)")
    print("=" * 80)
    if not dual_cross.empty:
        print(dual_cross[["Symbol", "Close", "Upper_BB", "BB_Diff_%", "RSI", "Prev_RSI", "Category"]].to_string(index=False))
    else:
        print("No stocks triggered a dual crossover on the exact latest trading session.")

    print("\n" + "=" * 80)
    print(" 2. FRESH CROSSOVER STOCKS (One Indicator Crossed Today, Other Active)")
    print("=" * 80)
    if not fresh_cross.empty:
        print(fresh_cross[["Symbol", "Close", "Upper_BB", "BB_Diff_%", "RSI", "Prev_RSI", "Category"]].to_string(index=False))
    else:
        print("No fresh single crossover stocks found today.")

    print("\n" + "=" * 80)
    print(" 3. ALL ACTIVE BREAKOUT STOCKS (Close > Upper BB & RSI > 60 Active)")
    print("=" * 80)
    if not active_breakouts.empty:
        print(active_breakouts[["Symbol", "Close", "Upper_BB", "BB_Diff_%", "RSI", "Prev_RSI", "Category"]].to_string(index=False))
    else:
        print("No active breakout stocks found.")

    print("\n" + "=" * 80)
    print(f" TOTAL MATCHES FOUND: {len(res_df)} stocks")
    print(" Summary saved to 'scan_results.csv'")
    print("=" * 80)

if __name__ == "__main__":
    main()
