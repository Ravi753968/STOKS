# ⚡ STOKS V5.0 — Enterprise Quantitative Breakout Workstation

> **Production-Grade Automated Technical Breakout Scanner, FII/DII Liquidity Engine, Live News Catalyst Tracker, 925 IPO Performance Tracker & AI Intelligence Suite for Indian Stock Markets (BSE & NSE).**

---

## 🌟 Key System Capabilities

| Feature | Module | Description |
|---------|--------|-------------|
| **Quantitative Breakout Engine** | `quant_engine.py` | RSI(9) Fast Momentum > 60 + Upper Bollinger Band (20,2) Breakout + 1.5x–17x Volume Surge + 2× ATR Trailing Stop Loss |
| **FII / DII Flow Engine** | `fii_dii_engine.py` | Auto-fetches daily Cash Market net institutional liquidity (₹ Crores) & evaluates macro market bias |
| **Live News Catalyst Engine** | `news_engine.py` | Scrapes Google News RSS feeds for breakout stocks in parallel; classifies headlines into Earnings, Order Wins, Block Deals, Capex |
| **925 Live IPO Universe** | `live_ipo_fetcher.py` | Auto-fetches all BSE & NSE Main Board IPOs (2022–2026) from official archives & Chittorgarh with 24h cache |
| **Local AI Analysis Engine** | `ai_engine.py` | 100% local, rule-based NLP AI engine generating structured reports & signal tiers (🔴 Premium, 🟠 Strong, 🟡 Moderate, 🟢 Watch) |
| **Sector Heatmap Engine** | `sector_map.py` | Maps breakout stocks into 10 sectors, calculating sector strength, RSI momentum, and top sector performers |
| **IPO Performance Tracker** | `ipo_performance.py` | High-speed vectorized price fetcher for 925 IPO tickers |
| **TradingView Charting Modal** | `dashboard.html` | Interactive 90-day price charts with Bollinger Bands overlay & RSI sub-charts via Lightweight Charts API |
| **Risk & Position Calculator** | `dashboard.html` | Real-time position sizing calculator: Enter Capital & Risk % to get exact share quantities & capital allocation % |
| **Telegram Alert Dispatcher** | `alerts/alert_dispatcher.py` | Dispatches high-conviction 🔴 Tier 1 Premium Breakout alerts to Telegram |

---

## 🚀 Quick Start Guide

### 1. Launch Server (One-Click)
Double-click **`run_system.bat`** or run:
```bash
python main.py server
```
Then open **`http://localhost:5005`** in your browser.

### 2. Run Full Market Scan Pipeline
Click **"🔄 RUN SCAN NOW"** on the dashboard or run:
```bash
python main.py scan
```

### 3. Check System Status
```bash
python main.py status
```

---

## 🛠️ System Architecture (11-Stage Automated Pipeline)

```
                       RUN SCAN PIPELINE
                              │
  ┌───────────────────────────┼───────────────────────────┐
  │                           │                           │
STAGE 1                     STAGE 2                     STAGE 9
Daily Market Fetch          Monthly ATH Fetch           FII / DII Flow Engine
RSI(9) + BB(20,2)           Multi-year Breakouts        Cash Net Buy/Sell
  │                           │                           │
  └───────────────────────────┼───────────────────────────┘
                              │
                           STAGE 10
                     Live News Catalyst Scraper
                              │
                           STAGE 5
                     Sector Heatmap Engine
                              │
                           STAGE 7
                   925 Live IPO Performance
                              │
                           STAGE 8
                  Local AI Smart Analysis Engine
                              │
                           STAGE 11
                   Telegram Alert Dispatcher
                              │
                           STAGE 4
                  Web Workstation Generator
```

---

## 🌐 Production Server API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web Workstation Dashboard (`dashboard.html`) |
| `GET` | `/api/status` | System health check JSON |
| `GET` | `/api/chart?ticker=TICKER.NS&period=90d` | Fetch OHLCV candles + BB + RSI for charting |
| `POST` | `/api/scan` | Trigger background 11-stage full market scan |

---

## 📊 System Files Summary

- **`main.py`** — Unified CLI Controller
- **`run_system.bat`** — One-click launcher & browser opener
- **`server.py`** — Production REST Server (Port 5005)
- **`run_production_pipeline.py`** — 11-Stage Automated Pipeline
- **`build_premium_dashboard.py`** — Workstation Dashboard Builder
- **`ai_engine.py`** — Local AI Smart Analysis Engine
- **`fii_dii_engine.py`** — FII/DII Net Flow Engine
- **`news_engine.py`** — Live Stock News & Catalyst Engine
- **`live_ipo_fetcher.py`** — 925 Live Internet IPO Fetcher (2022–2026)
- **`sector_map.py`** — Sector Heatmap Engine
- **`ipo_performance.py`** — IPO Performance Engine
- **`alerts/alert_dispatcher.py`** — Alert Dispatcher
- **`Production_Breakout_Master_V3.xlsx`** — Institutional Master Excel Report
