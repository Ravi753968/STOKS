"""
STOKS V5.0 — Enterprise System CLI Controller
Unified command-line launcher and system interface.

Usage:
    python main.py scan      - Run full 11-stage automated market scan
    python main.py server    - Start production workstation server (Port 5005)
    python main.py status    - System health check & data inventory
    python main.py fii       - Fetch live FII/DII net flows
    python main.py news      - Fetch live stock news & catalysts
    python main.py ipo       - Refresh 925 live IPO universe
"""
import sys
import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import PORT, BASE_DIR, CACHE_DIR
from prod_logger import log_info, log_error


def cmd_scan():
    """Run full automated production scanning pipeline."""
    log_info("Starting STOKS V5.0 Full Market Scan Pipeline...")
    from run_production_pipeline import run_production_pipeline
    run_production_pipeline()


def cmd_server():
    """Start workstation web server."""
    log_info(f"Starting STOKS V5.0 Production Server on Port {PORT}...")
    from server import start_production_server
    start_production_server()


def cmd_fii():
    """Fetch FII/DII institutional flows."""
    from fii_dii_engine import fetch_fii_dii_flows
    fetch_fii_dii_flows()


def cmd_news():
    """Fetch live stock news & catalysts."""
    from news_engine import fetch_live_market_news
    fetch_live_market_news()


def cmd_ipo():
    """Refresh live 925 IPO universe."""
    from live_ipo_fetcher import fetch_live_ipo_universe
    fetch_live_ipo_universe(force_refresh=True)


def cmd_status():
    """System health check and file inventory."""
    print("\n" + "=" * 65)
    print(" STOKS V5.0 ENTERPRISE SYSTEM HEALTH & INVENTORY CHECK")
    print("=" * 65)

    files_to_check = [
        ("Production Server", "server.py"),
        ("Scan Pipeline", "run_production_pipeline.py"),
        ("Dashboard Builder", "build_premium_dashboard.py"),
        ("AI Smart Engine", "ai_engine.py"),
        ("FII/DII Flow Engine", "fii_dii_engine.py"),
        ("News Catalyst Engine", "news_engine.py"),
        ("Sector Heatmap Engine", "sector_map.py"),
        ("IPO Performance Engine", "ipo_performance.py"),
        ("Live IPO Fetcher", "live_ipo_fetcher.py"),
        ("Alert Dispatcher", "alerts/alert_dispatcher.py"),
        ("Web Workstation", "dashboard.html"),
        ("AI Report Output", "ai_analysis_report.json"),
        ("FII/DII Output", "fii_dii_data.json"),
        ("Stock News Output", "stock_news_data.json"),
        ("Live IPO Cache", "cache/ipo_universe_cache.json"),
        ("Master Excel Report", "Production_Breakout_Master_V3.xlsx"),
    ]

    for label, rel_path in files_to_check:
        full_path = os.path.join(BASE_DIR, rel_path)
        exists = os.path.exists(full_path)
        size_kb = round(os.path.getsize(full_path) / 1024.0, 1) if exists else 0.0
        status_str = f"OK  ({size_kb:>6.1f} KB)" if exists else "MISSING      "
        print(f"  [{status_str}]  {label:25s} -> {rel_path}")

    print("=" * 65)
    print(f"  Server URL: http://localhost:{PORT}")
    print("=" * 65 + "\n")


def main():
    if len(sys.argv) < 2:
        cmd_status()
        print("Commands: scan | server | status | fii | news | ipo\n")
        return

    cmd = sys.argv[1].lower()
    if cmd == "scan":
        cmd_scan()
    elif cmd == "server":
        cmd_server()
    elif cmd == "status":
        cmd_status()
    elif cmd == "fii":
        cmd_fii()
    elif cmd == "news":
        cmd_news()
    elif cmd == "ipo":
        cmd_ipo()
    else:
        print(f"Unknown command: {cmd}")
        print("Valid commands: scan, server, status, fii, news, ipo")


if __name__ == "__main__":
    main()
