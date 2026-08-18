"""
STOKS V4.0 — Backtesting Engine
Simulates RSI(9) > 60 + Bollinger Band Breakout strategy on 1-year historical data.
Computes: Win Rate, Avg Gain, Max Drawdown, Avg Days to Target.
"""
import pandas as pd
import yfinance as yf
import numpy as np
import json
import os
import time
from prod_logger import logger


def compute_rsi(series, period=9):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_bb(series, period=20, std_dev=2.0):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + std_dev * std
    return upper


def backtest_ticker(ticker, company_name):
    """Backtest RSI(9)+BB strategy on 1 year of historical data for one ticker."""
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
        if df is None or len(df) < 30:
            return None

        df = df.reset_index()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df["RSI9"] = compute_rsi(df["Close"])
        df["Upper_BB"] = compute_bb(df["Close"])
        df = df.dropna(subset=["RSI9", "Upper_BB"]).reset_index(drop=True)

        trades = []
        in_trade = False
        entry_price = 0.0
        entry_date = None
        entry_idx = 0

        for i in range(1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i - 1]

            if not in_trade:
                # Entry signal: Close > Upper BB AND RSI(9) > 60
                if (row["Close"] > row["Upper_BB"]) and (row["RSI9"] > 60):
                    in_trade = True
                    entry_price = float(row["Close"])
                    entry_date = str(row["Date"])[:10]
                    entry_idx = i

                    # Precompute stop/targets
                    atr_window = df["Close"].iloc[max(0, i-14):i]
                    atr_est = float(atr_window.std()) * 1.5 if len(atr_window) > 5 else entry_price * 0.05
                    stop_loss = entry_price - 2 * atr_est
                    target1 = entry_price * 1.10
                    target2 = entry_price * 1.17
            else:
                # Check exit conditions
                close_price = float(row["Close"])
                days_in_trade = i - entry_idx
                pct_change = (close_price - entry_price) / entry_price * 100

                hit_target1 = close_price >= target1
                hit_stop = close_price <= stop_loss
                max_hold = days_in_trade >= 30  # Max 30 days hold

                if hit_target1 or hit_stop or max_hold:
                    outcome = "WIN" if hit_target1 else ("LOSS" if hit_stop else "TIMEOUT")
                    gain_pct = round(pct_change, 2)
                    trades.append({
                        "Ticker": ticker,
                        "Company": company_name,
                        "Entry_Date": entry_date,
                        "Exit_Date": str(row["Date"])[:10],
                        "Entry_Price": round(entry_price, 2),
                        "Exit_Price": round(close_price, 2),
                        "Gain_Pct": gain_pct,
                        "Days_Held": days_in_trade,
                        "Outcome": outcome,
                    })
                    in_trade = False

        return trades if trades else None

    except Exception as e:
        logger.warning(f"Backtest failed for {ticker}: {e}")
        return None


def run_backtest():
    """Run full backtest across all breakout tickers."""
    logger.info("=" * 60)
    logger.info("STOKS V4.0 — Backtesting Engine Starting...")
    logger.info("=" * 60)

    all_dfs = []
    csv_files = [
        "recent_ipo_breakouts_5y.csv",
        "master_scan_results.csv",
    ]
    for f in csv_files:
        if os.path.exists(f):
            try:
                df = pd.read_csv(f)
                all_dfs.append(df)
            except Exception:
                pass

    if not all_dfs:
        logger.error("No scan data found. Run the main scanner first.")
        return

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["Ticker"]).reset_index(drop=True)
    logger.info(f"Backtesting {len(combined)} tickers over 1-year history...")

    all_trades = []
    for _, row in combined.iterrows():
        ticker = row.get("Ticker", "")
        company = row.get("Company_Name", ticker)
        logger.info(f"  Backtesting: {ticker}...")
        trades = backtest_ticker(ticker, company)
        if trades:
            all_trades.extend(trades)
        time.sleep(0.2)

    if not all_trades:
        logger.warning("No trades generated during backtest.")
        # Write empty results
        summary = {
            "total_trades": 0, "wins": 0, "losses": 0, "timeouts": 0,
            "win_rate_pct": 0, "avg_gain_pct": 0, "avg_loss_pct": 0,
            "avg_days_held": 0, "best_trade_pct": 0, "worst_trade_pct": 0,
            "total_tickers": len(combined),
        }
        with open("backtest_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        pd.DataFrame().to_csv("backtest_results.csv", index=False)
        return

    df_trades = pd.DataFrame(all_trades)
    df_trades.to_csv("backtest_results.csv", index=False)
    logger.info(f"SUCCESS: Saved {len(df_trades)} backtest trades → backtest_results.csv")

    # Compute summary statistics
    wins = df_trades[df_trades["Outcome"] == "WIN"]
    losses = df_trades[df_trades["Outcome"] == "LOSS"]
    timeouts = df_trades[df_trades["Outcome"] == "TIMEOUT"]
    total = len(df_trades)

    win_rate = round(len(wins) / total * 100, 1) if total > 0 else 0
    avg_gain = round(wins["Gain_Pct"].mean(), 2) if len(wins) > 0 else 0
    avg_loss = round(losses["Gain_Pct"].mean(), 2) if len(losses) > 0 else 0
    avg_days = round(df_trades["Days_Held"].mean(), 1)
    best = round(df_trades["Gain_Pct"].max(), 2) if total > 0 else 0
    worst = round(df_trades["Gain_Pct"].min(), 2) if total > 0 else 0
    expectancy = round((win_rate/100 * avg_gain) + ((1 - win_rate/100) * avg_loss), 2)

    summary = {
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "timeouts": len(timeouts),
        "win_rate_pct": win_rate,
        "avg_gain_pct": avg_gain,
        "avg_loss_pct": avg_loss,
        "avg_days_held": avg_days,
        "best_trade_pct": best,
        "worst_trade_pct": worst,
        "expectancy_pct": expectancy,
        "total_tickers": len(combined),
    }

    with open("backtest_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info("=" * 60)
    logger.info("BACKTEST RESULTS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Total Trades    : {total}")
    logger.info(f"  Wins            : {len(wins)}  ({win_rate}%)")
    logger.info(f"  Losses          : {len(losses)}")
    logger.info(f"  Timeouts        : {len(timeouts)}")
    logger.info(f"  Avg Win Gain    : +{avg_gain}%")
    logger.info(f"  Avg Loss        : {avg_loss}%")
    logger.info(f"  Expectancy      : {expectancy}% per trade")
    logger.info(f"  Best Trade      : +{best}%")
    logger.info(f"  Worst Trade     : {worst}%")
    logger.info(f"  Avg Days Held   : {avg_days} days")
    logger.info("=" * 60)

    return summary


if __name__ == "__main__":
    run_backtest()
