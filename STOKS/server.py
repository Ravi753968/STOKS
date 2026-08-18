import http.server
import socketserver
import json
import subprocess
import os
import sys
import threading
from urllib.parse import urlparse, parse_qs
from config import PORT, BASE_DIR

# ─────────────────────────────────────────────
# Chart Data Fetcher (for /api/chart endpoint)
# ─────────────────────────────────────────────
def fetch_chart_data(ticker, period="90d"):
    """Fetch OHLCV + BB + RSI data for a ticker via yfinance."""
    try:
        import yfinance as yf
        import numpy as np

        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if df is None or len(df) < 10:
            return None

        df = df.reset_index()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

        # Bollinger Bands (20, 2)
        df["SMA20"] = df["Close"].rolling(20).mean()
        df["STD20"] = df["Close"].rolling(20).std()
        df["BB_Upper"] = df["SMA20"] + 2 * df["STD20"]

        # RSI (9)
        delta = df["Close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=8, min_periods=9).mean()
        avg_loss = loss.ewm(com=8, min_periods=9).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["RSI9"] = 100 - (100 / (1 + rs))

        df = df.dropna(subset=["SMA20", "RSI9"]).reset_index(drop=True)

        def to_ts(dt):
            import pandas as pd
            ts = pd.Timestamp(dt)
            return int(ts.timestamp())

        candles = []
        bb_upper = []
        bb_mid = []
        rsi_data = []

        for _, row in df.iterrows():
            t = to_ts(row["Date"])
            candles.append({
                "time": t,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low":  round(float(row["Low"]), 2),
                "close":round(float(row["Close"]), 2),
            })
            bb_upper.append({"time": t, "value": round(float(row["BB_Upper"]), 2)})
            bb_mid.append({"time": t, "value": round(float(row["SMA20"]), 2)})
            if not (row["RSI9"] != row["RSI9"]):  # not NaN
                rsi_data.append({"time": t, "value": round(float(row["RSI9"]), 2)})

        return {"candles": candles, "bb_upper": bb_upper, "bb_mid": bb_mid, "rsi": rsi_data}

    except Exception as e:
        print(f"[Chart API] Error fetching {ticker}: {e}")
        return None


# ─────────────────────────────────────────────
# HTTP Handler
# ─────────────────────────────────────────────
class ProductionHandler(http.server.SimpleHTTPRequestHandler):

    def log_message(self, format, *args):
        try:
            msg = str(args[0]) if args else ""
            if "/api/" in msg:
                print(f"[Server] {msg}")
        except Exception:
            pass

    def send_json(self, code, data):
        body = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/scan":
            print("\n[Server] Live Market Scan Triggered...")
            try:
                result = subprocess.run(
                    [sys.executable, "run_production_pipeline.py"],
                    cwd=BASE_DIR, capture_output=True, text=True, timeout=300
                )
                print("[Server] Scan completed.")
                self.send_json(200, {
                    "status": "success",
                    "message": "Production scan completed successfully!",
                    "output": result.stdout[:500],
                })
            except subprocess.TimeoutExpired:
                self.send_json(408, {"status": "timeout", "message": "Scan timed out (>5 min)"})
            except Exception as e:
                self.send_json(500, {"status": "error", "message": str(e)})
        else:
            self.send_error(404, "Endpoint not found")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path in ("/", "/dashboard"):
            self.path = "/dashboard.html"
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

        elif path in ("/mobile", "/m"):
            self.path = "/mobile.html"
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        elif path == "/api/status":
            self.send_json(200, {
                "status": "active",
                "system": "STOKS V4.0 Production Engine",
                "version": "4.0",
                "port": PORT,
            })
            return

        elif path == "/api/chart":
            ticker = params.get("ticker", [""])[0]
            period = params.get("period", ["90d"])[0]
            if not ticker:
                self.send_json(400, {"error": "ticker parameter required"})
                return
            print(f"[Server] Chart request: {ticker} ({period})")
            data = fetch_chart_data(ticker, period)
            if data:
                self.send_json(200, data)
            else:
                self.send_json(404, {"error": "No data available for ticker: " + ticker})
            return

        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)


# ─────────────────────────────────────────────
# Server Startup
# ─────────────────────────────────────────────
def start_production_server():
    os.chdir(BASE_DIR)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), ProductionHandler) as httpd:
        print("=" * 65)
        print(f"  STOKS V4.0 PRODUCTION SERVER -> http://localhost:{PORT}")
        print("  Endpoints:")
        print("    GET  /            -> Dashboard UI")
        print("    GET  /api/status  -> System health")
        print("    GET  /api/chart   -> Chart data (ticker, period params)")
        print("    POST /api/scan    -> Run full market scan")
        print("=" * 65)
        httpd.serve_forever()


if __name__ == "__main__":
    start_production_server()
