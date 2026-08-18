import pandas as pd
import numpy as np
import yfinance as yf
import datetime
import os
import sys

from config import BASE_DIR
from quant_engine import analyze_stock_quant, calculate_rsi
from data_engine import load_ipo_universe_5y, fetch_market_data
from generate_production_excel import generate_production_excel
from build_premium_dashboard import build_dashboard
from prod_logger import log_info, log_error

# V4.0 New Modules (imported safely so pipeline continues even if they fail)
try:
    from sector_map import build_sector_heatmap
except Exception:
    build_sector_heatmap = None
try:
    from backtest_engine import run_backtest
except Exception:
    run_backtest = None
try:
    from ipo_performance import build_ipo_performance
except Exception:
    build_ipo_performance = None
try:
    from ai_engine import run_ai_engine
except Exception:
    run_ai_engine = None
try:
    from fii_dii_engine import fetch_fii_dii_flows
except Exception:
    fetch_fii_dii_flows = None
try:
    from news_engine import fetch_live_market_news
except Exception:
    fetch_live_market_news = None
try:
    from alerts.alert_dispatcher import dispatch_alerts
except Exception:
    dispatch_alerts = None

NSE_STOCKS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "BHARTIARTL", "SBIN", "LTIM", "LT", "ITC",
    "SUNPHARMA", "HCLTECH", "KOTAKBANK", "M&M", "AXISBANK", "MARUTI", "NTPC", "ULTRACEMCO", "ASIANPAINT", "TITAN",
    "BAJFINANCE", "POWERGRID", "TATASTEEL", "COALINDIA", "ADANIENT", "ADANIPORTS", "ONGC", "JSWSTEEL", "HINDUNILVR", "WIPRO",
    "NESTLEIND", "TRENT", "BEL", "HAL", "SIEMENS", "ABB", "ZOMATO", "VBL", "CHOLAFIN", "IOC",
    "REC", "PFC", "DLF", "GAIL", "BPCL", "INDIGO", "CIPLA", "DRREDDY", "DIVISLAB", "EICHERMOT",
    "HEROMOTOCO", "BAJAJ-AUTO", "GRASIM", "BRITANNIA", "TECHM", "HDFCLIFE", "SBILIFE", "ICICIPRULI", "TATACONSUM", "APOLLOHOSP",
    "HINDALCO", "BANKBARODA", "PNB", "IDFCFIRSTB", "CANBK", "UNIONBANK", "BHEL", "HINDZINC", "NMDC", "SAIL",
    "VEDL", "INDUSTOWER", "POLYCAB", "KEI", "DIXON", "TATAELXSI", "PERSISTENT", "COFORGE", "MPHASIS", "OFSS",
    "HDFCAMC", "NAM-INDIA", "CDSL", "BSE", "MCX", "IRCTC", "IRFC", "RVNL", "RAILTEL", "MAZDOCK"
]

def save_csv_safe(df, filepath):
    try:
        df.to_csv(filepath, index=False)
        return filepath
    except Exception:
        base, ext = os.path.splitext(filepath)
        alt = f"{base}_v3{ext}"
        df.to_csv(alt, index=False)
        return alt

def run_production_pipeline():
    log_info("=" * 80)
    log_info(" STOKS V4.0 — ENTERPRISE PRODUCTION BREAKOUT SUITE ")
    log_info(" Parameters: RSI(9) Fast Momentum + BB(20,2) + ATR SL + Charts + Heatmap + Backtest")
    log_info("=" * 80)

    # 1. Load IPO Universe 5Y
    ipo_map = load_ipo_universe_5y()
    log_info(f"Resolved {len(ipo_map)} Main Board IPOs listed within last 5 years (2021-2026)")

    all_targets = {}
    for name, (ticker, l_date, exch) in ipo_map.items():
        all_targets[ticker] = (name, l_date, exch)

    for n_sym in NSE_STOCKS:
        t = f"{n_sym}.NS"
        if t not in all_targets:
            all_targets[t] = (n_sym, "Prior to 2021", "NSE Top Stock")

    unique_tickers = list(all_targets.keys())
    log_info(f"Combined Universe Total Tickers: {len(unique_tickers)}")

    # STAGE 1: Daily Quantitative Analysis & Targets
    log_info("STAGE 1: Downloading 60-day daily market data...")
    d_data = fetch_market_data(unique_tickers, period="60d", interval="1d")

    daily_results = []
    ipo_5y_results = []

    if d_data is not None and 'Close' in d_data and 'Volume' in d_data:
        closes = d_data['Close']
        highs = d_data['High']
        lows = d_data['Low']
        volumes = d_data['Volume']

        for ticker, (disp_name, l_date, u_name) in all_targets.items():
            if ticker not in closes.columns or ticker not in volumes.columns:
                continue

            s_close = closes[ticker].dropna()
            s_high = highs[ticker].dropna()
            s_low = lows[ticker].dropna()
            s_vol = volumes[ticker].dropna()

            res = analyze_stock_quant(s_close, s_high, s_low, s_vol, ticker, disp_name, l_date, u_name)
            if res:
                daily_results.append(res)
                if u_name in ["NSE Main Board", "BSE Main Board", "BSE Main Board IPO", "NSE Main Board IPO"]:
                    res_5y = dict(res)
                    res_5y["Exchange"] = u_name
                    ipo_5y_results.append(res_5y)

    df_daily = pd.DataFrame(daily_results).sort_values(by=["Strength_Score", "RSI_9"], ascending=[False, False]) if daily_results else pd.DataFrame()
    df_5y = pd.DataFrame(ipo_5y_results).sort_values(by=["Strength_Score", "RSI_9"], ascending=[False, False]) if ipo_5y_results else pd.DataFrame()

    save_csv_safe(df_daily, "master_scan_results.csv")
    save_csv_safe(df_daily, "price_action_targets.csv")
    save_csv_safe(df_5y, "recent_ipo_breakouts_5y.csv")

    log_info(f"STAGE 1 Complete: {len(df_daily)} daily breakouts & {len(df_5y)} 5-Year IPO breakouts detected!")

    # STAGE 2: Monthly ATH Breakout Analysis
    log_info("STAGE 2: Downloading Monthly Timeframe Data...")
    m_data = fetch_market_data(unique_tickers, period="max", interval="1mo")

    monthly_results = []
    if m_data is not None and 'Close' in m_data and 'High' in m_data:
        m_closes = m_data['Close']
        m_highs = m_data['High']

        for ticker, (disp_name, l_date, u_name) in all_targets.items():
            if ticker not in m_closes.columns or ticker not in m_highs.columns:
                continue

            s_close = m_closes[ticker].dropna()
            s_high = m_highs[ticker].dropna()

            if len(s_close) < 6:
                continue

            curr_close = float(s_close.iloc[-1])
            curr_high = float(s_high.iloc[-1])

            prev_max_close = float(s_close.iloc[:-1].max())
            prev_max_high = float(s_high.iloc[:-1].max())

            if prev_max_high <= 0:
                continue

            m_rsi_series = calculate_rsi(s_close, period=9)
            m_rsi_val = float(m_rsi_series.iloc[-1]) if not m_rsi_series.empty and not np.isnan(m_rsi_series.iloc[-1]) else 0.0

            pct_diff_high = round(((curr_close - prev_max_high) / prev_max_high) * 100.0, 2)

            is_fresh_high_breakout = curr_close >= prev_max_high or curr_high >= prev_max_high
            is_fresh_close_breakout = curr_close >= prev_max_close

            if is_fresh_high_breakout or is_fresh_close_breakout or (pct_diff_high >= -1.0):
                if curr_close >= prev_max_high:
                    category = "FRESH MONTHLY ATH HIGH & CLOSE"
                    priority = 1
                elif is_fresh_close_breakout:
                    category = "FRESH MONTHLY ATH CLOSE"
                    priority = 2
                else:
                    category = "MONTHLY ATH TOUCHED / RESISTANCE"
                    priority = 3

                monthly_results.append({
                    "Company_Name": disp_name,
                    "Ticker": ticker,
                    "Universe": u_name,
                    "Listed_Date": l_date,
                    "Monthly_Close": round(curr_close, 2),
                    "Monthly_High": round(curr_high, 2),
                    "Prev_Monthly_ATH_High": round(prev_max_high, 2),
                    "Monthly_ATH_Diff_Pct": f"{'+' if pct_diff_high >= 0 else ''}{pct_diff_high}%",
                    "Monthly_RSI_9": round(m_rsi_val, 2),
                    "Breakout_Category": category,
                    "Priority": priority
                })

    df_monthly = pd.DataFrame(monthly_results).sort_values(by=["Priority", "Monthly_Close"], ascending=[True, False]) if monthly_results else pd.DataFrame()
    save_csv_safe(df_monthly, "monthly_ath_breakouts.csv")
    log_info(f"STAGE 2 Complete: {len(df_monthly)} monthly ATH breakouts detected!")

    # STAGE 3: Build Master Excel Report
    log_info("STAGE 3: Generating Production Master Excel Report...")
    generate_production_excel()

    # STAGE 5: Sector Heatmap
    log_info("STAGE 5: Building Sector Heatmap Data...")
    if build_sector_heatmap:
        try:
            build_sector_heatmap()
            log_info("STAGE 5 Complete: Sector heatmap data generated.")
        except Exception as e:
            log_error(f"STAGE 5 Warning: Sector heatmap failed (non-critical): {e}")
    else:
        log_info("STAGE 5 Skipped: sector_map module not available.")

    # STAGE 6: Backtesting Engine
    log_info("STAGE 6: Running Historical Backtesting...")
    if run_backtest:
        try:
            run_backtest()
            log_info("STAGE 6 Complete: Backtesting results generated.")
        except Exception as e:
            log_error(f"STAGE 6 Warning: Backtesting failed (non-critical): {e}")
    else:
        log_info("STAGE 6 Skipped: backtest_engine module not available.")

    # STAGE 7: IPO Performance Tracker
    log_info("STAGE 7: Building IPO Performance Tracker...")
    if build_ipo_performance:
        try:
            build_ipo_performance()
            log_info("STAGE 7 Complete: IPO performance data generated.")
        except Exception as e:
            log_error(f"STAGE 7 Warning: IPO tracker failed (non-critical): {e}")
    else:
        log_info("STAGE 7 Skipped: ipo_performance module not available.")

    # STAGE 9: FII / DII Net Flow Engine
    log_info("STAGE 9: Fetching FII / DII Institutional Flows...")
    if fetch_fii_dii_flows:
        try:
            fetch_fii_dii_flows()
            log_info("STAGE 9 Complete: FII/DII flow data generated.")
        except Exception as e:
            log_error(f"STAGE 9 Warning: FII/DII engine failed (non-critical): {e}")

    # STAGE 10: Live Stock News & Catalyst Engine
    log_info("STAGE 10: Fetching Live Stock News & Catalysts...")
    if fetch_live_market_news:
        try:
            fetch_live_market_news()
            log_info("STAGE 10 Complete: Stock news data generated.")
        except Exception as e:
            log_error(f"STAGE 10 Warning: News engine failed (non-critical): {e}")

    # STAGE 8: AI Smart Analysis Engine
    log_info("STAGE 8: Running AI Smart Analysis Engine...")
    if run_ai_engine:
        try:
            run_ai_engine()
            log_info("STAGE 8 Complete: AI analysis report generated.")
        except Exception as e:
            log_error(f"STAGE 8 Warning: AI engine failed (non-critical): {e}")
    else:
        log_info("STAGE 8 Skipped: ai_engine module not available.")

    # STAGE 11: Alert Dispatcher
    log_info("STAGE 11: Dispatching Breakout Alerts...")
    if dispatch_alerts:
        try:
            dispatch_alerts()
            log_info("STAGE 11 Complete: Alerts dispatched.")
        except Exception as e:
            log_error(f"STAGE 11 Warning: Alert dispatcher failed (non-critical): {e}")

    # STAGE 4: Build Web Dashboard (runs LAST so all data files are ready)
    log_info("STAGE 4: Regenerating STOKS V4.2 Workstation Dashboard...")
    build_dashboard()

    log_info("=" * 80)
    log_info(" STOKS V4.2 ENTERPRISE PIPELINE FINISHED SUCCESSFULLY!")
    log_info("=" * 80)

if __name__ == "__main__":
    run_production_pipeline()
