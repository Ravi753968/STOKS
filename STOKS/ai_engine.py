"""
STOKS AI — Smart Analysis Engine V1.0
100% Local, No API Key Required.
Generates professional-grade AI stock analysis using rule-based NLP.
"""
import pandas as pd
import json
import os
import math
from datetime import datetime
from prod_logger import log_info, log_error

# Simple logger wrapper for compatibility
class _Logger:
    def info(self, msg):  log_info(msg)
    def warning(self, msg): log_info(f"WARN: {msg}")
    def error(self, msg): log_error(msg)

logger = _Logger()



# ─────────────────────────────────────────────────────────────────────────────
# Signal Tier Classification
# ─────────────────────────────────────────────────────────────────────────────
def classify_tier(score, vol_spike, rsi, rsi_slope):
    """Classify a stock into AI signal tier (1=Premium ... 5=Weak)."""
    try:
        vol = float(str(vol_spike).replace("x", ""))
    except Exception:
        vol = 1.0
    try:
        slope = float(rsi_slope or 0)
    except Exception:
        slope = 0.0

    score = float(score or 70)
    rsi = float(rsi or 60)

    if score >= 90 and vol >= 3.0 and rsi >= 75:
        return 1, "PREMIUM SIGNAL", "#ef4444", "🔴"
    elif score >= 80 and vol >= 2.0 and rsi >= 68:
        return 2, "STRONG SIGNAL", "#f97316", "🟠"
    elif score >= 70 and rsi >= 62:
        return 3, "MODERATE SIGNAL", "#f59e0b", "🟡"
    elif score >= 60:
        return 4, "WATCH SIGNAL", "#10b981", "🟢"
    else:
        return 5, "WEAK SIGNAL", "#64748b", "⚪"


# ─────────────────────────────────────────────────────────────────────────────
# RSI Narrative
# ─────────────────────────────────────────────────────────────────────────────
def rsi_narrative(rsi):
    rsi = float(rsi or 0)
    if rsi >= 90:
        return f"RSI(9) at {rsi} — Extreme overbought (momentum exhaustion zone)"
    elif rsi >= 80:
        return f"RSI(9) at {rsi} — Strongly overbought, high momentum"
    elif rsi >= 70:
        return f"RSI(9) at {rsi} — Overbought momentum, trending strongly"
    elif rsi >= 60:
        return f"RSI(9) at {rsi} — Above trigger threshold, bullish momentum building"
    else:
        return f"RSI(9) at {rsi} — Neutral zone"


def rsi_slope_narrative(slope):
    slope = float(slope or 0)
    if slope >= 10:
        return "RSI slope is steeply rising — fast momentum acceleration"
    elif slope >= 5:
        return "RSI slope is rising — momentum gaining speed"
    elif slope >= 0:
        return "RSI slope is flat-positive — steady momentum"
    else:
        return "RSI slope is declining — momentum may be fading"


# ─────────────────────────────────────────────────────────────────────────────
# Volume Narrative
# ─────────────────────────────────────────────────────────────────────────────
def volume_narrative(vol_spike):
    try:
        vol = float(str(vol_spike).replace("x", ""))
    except Exception:
        vol = 1.0
    if vol >= 10:
        return f"{vol_spike} volume surge — EXTREME institutional activity, rare signal"
    elif vol >= 5:
        return f"{vol_spike} volume surge — Very high institutional buying pressure"
    elif vol >= 3:
        return f"{vol_spike} volume surge — Strong institutional participation"
    elif vol >= 2:
        return f"{vol_spike} volume surge — Above-average institutional activity"
    elif vol >= 1.5:
        return f"{vol_spike} volume surge — Moderate above-average volume"
    else:
        return f"{vol_spike} volume — Below confirmation threshold"


# ─────────────────────────────────────────────────────────────────────────────
# Bollinger Band Narrative
# ─────────────────────────────────────────────────────────────────────────────
def bb_narrative(close, upper_bb):
    try:
        c = float(close or 0)
        u = float(upper_bb or 0)
        if u <= 0:
            return "Bollinger Band data unavailable"
        pct_above = round((c - u) / u * 100, 2)
        if pct_above > 3:
            return f"Price {pct_above}% above Upper BB — strong volatility expansion breakout"
        elif pct_above >= 0:
            return f"Price has crossed above Upper Bollinger Band (₹{round(u, 2)}) — confirmed breakout"
        else:
            return f"Price approaching Upper BB resistance at ₹{round(u, 2)}"
    except Exception:
        return "Bollinger Band: Breakout confirmed"


# ─────────────────────────────────────────────────────────────────────────────
# Risk Warnings
# ─────────────────────────────────────────────────────────────────────────────
def generate_risk_warnings(rsi, vol_spike, score, rsi_slope):
    warnings = []
    rsi = float(rsi or 0)
    slope = float(rsi_slope or 0)
    try:
        vol = float(str(vol_spike).replace("x", ""))
    except Exception:
        vol = 1.0

    if rsi >= 90:
        warnings.append("RSI(9) above 90 — Extreme overbought zone. High probability of short-term pullback. Consider partial entry or wait for 2-3 day consolidation.")
    elif rsi >= 80:
        warnings.append("RSI(9) above 80 — Overbought. Enter only with strict stop-loss discipline.")

    if slope < 0:
        warnings.append("RSI slope is declining — momentum may be reversing. Monitor closely before entry.")

    if vol < 1.5:
        warnings.append("Volume surge below 1.5x — Low conviction breakout. Risk of false breakout is higher. Wait for higher volume confirmation.")

    if vol >= 10:
        warnings.append("Extreme volume spike (>10x) — Possible news-driven move. Check fundamentals and news before entering.")

    if not warnings:
        warnings.append("No major risk flags detected. Standard stop-loss discipline applies.")

    return warnings


# ─────────────────────────────────────────────────────────────────────────────
# Generate AI Report for ONE Stock
# ─────────────────────────────────────────────────────────────────────────────
def generate_stock_report(row, scan_type="daily"):
    """Generate full AI analysis text for a single stock row."""
    name    = str(row.get("Company_Name", row.get("Ticker", "Unknown")))
    ticker  = str(row.get("Ticker", ""))
    score   = row.get("Strength_Score", 70)
    rsi     = row.get("RSI_9", row.get("Monthly_RSI_9", 65))
    slope   = row.get("RSI_Slope", 0)
    vol     = row.get("Volume_Spike", "1.5x")
    close   = row.get("Close", row.get("Entry_Price", row.get("Monthly_Close", 0)))
    upper_bb= row.get("Upper_BB", 0)
    sl      = row.get("Stop_Loss", 0)
    t1      = row.get("Target_1", 0)
    t2      = row.get("Target_2", 0)
    t3      = row.get("Target_3", 0)
    t1_pct  = row.get("Target_1_Gain_%", row.get("Target_1_Gain_Pct", "+10%"))
    t2_pct  = row.get("Target_2_Gain_%", row.get("Target_2_Gain_Pct", "+17%"))
    t3_pct  = row.get("Target_3_Gain_%", row.get("Target_3_Gain_Pct", "+30%"))
    rr      = row.get("Risk_Reward", "1:1.5")
    listed  = row.get("Listed_Date", "")
    universe= row.get("Universe", "")

    tier_num, tier_label, tier_color, tier_emoji = classify_tier(score, vol, rsi, slope)
    risk_warnings = generate_risk_warnings(rsi, vol, score, slope)

    # Build signal description
    signal_word = {1: "STRONG BUY", 2: "BUY", 3: "MODERATE BUY", 4: "WATCH", 5: "WEAK"}.get(tier_num, "WATCH")

    rsi_txt  = rsi_narrative(rsi)
    slope_txt= rsi_slope_narrative(slope)
    vol_txt  = volume_narrative(vol)
    bb_txt   = bb_narrative(close, upper_bb)

    # Compose full report
    lines = []
    lines.append(f"{tier_emoji} {tier_label} — {signal_word}")
    lines.append("")
    lines.append(f"STOCK: {name} ({ticker})")
    if listed:
        lines.append(f"Listed: {listed}  |  Universe: {universe}")
    lines.append(f"Institutional Score: {score}/100")
    lines.append("")
    lines.append("TECHNICAL ANALYSIS:")
    lines.append(f"  • {bb_txt}")
    lines.append(f"  • {rsi_txt}")
    lines.append(f"  • {slope_txt}")
    lines.append(f"  • {vol_txt}")
    lines.append("")
    lines.append("TRADE SETUP:")
    if close:
        lines.append(f"  Entry Price  : Rs {round(float(close), 2):,.2f}")
    if sl:
        try:
            sl_pct = round((float(sl) - float(close)) / float(close) * 100, 1)
            lines.append(f"  Stop Loss    : Rs {round(float(sl), 2):,.2f}  ({sl_pct}%)")
        except Exception:
            lines.append(f"  Stop Loss    : Rs {round(float(sl), 2):,.2f}")
    if t1:
        lines.append(f"  Target 1     : Rs {round(float(t1), 2):,.2f}  ({t1_pct})  Conservative")
    if t2:
        lines.append(f"  Target 2     : Rs {round(float(t2), 2):,.2f}  ({t2_pct})  Aggressive")
    if t3:
        lines.append(f"  Target 3     : Rs {round(float(t3), 2):,.2f}  ({t3_pct})  Moonshot")
    if rr:
        lines.append(f"  Risk-Reward  : {rr}")
    lines.append("")
    lines.append("RISK ASSESSMENT:")
    for w in risk_warnings:
        lines.append(f"  WARNING: {w}" if "High" in w or "Extreme" in w or "declining" in w or "Low" in w else f"  OK: {w}")
    lines.append("")

    # News & Catalyst Integration
    news_item = news_map.get(ticker, {}) if 'news_map' in locals() or 'news_map' in globals() else {}
    if news_item and news_item.get("top_headline"):
        lines.append("LIVE MARKET NEWS & CATALYSTS:")
        lines.append(f"  • {news_item.get('top_catalyst', '📰 Market News')}: \"{news_item.get('top_headline')}\"")
        lines.append("")

    lines.append("STRATEGY: BB(20,2) Upper Band Breakout + RSI(9) > 60 + Volume Surge Confirmation")

    return {
        "ticker":       ticker,
        "company":      name,
        "tier":         tier_num,
        "tier_label":   tier_label,
        "tier_color":   tier_color,
        "tier_emoji":   tier_emoji,
        "signal":       signal_word,
        "score":        score,
        "rsi":          rsi,
        "vol_spike":    str(vol),
        "close":        close,
        "stop_loss":    sl,
        "target_1":     t1,
        "target_2":     t2,
        "target_3":     t3,
        "risk_warnings":risk_warnings,
        "report_text":  "\n".join(lines),
        "short_summary": (
            f"{tier_emoji} {name.split()[0]} — {signal_word}. "
            f"RSI(9) {rsi}, Vol {vol}, Score {score}/100. "
            f"Entry Rs{round(float(close or 0), 0):.0f} | "
            f"T1 Rs{round(float(t1 or 0), 0):.0f} ({t1_pct}) | "
            f"SL Rs{round(float(sl or 0), 0):.0f}."
        ),
        "scan_type": scan_type,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Market Sentiment
# ─────────────────────────────────────────────────────────────────────────────
def compute_market_sentiment(all_reports):
    """Compute overall market sentiment from all signals."""
    if not all_reports:
        return "NEUTRAL", "No scan data available."

    tier1 = [r for r in all_reports if r["tier"] == 1]
    tier2 = [r for r in all_reports if r["tier"] == 2]
    tier12= tier1 + tier2
    total = len(all_reports)
    premium_ratio = len(tier12) / total if total > 0 else 0

    scores = [float(r["score"] or 70) for r in all_reports]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 70

    rsis = []
    for r in all_reports:
        try:
            rsis.append(float(r["rsi"] or 0))
        except Exception:
            pass
    avg_rsi = round(sum(rsis) / len(rsis), 1) if rsis else 0

    extreme_vol = [r for r in all_reports if _vol_float(r["vol_spike"]) >= 5]

    if premium_ratio >= 0.4 and avg_score >= 85:
        sentiment = "STRONGLY BULLISH"
        desc = "High concentration of premium signals with strong institutional participation."
    elif premium_ratio >= 0.25 or avg_score >= 78:
        sentiment = "BULLISH"
        desc = "Good breadth of strong signals. Market showing healthy momentum."
    elif premium_ratio >= 0.1 or avg_score >= 70:
        sentiment = "MODERATELY BULLISH"
        desc = "Mixed signals. Selective stock picking recommended."
    else:
        sentiment = "NEUTRAL / CAUTIOUS"
        desc = "Few high-quality signals today. Wait for stronger confirmation."

    return sentiment, desc, avg_score, avg_rsi, len(extreme_vol), tier1, tier2


def _vol_float(v):
    try:
        return float(str(v).replace("x", ""))
    except Exception:
        return 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Generate Market Summary Report
# ─────────────────────────────────────────────────────────────────────────────
def generate_market_summary(all_reports, scan_time):
    """Generate the top-level market intelligence summary."""
    if not all_reports:
        return {
            "sentiment": "NEUTRAL",
            "summary_text": "No scan data available. Run the market scan first.",
            "top_picks": [],
            "scan_time": scan_time,
            "total_signals": 0,
        }

    result = compute_market_sentiment(all_reports)
    sentiment   = result[0]
    desc        = result[1]
    avg_score   = result[2]
    avg_rsi     = result[3]
    extreme_vols= result[4]
    tier1       = result[5]
    tier2       = result[6]

    # Top picks = Tier 1 first, then Tier 2, sorted by score
    top_pool = sorted(tier1 + tier2, key=lambda x: float(x["score"] or 0), reverse=True)
    top_picks = [r["company"].split()[0] + f" ({r['ticker'].replace('.NS','').replace('.BO','')})" for r in top_pool[:5]]

    # Hot sectors from scan
    all_vols = sorted(all_reports, key=lambda x: _vol_float(x["vol_spike"]), reverse=True)
    extreme_tickers = [r["ticker"].replace(".NS","").replace(".BO","") + f" ({r['vol_spike']})" for r in all_vols if _vol_float(r["vol_spike"]) >= 3][:5]

    # Highest RSI stocks
    top_rsi = sorted(all_reports, key=lambda x: float(x["rsi"] or 0), reverse=True)
    top_rsi_names = [r["company"].split()[0] + f" ({r['rsi']})" for r in top_rsi[:3]]

    lines = [
        "=" * 62,
        "  STOKS AI — DAILY MARKET INTELLIGENCE REPORT",
        f"  Generated: {scan_time}",
        "=" * 62,
        f"  MARKET SENTIMENT   : {sentiment}",
        f"  SIGNALS FOUND      : {len(all_reports)} breakout stocks",
        f"  PREMIUM SIGNALS    : {len(tier1)} (Tier 1) + {len(tier2)} (Tier 2)",
        f"  AVG INST. SCORE    : {avg_score}/100",
        f"  AVG RSI(9)         : {avg_rsi}",
        f"  EXTREME VOL (>3x)  : {', '.join(extreme_tickers) if extreme_tickers else 'None today'}",
        f"  TOP RSI MOMENTUM   : {', '.join(top_rsi_names)}",
        f"  TOP PICKS TODAY    : {', '.join(top_picks) if top_picks else 'N/A'}",
        "=" * 62,
        f"  ANALYSIS: {desc}",
        "=" * 62,
    ]

    return {
        "sentiment": sentiment,
        "summary_text": "\n".join(lines),
        "top_picks": top_picks,
        "extreme_vol_stocks": extreme_tickers,
        "top_rsi_stocks": top_rsi_names,
        "avg_score": avg_score,
        "avg_rsi": avg_rsi,
        "total_signals": len(all_reports),
        "tier1_count": len(tier1),
        "tier2_count": len(tier2),
        "scan_time": scan_time,
        "sentiment_desc": desc,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────────────────────────────────────
def run_ai_engine():
    """Main function: load all scan CSVs, FII/DII, News, generate AI reports, save JSON."""
    logger.info("=" * 60)
    logger.info("STOKS AI — Smart Analysis Engine V1.1 Starting...")
    logger.info("=" * 60)

    scan_time = datetime.now().strftime("%Y-%m-%d %H:%M IST")

    # Load FII/DII data if available
    fii_dii_data = {}
    if os.path.exists("fii_dii_data.json"):
        try:
            with open("fii_dii_data.json", "r", encoding="utf-8") as f:
                fii_dii_data = json.load(f)
        except Exception:
            pass

    # Load Stock News data if available
    global news_map
    news_map = {}
    if os.path.exists("stock_news_data.json"):
        try:
            with open("stock_news_data.json", "r", encoding="utf-8") as f:
                news_map = json.load(f)
        except Exception:
            pass

    all_reports = []

    # Load each scan type
    sources = [
        ("recent_ipo_breakouts_5y.csv", "5y_ipo"),
        ("master_scan_results.csv",      "daily"),
        ("monthly_ath_breakouts.csv",    "monthly"),
    ]

    seen_tickers = set()
    for csv_path, scan_type in sources:
        if not os.path.exists(csv_path):
            logger.warning(f"  Skipping {csv_path} — file not found")
            continue
        try:
            df = pd.read_csv(csv_path)
            df.columns = [c.strip() for c in df.columns]
            logger.info(f"  Processing {len(df)} rows from {csv_path}...")
            for _, row in df.iterrows():
                ticker = str(row.get("Ticker", ""))
                if ticker in seen_tickers:
                    continue
                seen_tickers.add(ticker)
                try:
                    report = generate_stock_report(row.to_dict(), scan_type)
                    all_reports.append(report)
                except Exception as e:
                    logger.warning(f"    Report failed for {ticker}: {e}")
        except Exception as e:
            logger.error(f"  Failed to read {csv_path}: {e}")

    logger.info(f"  Generated {len(all_reports)} AI stock reports.")

    # Generate market summary
    market_summary = generate_market_summary(all_reports, scan_time)
    logger.info(f"  Market Sentiment: {market_summary['sentiment']}")
    logger.info(f"  Top Picks: {', '.join(market_summary['top_picks'])}")

    # Sort reports: Tier ASC, then Score DESC
    all_reports.sort(key=lambda x: (x["tier"], -float(x["score"] or 0)))

    # Build final output
    output = {
        "scan_time": scan_time,
        "market_summary": market_summary,
        "fii_dii": fii_dii_data,
        "reports": all_reports,
        "total": len(all_reports),
    }

    # Save
    out_path = "ai_analysis_report.json"
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, separators=(",", ":"), ensure_ascii=False, default=str)
        logger.info(f"SUCCESS: AI Analysis Report saved -> {out_path}")
    except Exception as e:
        logger.error(f"Failed to save {out_path}: {e}")

    # Print market summary to console
    print("\n" + market_summary["summary_text"] + "\n")

    return output


if __name__ == "__main__":
    run_ai_engine()
