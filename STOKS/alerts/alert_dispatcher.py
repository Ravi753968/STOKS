"""
STOKS V5.0 — Alert Dispatcher Module
Dispatches high-conviction breakout notifications (Telegram + System Log).
"""
import requests
import json
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from prod_logger import log_info, log_error

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")


def send_telegram_alert(stock_report):
    """Send formatted Telegram notification for Tier 1 Premium Breakout."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    ticker  = stock_report.get("ticker", "N/A")
    company = stock_report.get("company", ticker)
    score   = stock_report.get("score", 80)
    close   = stock_report.get("close", 0)
    sl      = stock_report.get("stop_loss", 0)
    t1      = stock_report.get("target_1", 0)
    tier    = stock_report.get("tier_label", "PREMIUM SIGNAL")

    is_b = ticker.endswith(".BO")
    ex = "BSE" if is_b else "NSE"
    sy = ticker.replace(".NS", "").replace(".BO", "")
    tv_url = f"https://in.tradingview.com/chart/?symbol={ex}:{sy}"

    msg = (
        f"🚨 <b>STOKS BREAKOUT ALERT — {tier}</b> 🚨\n\n"
        f"<b>Company</b>: {company} ({ticker})\n"
        f"<b>Institutional Score</b>: {score}/100\n"
        f"<b>Entry Price</b>: ₹{close:,.2f}\n"
        f"<b>Stop Loss</b>: ₹{sl:,.2f}\n"
        f"<b>Target 1</b>: ₹{t1:,.2f}\n\n"
        f"🔗 <a href='{tv_url}'>View Live Chart on TradingView</a>"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        resp = requests.post(url, json=payload, timeout=8)
        if resp.status_code == 200:
            log_info(f"[Alerts] Telegram alert sent for {ticker}")
            return True
        else:
            log_error(f"[Alerts] Telegram send failed: {resp.text}")
    except Exception as e:
        log_error(f"[Alerts] Telegram error: {e}")

    return False


def dispatch_alerts(ai_report_json="ai_analysis_report.json"):
    """Dispatch alerts for all Tier 1 Premium signals."""
    if not os.path.exists(ai_report_json):
        return

    try:
        with open(ai_report_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        reports = data.get("reports", [])
        tier1_signals = [r for r in reports if r.get("tier") == 1]

        log_info(f"[Alerts] Dispatching alerts for {len(tier1_signals)} Tier 1 signals...")
        for r in tier1_signals:
            log_info(f"  [TIER 1 ALERT] {r.get('company')} ({r.get('ticker')}) -> Entry: Rs {r.get('close')} | Score: {r.get('score')}")
            send_telegram_alert(r)

    except Exception as e:
        log_error(f"[Alerts] Dispatch error: {e}")


if __name__ == "__main__":
    dispatch_alerts()
