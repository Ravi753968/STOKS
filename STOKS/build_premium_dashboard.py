import pandas as pd
import json
import os

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def compact_records(df):
    if df.empty:
        return "[]"
    records = df.to_dict(orient="records")
    clean = []
    for r in records:
        clean.append({k: v for k, v in r.items() if pd.notnull(v)})
    return json.dumps(clean, separators=(',', ':'))

def load_json_file(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.dumps(json.load(f), separators=(',', ':'))
        except Exception:
            pass
    return "[]"

def load_backtest_summary(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.dumps(json.load(f), separators=(',', ':'))
        except Exception:
            pass
    return '{}'

def load_csv_safe(path):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            pass
    return pd.DataFrame()

# ─────────────────────────────────────────────
# Main Builder
# ─────────────────────────────────────────────
def build_dashboard():
    print("Building STOKS V4.0 Dashboard...")

    df_5y     = load_csv_safe("recent_ipo_breakouts_5y.csv")
    df_daily  = load_csv_safe("master_scan_results.csv")
    df_monthly= load_csv_safe("monthly_ath_breakouts.csv")
    df_ipo    = load_csv_safe("ipo_performance_data.csv")
    df_bt     = load_csv_safe("backtest_results.csv")

    records_5y      = compact_records(df_5y)
    records_daily   = compact_records(df_daily)
    records_monthly = compact_records(df_monthly)
    records_ipo     = compact_records(df_ipo)
    records_bt      = compact_records(df_bt)
    records_sector  = load_json_file("sector_heatmap_data.json")
    bt_summary      = load_backtest_summary("backtest_summary.json")
    ai_report       = load_backtest_summary("ai_analysis_report.json")
    fii_dii_json    = load_backtest_summary("fii_dii_data.json")
    news_json       = load_json_file("stock_news_data.json")

    count_5y      = len(df_5y)
    count_daily   = len(df_daily)
    count_monthly = len(df_monthly)
    count_ipo     = len(df_ipo)
    count_bt      = len(df_bt)
    # AI count from JSON
    try:
        import json as _json
        _ai_data = _json.loads(ai_report) if ai_report != '{}' else {}
        count_ai = _ai_data.get('total', 0)
    except Exception:
        count_ai = 0

    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>STOKS V4.1 AI — Institutional Breakout Workstation</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
:root{--bg-dark:#080d1a;--card-bg:#111a2e;--card-border:#1e2d4a;--text-main:#f8fafc;--text-muted:#94a3b8;--accent-cyan:#00f5d4;--accent-green:#10b981;--accent-blue:#3b82f6;--accent-purple:#8b5cf6;--accent-amber:#f59e0b;--accent-red:#ef4444;--hover-bg:#192642}
*{margin:0;padding:0;box-sizing:border-box;font-family:'Outfit','Inter',sans-serif}
body{background-color:var(--bg-dark);color:var(--text-main);padding:20px;min-height:100vh}
.container{max-width:1700px;margin:0 auto}

/* ── Header ── */
header{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px;padding-bottom:18px;border-bottom:1px solid var(--card-border)}
.title-area h1{font-size:26px;font-weight:800;background:linear-gradient(135deg,#00f5d4,#3b82f6,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.title-area p{font-size:13px;color:var(--text-muted);margin-top:3px}
.header-actions{display:flex;gap:10px;align-items:center}
.btn-run-scan{background:linear-gradient(135deg,#10b981,#059669);border:1px solid #10b981;color:#fff;padding:10px 22px;border-radius:10px;font-size:14px;font-weight:800;cursor:pointer;display:flex;align-items:center;gap:8px;box-shadow:0 4px 14px rgba(16,185,129,.35);transition:all .25s}
.btn-run-scan:hover{background:linear-gradient(135deg,#059669,#047857);transform:translateY(-2px);box-shadow:0 6px 20px rgba(16,185,129,.5)}
.btn-run-scan:disabled{background:#334155;border-color:#475569;color:#94a3b8;cursor:not-allowed;transform:none;box-shadow:none}
.spinner{width:16px;height:16px;border:2px solid rgba(255,255,255,.3);border-radius:50%;border-top-color:#fff;animation:spin .8s linear infinite;display:none}
@keyframes spin{to{transform:rotate(360deg)}}
.btn-action{background:linear-gradient(135deg,rgba(59,130,246,.2),rgba(139,92,246,.2));border:1px solid rgba(59,130,246,.4);color:#60a5fa;padding:9px 16px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;transition:all .2s}
.btn-action:hover{background:rgba(59,130,246,.35);color:#fff}
.badge-status{background:rgba(16,185,129,.15);color:var(--accent-green);border:1px solid var(--accent-green);padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;display:flex;align-items:center;gap:8px}
.badge-status::before{content:'';width:8px;height:8px;background-color:var(--accent-green);border-radius:50%;display:inline-block;box-shadow:0 0 10px var(--accent-green)}

/* ── Toast ── */
#toastNotice{position:fixed;bottom:24px;right:24px;background-color:var(--card-bg);border:1px solid var(--accent-cyan);color:var(--text-main);padding:14px 20px;border-radius:10px;font-size:14px;font-weight:600;box-shadow:0 10px 25px rgba(0,0,0,.5);display:none;z-index:2000;align-items:center;gap:10px}

/* ── Tabs ── */
.nav-tabs{display:flex;gap:8px;margin-bottom:22px;background-color:rgba(17,26,46,.6);padding:5px;border-radius:12px;border:1px solid var(--card-border);width:fit-content;flex-wrap:wrap}
.tab-btn{background:transparent;border:none;color:var(--text-muted);padding:9px 18px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;transition:all .25s;white-space:nowrap}
.tab-btn:hover{color:var(--text-main)}
.tab-btn.active{background:linear-gradient(135deg,#1d2b4a,#283759);color:#60a5fa;border:1px solid rgba(96,165,250,.3);box-shadow:0 4px 12px rgba(0,0,0,.3)}

/* ── Metrics ── */
.metrics-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:22px}
.metric-card{background-color:var(--card-bg);border:1px solid var(--card-border);border-radius:14px;padding:18px;position:relative;overflow:hidden;transition:transform .2s,border-color .2s}
.metric-card:hover{transform:translateY(-2px);border-color:rgba(96,165,250,.4)}
.metric-card .label{font-size:12px;color:var(--text-muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px}
.metric-card .val{font-size:30px;font-weight:800;color:var(--text-main);font-family:'Inter',sans-serif}
.metric-card .sub{font-size:12px;margin-top:5px;color:var(--accent-green);font-weight:500}

/* ── Controls ── */
.controls-bar{background-color:var(--card-bg);border:1px solid var(--card-border);border-radius:14px;padding:14px 18px;margin-bottom:22px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:space-between}
.search-box{flex:1;min-width:260px}
.search-box input{width:100%;background-color:var(--bg-dark);border:1px solid var(--card-border);color:var(--text-main);padding:10px 14px;border-radius:10px;font-size:14px;outline:none;transition:border-color .2s}
.search-box input:focus{border-color:var(--accent-blue)}
.filter-group{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
select{background-color:var(--bg-dark);border:1px solid var(--card-border);color:var(--text-main);padding:10px 14px;border-radius:10px;font-size:13px;outline:none;cursor:pointer}

/* ── Table ── */
.table-container{background-color:var(--card-bg);border:1px solid var(--card-border);border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.4)}
.table-scroll{overflow-x:auto}
table{width:100%;border-collapse:collapse;text-align:left}
th{background-color:rgba(8,13,26,.8);color:var(--text-muted);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;padding:14px 16px;border-bottom:1px solid var(--card-border);white-space:nowrap}
td{padding:14px 16px;border-bottom:1px solid var(--card-border);font-size:13px;vertical-align:middle}
tr:hover{background-color:var(--hover-bg)}
.stock-symbol{font-weight:800;font-size:14px;color:#60a5fa;text-decoration:none;cursor:pointer}
.stock-symbol:hover{text-decoration:underline;color:var(--accent-cyan)}
.score-pill{display:inline-block;padding:3px 9px;border-radius:20px;font-weight:800;font-size:11px}
.score-high{background-color:rgba(16,185,129,.2);color:#34d399;border:1px solid #10b981}
.score-mid{background-color:rgba(245,158,11,.2);color:#fbbf24;border:1px solid #f59e0b}
.score-low{background-color:rgba(239,68,68,.2);color:#f87171;border:1px solid #ef4444}
.vol-badge{color:#fbbf24;font-weight:700;background-color:rgba(245,158,11,.12);padding:3px 7px;border-radius:6px;border:1px solid rgba(245,158,11,.3);display:inline-block;font-size:12px}
.sl-price{color:var(--accent-red);font-weight:700;font-family:'Inter',sans-serif}
.target1-price{color:var(--accent-green);font-weight:800;font-family:'Inter',sans-serif}
.target2-price{color:var(--accent-purple);font-weight:800;font-family:'Inter',sans-serif}
.chart-links-group{display:flex;gap:5px;align-items:center}
.tv-btn{color:#60a5fa;text-decoration:none;font-size:11px;font-weight:700;padding:5px 10px;border:1px solid rgba(96,165,250,.4);border-radius:6px;background-color:rgba(96,165,250,.1);transition:all .2s}
.tv-btn:hover{background-color:rgba(96,165,250,.3);color:#fff}
.chartink-btn{color:#fbbf24;text-decoration:none;font-size:11px;font-weight:700;padding:5px 10px;border:1px solid rgba(245,158,11,.4);border-radius:6px;background-color:rgba(245,158,11,.1);transition:all .2s}
.chartink-btn:hover{background-color:rgba(245,158,11,.3);color:#fff}
.chart-btn-inline{color:#00f5d4;font-size:11px;font-weight:700;padding:5px 10px;border:1px solid rgba(0,245,212,.4);border-radius:6px;background-color:rgba(0,245,212,.1);cursor:pointer;transition:all .2s;border-style:solid}
.chart-btn-inline:hover{background-color:rgba(0,245,212,.3);color:#fff}

/* ── Chart Modal ── */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.82);z-index:3000;align-items:center;justify-content:center}
.modal-overlay.open{display:flex}
.modal-box{background:var(--card-bg);border:1px solid var(--card-border);border-radius:18px;padding:24px;width:92%;max-width:1050px;max-height:92vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.8);animation:slideUp .25s ease}
@keyframes slideUp{from{transform:translateY(40px);opacity:0}to{transform:translateY(0);opacity:1}}
.modal-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px}
.modal-title{font-size:20px;font-weight:800;color:#60a5fa}
.modal-subtitle{font-size:13px;color:var(--text-muted);margin-top:3px}
.modal-close{background:rgba(239,68,68,.2);border:1px solid rgba(239,68,68,.4);color:#f87171;width:32px;height:32px;border-radius:8px;cursor:pointer;font-size:18px;font-weight:700;display:flex;align-items:center;justify-content:center;transition:all .2s}
.modal-close:hover{background:rgba(239,68,68,.4);color:#fff}
.modal-levels{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap}
.level-badge{padding:8px 16px;border-radius:10px;font-size:13px;font-weight:700}
.level-entry{background:rgba(59,130,246,.2);border:1px solid rgba(59,130,246,.5);color:#60a5fa}
.level-sl{background:rgba(239,68,68,.2);border:1px solid rgba(239,68,68,.5);color:#f87171}
.level-t1{background:rgba(16,185,129,.2);border:1px solid rgba(16,185,129,.5);color:#34d399}
.level-t2{background:rgba(139,92,246,.2);border:1px solid rgba(139,92,246,.5);color:#a78bfa}
.level-t3{background:rgba(245,158,11,.2);border:1px solid rgba(245,158,11,.5);color:#fbbf24}
#chartContainer{height:340px;border-radius:10px;overflow:hidden;border:1px solid var(--card-border);margin-bottom:12px}
#rsiContainer{height:140px;border-radius:10px;overflow:hidden;border:1px solid var(--card-border)}
.chart-loading{display:flex;align-items:center;justify-content:center;height:340px;color:var(--text-muted);font-size:14px;gap:10px}

/* ── Sector Heatmap ── */
.heatmap-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin-bottom:24px}
.sector-card{background:var(--card-bg);border:1px solid var(--card-border);border-radius:14px;padding:20px;cursor:pointer;transition:all .25s;position:relative;overflow:hidden}
.sector-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--sc-color)}
.sector-card:hover{transform:translateY(-3px);border-color:var(--sc-color);box-shadow:0 8px 24px rgba(0,0,0,.5)}
.sector-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px}
.sector-name{font-size:15px;font-weight:700;color:var(--text-main)}
.sector-emoji{font-size:28px}
.sector-count{background:rgba(255,255,255,.08);border-radius:8px;padding:4px 10px;font-size:20px;font-weight:800;color:var(--sc-color)}
.sector-stats{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.sector-stat{text-align:center;background:rgba(255,255,255,.04);border-radius:8px;padding:8px}
.sector-stat .s-label{font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px}
.sector-stat .s-val{font-size:18px;font-weight:800;color:var(--text-main)}
.sector-top-stock{font-size:12px;color:var(--text-muted);border-top:1px solid var(--card-border);padding-top:10px;margin-top:4px}
.sector-top-stock span{color:var(--sc-color);font-weight:700}
.sector-stocks-list{display:none;margin-top:12px;border-top:1px solid var(--card-border);padding-top:12px}
.sector-stocks-list.open{display:block}
.sector-stock-item{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:12px}
.sector-stock-item:last-child{border-bottom:none}

/* ── Backtest ── */
.bt-summary-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;margin-bottom:24px}
.bt-card{background:var(--card-bg);border:1px solid var(--card-border);border-radius:14px;padding:18px;text-align:center}
.bt-card .b-label{font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.bt-card .b-val{font-size:28px;font-weight:800}
.bt-card .b-sub{font-size:11px;color:var(--text-muted);margin-top:5px}
.outcome-win{color:#34d399}
.outcome-loss{color:#f87171}
.outcome-timeout{color:#fbbf24}
.outcome-badge{display:inline-block;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:700}
.badge-win{background:rgba(16,185,129,.2);color:#34d399;border:1px solid #10b981}
.badge-loss{background:rgba(239,68,68,.2);color:#f87171;border:1px solid #ef4444}
.badge-timeout{background:rgba(245,158,11,.2);color:#fbbf24;border:1px solid #f59e0b}

/* ── IPO Tracker ── */
.ipo-filter-bar{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap}
.ipo-year-btn{background:transparent;border:1px solid var(--card-border);color:var(--text-muted);padding:7px 14px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;transition:all .2s}
.ipo-year-btn.active,.ipo-year-btn:hover{background:rgba(59,130,246,.2);border-color:rgba(59,130,246,.5);color:#60a5fa}
.gain-positive{color:#34d399;font-weight:700}
.gain-negative{color:#f87171;font-weight:700}
.gain-flat{color:#fbbf24;font-weight:700}
.perf-badge{display:inline-block;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:700;white-space:nowrap}

/* ── Guide ── */
.guide-box{padding:22px;background-color:var(--card-bg);border-radius:14px;border:1px solid var(--card-border);margin-top:22px}
.guide-box h2{font-size:17px;color:#60a5fa;margin-bottom:14px}
.guide-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
.guide-card{background-color:var(--bg-dark);border:1px solid var(--card-border);padding:14px;border-radius:10px}
.guide-card h4{color:var(--accent-cyan);font-size:13px;margin-bottom:5px}
.guide-card p{color:var(--text-muted);font-size:12px;line-height:1.6}

/* ── No Data ── */
.no-data{text-align:center;padding:60px 20px;color:var(--text-muted)}
.no-data .nd-icon{font-size:48px;margin-bottom:12px}
.no-data p{font-size:14px}
/* ── Risk & Position Calculator ── */
.risk-calc-box{background:rgba(255,255,255,.04);border:1px solid var(--card-border);border-radius:10px;padding:12px 16px;margin:12px 0;display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;align-items:center}
.calc-field label{display:block;font-size:10px;color:var(--text-muted);text-transform:uppercase;margin-bottom:4px;font-weight:700}
.calc-field input{width:100%;padding:5px 8px;font-size:12px;border-radius:6px;background:var(--bg-dark);border:1px solid var(--card-border);color:var(--text-main);font-weight:700}
.calc-res-item{text-align:center;background:rgba(0,0,0,.2);border-radius:8px;padding:6px 10px}
.calc-res-item .cr-val{font-size:14px;font-weight:800;color:var(--accent-cyan)}
.calc-res-item .cr-lbl{font-size:10px;color:var(--text-muted)}
/* ── AI Panel ── */
.ai-summary-box{background:linear-gradient(135deg,rgba(139,92,246,.12),rgba(59,130,246,.08));border:1px solid rgba(139,92,246,.35);border-radius:14px;padding:20px 24px;margin-bottom:22px;position:relative;overflow:hidden}
.ai-summary-box::before{content:'AI';position:absolute;top:-10px;right:16px;font-size:80px;font-weight:900;color:rgba(139,92,246,.07);line-height:1}
.ai-summary-title{font-size:13px;color:#a78bfa;text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-bottom:8px}
.ai-sentiment{font-size:22px;font-weight:800;color:#fff;margin-bottom:6px}
.ai-summary-text{font-size:13px;color:var(--text-muted);line-height:1.6}
.ai-stats-row{display:flex;gap:14px;flex-wrap:wrap;margin-top:14px;padding-top:14px;border-top:1px solid rgba(139,92,246,.2)}
.ai-stat{background:rgba(255,255,255,.05);border-radius:8px;padding:8px 14px;font-size:12px;color:var(--text-muted)}
.ai-stat span{display:block;font-size:16px;font-weight:800;color:#fff;margin-bottom:2px}
.ai-filter-bar{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;align-items:center}
.ai-tier-btn{background:transparent;border:1px solid var(--card-border);color:var(--text-muted);padding:7px 14px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;transition:all .2s}
.ai-tier-btn.active,.ai-tier-btn:hover{background:rgba(139,92,246,.2);border-color:rgba(139,92,246,.5);color:#a78bfa}
.ai-cards-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:16px}
.ai-stock-card{background:var(--card-bg);border:1px solid var(--card-border);border-radius:14px;overflow:hidden;transition:transform .2s,border-color .2s}
.ai-stock-card:hover{transform:translateY(-2px);border-color:rgba(139,92,246,.4)}
.ai-card-header{display:flex;justify-content:space-between;align-items:flex-start;padding:16px 18px 12px;border-bottom:1px solid var(--card-border)}
.ai-card-left .ai-company{font-size:15px;font-weight:800;color:#60a5fa;margin-bottom:3px}
.ai-card-left .ai-ticker{font-size:11px;color:var(--text-muted)}
.ai-tier-badge{padding:5px 12px;border-radius:20px;font-size:11px;font-weight:800;text-align:center;white-space:nowrap}
.ai-card-body{padding:14px 18px}
.ai-report-pre{font-family:'Inter',monospace;font-size:11px;color:var(--text-muted);white-space:pre-wrap;line-height:1.7;max-height:180px;overflow-y:auto;background:rgba(0,0,0,.2);border-radius:8px;padding:12px;border:1px solid var(--card-border)}
.ai-report-pre::-webkit-scrollbar{width:4px}
.ai-report-pre::-webkit-scrollbar-track{background:transparent}
.ai-report-pre::-webkit-scrollbar-thumb{background:#334155;border-radius:4px}
.ai-card-footer{display:flex;gap:8px;padding:12px 18px;background:rgba(0,0,0,.15);border-top:1px solid var(--card-border);flex-wrap:wrap;align-items:center}
.ai-trade-pill{font-size:11px;font-weight:700;padding:4px 10px;border-radius:6px;background:rgba(255,255,255,.06);color:var(--text-muted)}
.ai-trade-pill.entry{color:#60a5fa;background:rgba(59,130,246,.1)}
.ai-trade-pill.sl{color:#f87171;background:rgba(239,68,68,.1)}
.ai-trade-pill.t1{color:#34d399;background:rgba(16,185,129,.1)}
.btn-copy-report{margin-left:auto;background:transparent;border:1px solid rgba(139,92,246,.4);color:#a78bfa;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer;transition:all .2s}
.btn-copy-report:hover{background:rgba(139,92,246,.2);color:#fff}
.ai-warn{margin-top:8px;font-size:11px;color:#fbbf24;background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.2);border-radius:6px;padding:6px 10px;line-height:1.5}
</style>
</head>
<body>
<div class="container">
<!-- Header -->
<header>
  <div class="title-area">
    <h1>⚡ STOKS V4.2 — Enterprise Breakout Workstation</h1>
    <p>BB(20,2) + RSI(9)&gt;60 + Volume Surge | FII/DII Flows · Live News Catalysts · Charts · Heatmap · Backtesting · IPO Tracker</p>
  </div>
  <div class="header-actions">
    <button id="runScanBtn" class="btn-run-scan" onclick="triggerMarketScan()">
      <span class="spinner" id="scanSpinner"></span>
      <span id="scanBtnText">🔄 RUN SCAN NOW</span>
    </button>
    <button class="btn-action" onclick="exportActiveCSV()">📥 Export CSV</button>
    <div class="badge-status">LIVE V4.0 ACTIVE</div>
  </div>
</header>

<!-- Toast -->
<div id="toastNotice" style="display:none">
  <span id="toastIcon">💡</span><span id="toastText">Initializing...</span>
</div>

<!-- Tabs -->
<div class="nav-tabs">
  <button id="tab5yBtn"     class="tab-btn active" onclick="switchTab('FIVE_YEAR')">🚀 5-Year IPOs (<span id="cnt5y">""" + str(count_5y) + """</span>)</button>
  <button id="tabDailyBtn"  class="tab-btn"        onclick="switchTab('DAILY')">🎯 Daily Breakouts (<span id="cntDaily">""" + str(count_daily) + """</span>)</button>
  <button id="tabMonthlyBtn"class="tab-btn"        onclick="switchTab('MONTHLY')">📅 Monthly ATH (<span id="cntMonthly">""" + str(count_monthly) + """</span>)</button>
  <button id="tabSectorBtn" class="tab-btn"        onclick="switchTab('SECTOR')">🔥 Sector Heatmap</button>
  <button id="tabBtBtn"     class="tab-btn"        onclick="switchTab('BACKTEST')">⏮️ Backtesting (<span id="cntBt">""" + str(count_bt) + """</span>)</button>
  <button id="tabIpoBtn"    class="tab-btn"        onclick="switchTab('IPO_TRACKER')">🏆 IPO Tracker (<span id="cntIpo">""" + str(count_ipo) + """</span>)</button>
  <button id="tabAiBtn"     class="tab-btn"        onclick="switchTab('AI_ANALYSIS')">🤖 AI Analysis (<span id="cntAi">""" + str(count_ai) + """</span>)</button>
  <button id="tabGuideBtn"  class="tab-btn"        onclick="switchTab('GUIDE')">📚 Strategy Rules</button>
</div>

<!-- Metrics Row -->
<div class="metrics-grid" id="metricsRow">
  <div class="metric-card">
    <div class="label">Scan Results</div>
    <div class="val" id="totalMatches">0</div>
    <div class="sub">RSI(9) &gt; 60 + BB Breakout</div>
  </div>
  <div class="metric-card">
    <div class="label">FII Cash Net Flow</div>
    <div class="val" style="color:var(--accent-green)" id="fiiNetVal">Rs 0 Cr</div>
    <div class="sub" id="fiiNetSub">Institutional Flow</div>
  </div>
  <div class="metric-card">
    <div class="label">DII Cash Net Flow</div>
    <div class="val" style="color:var(--accent-cyan)" id="diiNetVal">Rs 0 Cr</div>
    <div class="sub" id="diiNetSub">Domestic Flow</div>
  </div>
  <div class="metric-card">
    <div class="label">Institutional Stance</div>
    <div class="val" style="font-size:15px;color:var(--accent-amber)" id="instStanceVal">NEUTRAL</div>
    <div class="sub" id="instStanceSub">Macro Bias</div>
  </div>
  <div class="metric-card">
    <div class="label">Top Volume Surge</div>
    <div class="val" style="color:var(--accent-amber)" id="topVolStock">—</div>
    <div class="sub" id="topVolVal">Spike: —</div>
  </div>
  <div class="metric-card">
    <div class="label">Highest RSI (9)</div>
    <div class="val" style="color:var(--accent-green)" id="topRsiStock">—</div>
    <div class="sub" id="topRsiVal">RSI: —</div>
  </div>
  <div class="metric-card">
    <div class="label">Avg Target 1 Gain</div>
    <div class="val" style="color:var(--accent-cyan)">+10.2%</div>
    <div class="sub">Conservative 1.5x R:R</div>
  </div>
</div>

<!-- Controls -->
<div class="controls-bar" id="controlsRow">
  <div class="search-box">
    <input type="text" id="searchInput" placeholder="Search company or symbol..." onkeyup="filterData()">
  </div>
  <div class="filter-group">
    <select id="volFilter" onchange="filterData()">
      <option value="ALL">All Volume Spikes</option>
      <option value="HIGH">High Surge (≥ 2x)</option>
      <option value="EXTREME">Extreme Surge (≥ 5x)</option>
    </select>
    <select id="sortFilter" onchange="filterData()">
      <option value="SCORE_DESC">Sort: Institutional Score ↓</option>
      <option value="VOL_DESC">Sort: Volume Spike ↓</option>
      <option value="RSI_DESC">Sort: RSI(9) ↓</option>
    </select>
  </div>
</div>

<!-- Main Table -->
<div class="table-container" id="tableContainer">
  <div class="table-scroll">
    <table><thead id="tableHeader"></thead><tbody id="tableBody"></tbody></table>
  </div>
</div>

<!-- Sector Heatmap Panel -->
<div id="sectorPanel" style="display:none">
  <div class="metrics-grid" style="margin-bottom:18px">
    <div class="metric-card">
      <div class="label">Total Sectors</div>
      <div class="val" id="totalSectors">—</div>
      <div class="sub">With breakout activity</div>
    </div>
    <div class="metric-card">
      <div class="label">Hottest Sector</div>
      <div class="val" style="font-size:18px" id="hottestSector">—</div>
      <div class="sub" id="hottestSectorSub">Most breakout stocks</div>
    </div>
    <div class="metric-card">
      <div class="label">Avg Score Across Sectors</div>
      <div class="val" style="color:var(--accent-cyan)" id="avgSectorScore">—</div>
      <div class="sub">Weighted composite</div>
    </div>
    <div class="metric-card">
      <div class="label">Last Sector Scan</div>
      <div class="val" style="font-size:16px" id="sectorScanTime">—</div>
      <div class="sub">Refresh by running scan</div>
    </div>
  </div>
  <div class="heatmap-grid" id="heatmapGrid"></div>
</div>

<!-- Backtest Panel -->
<div id="backtestPanel" style="display:none">
  <div class="bt-summary-grid" id="btSummaryGrid"></div>
  <div class="table-container">
    <div class="table-scroll">
      <table>
        <thead><tr>
          <th>Company / Ticker</th><th>Entry Date</th><th>Exit Date</th>
          <th>Entry ₹</th><th>Exit ₹</th><th>Gain %</th>
          <th>Days Held</th><th>Outcome</th>
        </tr></thead>
        <tbody id="btTableBody"></tbody>
      </table>
    </div>
  </div>
</div>

<!-- IPO Tracker Panel -->
<div id="ipoTrackerPanel" style="display:none">
  <div class="ipo-filter-bar" id="ipoYearFilter">
    <button class="ipo-year-btn active" onclick="filterIPOYear('ALL',this)">All Years</button>
    <button class="ipo-year-btn" onclick="filterIPOYear('2022',this)">2022</button>
    <button class="ipo-year-btn" onclick="filterIPOYear('2023',this)">2023</button>
    <button class="ipo-year-btn" onclick="filterIPOYear('2024',this)">2024</button>
    <button class="ipo-year-btn" onclick="filterIPOYear('2025',this)">2025</button>
    <button class="ipo-year-btn" onclick="filterIPOYear('2026',this)">2026</button>
    <input type="text" id="ipoSearchInput" placeholder="Search 925 IPOs..." onkeyup="renderIPOTable()" class="search-input" style="width:220px;padding:6px 12px;margin-left:8px;font-size:12px;border-radius:8px;background:var(--card-bg);border:1px solid var(--card-border);color:var(--text-main)">
    <select id="ipoExchangeSel" style="margin-left:8px" onchange="renderIPOTable()">
      <option value="ALL">All Exchanges</option>
      <option value="NSE">NSE Main Board</option>
      <option value="BSE">BSE Main Board</option>
    </select>
    <select id="ipoSortSel" style="margin-left:auto" onchange="renderIPOTable()">
      <option value="DATE_DESC">Sort: Newest First</option>
      <option value="NAME_ASC">Sort: Company Name (A-Z)</option>
      <option value="OVERALL_DESC">Sort: Overall Gain ↓</option>
      <option value="OVERALL_ASC">Sort: Overall Gain ↑ (Worst)</option>
    </select>
    <span id="ipoCounter" style="color:var(--text-muted);font-size:12px;margin-left:10px;font-weight:600"></span>
  </div>
  <div class="table-container">
    <div class="table-scroll">
      <table>
        <thead><tr>
          <th>Company / Ticker</th><th>Listed</th><th>IPO Price ₹</th>
          <th>Listing Day ₹</th><th>Current ₹</th>
          <th>Listing Gain</th><th>Overall Gain</th><th>Status</th><th>Charts</th>
        </tr></thead>
        <tbody id="ipoTableBody"></tbody>
      </table>
    </div>
  </div>
</div>

<!-- AI Analysis Panel -->
<div id="aiPanel" style="display:none">
  <div class="ai-summary-box" id="aiSummaryBox">
    <div class="ai-summary-title">🤖 STOKS AI — MARKET INTELLIGENCE REPORT</div>
    <div class="ai-sentiment" id="aiSentiment">Loading...</div>
    <div class="ai-summary-text" id="aiSummaryDesc"></div>
    <div class="ai-stats-row" id="aiStatsRow"></div>
  </div>
  <div class="ai-filter-bar">
    <button class="ai-tier-btn active" onclick="filterAiTier(0,this)">All Signals</button>
    <button class="ai-tier-btn" style="color:#ef4444" onclick="filterAiTier(1,this)">🔴 Premium</button>
    <button class="ai-tier-btn" style="color:#f97316" onclick="filterAiTier(2,this)">🍑 Strong</button>
    <button class="ai-tier-btn" style="color:#f59e0b" onclick="filterAiTier(3,this)">🟡 Moderate</button>
    <button class="ai-tier-btn" style="color:#10b981" onclick="filterAiTier(4,this)">🟢 Watch</button>
    <span id="aiSignalCount" style="margin-left:auto;font-size:12px;color:var(--text-muted)"></span>
  </div>
  <div class="ai-cards-grid" id="aiCardsGrid"></div>
</div>

<!-- Guide Panel -->
<div class="guide-box" id="guideContainer" style="display:none">
  <h2>📚 STOKS V4.1 AI — Enterprise Strategy Specification</h2>
  <div class="guide-grid">
    <div class="guide-card"><h4>1. Bollinger Bands (20,2) Breakout</h4><p>Close Price strictly crosses above the Upper Bollinger Band (SMA 20 + 2 StdDev), signalling volatility expansion and bullish trend entry.</p></div>
    <div class="guide-card"><h4>2. RSI (9) Fast Momentum Trigger</h4><p>Updated RSI period = 9 (Fast Momentum). RSI must be strictly above 60 to confirm high-speed price momentum and institutional buying strength.</p></div>
    <div class="guide-card"><h4>3. Volume Surge Multiplier (1.5x – 13x)</h4><p>Today's volume must exceed 1.5x the 20-day Average Volume to eliminate low-volume false breakouts.</p></div>
    <div class="guide-card"><h4>4. Price Action Target 1 & 2</h4><p>Target 1 (+10%): 1.5x Risk-Reward.<br>Target 2 (+17%): 2.5x Risk-Reward & Fibonacci 1.618 ATH Extension.</p></div>
    <div class="guide-card"><h4>5. Dynamic ATR Trailing Stop Loss</h4><p>Stop-Loss anchored at 2× ATR(14) or 20-day SMA (~3%–6% risk), whichever is closer.</p></div>
    <div class="guide-card"><h4>6. Charts & Backtesting (V4.0 NEW)</h4><p>Click any stock to see 90-day price chart with BB overlay + RSI sub-chart. Backtest tab shows historical win rate and avg gain on this exact strategy.</p></div>
    <div class="guide-card"><h4>7. Sector Heatmap (V4.0 NEW)</h4><p>Visual heatmap showing which market sectors have the most breakout activity. Helps identify sector rotation and hot money flow themes.</p></div>
    <div class="guide-card"><h4>8. IPO Performance Tracker (V4.0 NEW)</h4><p>Tracks all BSE+NSE IPOs from 2021–2026. Shows listing gain vs current gain vs IPO price. Identify multibaggers and laggards.</p></div>
    <div class="guide-card"><h4>9. Scanned Universes</h4><p>BSE Main Board IPOs (2021–2026) + NSE Main Board IPOs (2021–2026) + NSE Top Stocks Universe (pre-2021 large caps).</p></div>
  </div>
</div>

</div><!-- /container -->

<!-- Chart Modal -->
<div class="modal-overlay" id="chartModal" onclick="closeChartModal(event)">
  <div class="modal-box" id="chartModalBox">
    <div class="modal-header">
      <div>
        <div class="modal-title" id="modalStockName">—</div>
        <div class="modal-subtitle" id="modalStockTicker">Loading chart data...</div>
      </div>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-levels" id="modalLevels"></div>
    <!-- Position Size & Risk Calculator -->
    <div class="risk-calc-box">
      <div class="calc-field">
        <label>Account Capital (₹)</label>
        <input type="number" id="calcCapital" value="500000" oninput="calcPositionSize()">
      </div>
      <div class="calc-field">
        <label>Risk Per Trade %</label>
        <input type="number" id="calcRiskPct" value="2.0" step="0.5" oninput="calcPositionSize()">
      </div>
      <div class="calc-res-item">
        <div class="cr-val" id="resMaxRisk" style="color:var(--accent-red)">₹10,000</div>
        <div class="cr-lbl">Max Risk (₹)</div>
      </div>
      <div class="calc-res-item">
        <div class="cr-val" id="resQty" style="color:var(--accent-green)">—</div>
        <div class="cr-lbl">Shares to Buy</div>
      </div>
      <div class="calc-res-item">
        <div class="cr-val" id="resPosValue">₹0</div>
        <div class="cr-lbl">Position Capital (₹)</div>
      </div>
    </div>
    <div id="chartContainer"><div class="chart-loading">⏳ Loading chart...</div></div>
    <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px;padding:0 4px">RSI (9) — Fast Momentum Indicator</div>
    <div id="rsiContainer"></div>
    <div style="margin-top:12px;font-size:11px;color:var(--text-muted);text-align:center">
      💡 Chart data sourced from Yahoo Finance. Click outside to close. 
      <a id="modalTVLink" href="#" target="_blank" style="color:#60a5fa;font-weight:700;margin-left:8px">Open Full Chart on TradingView ↗</a>
    </div>
  </div>
</div>

<script>
// ── Data ──────────────────────────────────────────────────────────
const data5y      = """ + records_5y + """;
const dataDaily   = """ + records_daily + """;
const dataMonthly = """ + records_monthly + """;
const dataIpo     = """ + records_ipo + """;
const dataBt      = """ + records_bt + """;
const dataSector  = """ + records_sector + """;
const btSummary   = """ + bt_summary + """;
const aiReport    = """ + ai_report + """;
const fiiDiiData  = """ + fii_dii_json + """;
const stockNewsData = """ + news_json + """;

let currentTab = 'FIVE_YEAR';
let currentFilteredData = [];
let ipoYearFilter = 'ALL';
let ipoFilteredData = [...dataIpo];
let aiTierFilter = 0;
let aiFilteredReports = [];

// ── Toast ─────────────────────────────────────────────────────────
function showToast(m, i) {
  const t = document.getElementById('toastNotice');
  document.getElementById('toastIcon').innerText = i || '💡';
  document.getElementById('toastText').innerText = m;
  t.style.display = 'flex';
  setTimeout(() => { t.style.display = 'none'; }, 5000);
}

// ── Scan Trigger ──────────────────────────────────────────────────
async function triggerMarketScan() {
  const b = document.getElementById('runScanBtn');
  const s = document.getElementById('scanSpinner');
  const t = document.getElementById('scanBtnText');
  b.disabled = true; s.style.display = 'inline-block'; t.innerText = '⏳ SCANNING...';
  showToast('Running full market scan in background...', '⚡');
  try {
    const r = await fetch('/api/scan', { method: 'POST' });
    if (r.ok) {
      showToast('Scan complete! Reloading data...', '✅');
      setTimeout(() => window.location.reload(), 1200);
    } else {
      showToast('Server error. Ensure server.py is running.', '⚠️');
      b.disabled = false; s.style.display = 'none'; t.innerText = '🔄 RUN SCAN NOW';
    }
  } catch(e) {
    showToast('Scan triggered! Check terminal output.', 'ℹ️');
    b.disabled = false; s.style.display = 'none'; t.innerText = '🔄 RUN SCAN NOW';
  }
}

// ── Tab Switcher ──────────────────────────────────────────────────
function switchTab(t) {
  currentTab = t;
  const tabs = ['FIVE_YEAR','DAILY','MONTHLY','SECTOR','BACKTEST','IPO_TRACKER','AI_ANALYSIS','GUIDE'];
  const btns = ['tab5yBtn','tabDailyBtn','tabMonthlyBtn','tabSectorBtn','tabBtBtn','tabIpoBtn','tabAiBtn','tabGuideBtn'];
  btns.forEach((b,i) => document.getElementById(b) && document.getElementById(b).classList.toggle('active', tabs[i] === t));

  // Show/hide panels
  const showMain    = ['FIVE_YEAR','DAILY','MONTHLY'].includes(t);
  const showSector  = t === 'SECTOR';
  const showBacktest= t === 'BACKTEST';
  const showIPO     = t === 'IPO_TRACKER';
  const showAI      = t === 'AI_ANALYSIS';
  const showGuide   = t === 'GUIDE';

  document.getElementById('metricsRow').style.display    = showMain ? 'grid' : 'none';
  document.getElementById('controlsRow').style.display   = showMain ? 'flex' : 'none';
  document.getElementById('tableContainer').style.display= showMain ? 'block' : 'none';
  document.getElementById('sectorPanel').style.display   = showSector ? 'block' : 'none';
  document.getElementById('backtestPanel').style.display = showBacktest ? 'block' : 'none';
  document.getElementById('ipoTrackerPanel').style.display = showIPO ? 'block' : 'none';
  document.getElementById('aiPanel').style.display       = showAI ? 'block' : 'none';
  document.getElementById('guideContainer').style.display= showGuide ? 'block' : 'none';

  if (showMain) filterData();
  if (showSector) renderSectorHeatmap();
  if (showBacktest) renderBacktest();
  if (showIPO) renderIPOTable();
  if (showAI) renderAIPanel();
}

// ── Filter & Sort (Main Tables) ───────────────────────────────────
function filterData() {
  const s = document.getElementById('searchInput').value.toUpperCase();
  const v = document.getElementById('volFilter').value;
  const o = document.getElementById('sortFilter').value;
  let d = currentTab==='FIVE_YEAR' ? data5y : currentTab==='DAILY' ? dataDaily : dataMonthly;

  let f = d.filter(x => {
    const ms = (!s) || (x.Company_Name&&x.Company_Name.toUpperCase().includes(s)) || (x.Ticker&&x.Ticker.toUpperCase().includes(s));
    let mv = true;
    const vsp = parseFloat((x.Volume_Spike||'0').toString().replace('x',''));
    if (v==='HIGH') mv = vsp >= 2;
    else if (v==='EXTREME') mv = vsp >= 5;
    return ms && mv;
  });

  if (o==='SCORE_DESC') f.sort((a,b)=>(b.Strength_Score||0)-(a.Strength_Score||0));
  else if (o==='VOL_DESC') f.sort((a,b)=>parseFloat((b.Volume_Spike||'0').replace('x',''))-parseFloat((a.Volume_Spike||'0').replace('x','')));
  else if (o==='RSI_DESC') f.sort((a,b)=>(b.RSI_9||b.Monthly_RSI_9||0)-(a.RSI_9||a.Monthly_RSI_9||0));

  currentFilteredData = f;
  document.getElementById('totalMatches').innerText = f.length;

  // Populate FII/DII Flow Cards
  if (fiiDiiData && fiiDiiData.institutional_bias) {
    const fiiN = fiiDiiData.fii_cash_net || 0;
    const diiN = fiiDiiData.dii_cash_net || 0;
    document.getElementById('fiiNetVal').innerText = (fiiN >= 0 ? '+Rs ' : '-Rs ') + Math.abs(fiiN).toLocaleString() + ' Cr';
    document.getElementById('fiiNetVal').style.color = fiiN >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
    document.getElementById('fiiNetSub').innerText = fiiDiiData.date || 'Today';

    document.getElementById('diiNetVal').innerText = (diiN >= 0 ? '+Rs ' : '-Rs ') + Math.abs(diiN).toLocaleString() + ' Cr';
    document.getElementById('diiNetVal').style.color = diiN >= 0 ? 'var(--accent-cyan)' : 'var(--accent-red)';
    document.getElementById('diiNetSub').innerText = fiiDiiData.date || 'Today';

    document.getElementById('instStanceVal').innerText = fiiDiiData.institutional_bias;
    document.getElementById('instStanceVal').style.color = fiiDiiData.bias_color || 'var(--accent-amber)';
    document.getElementById('instStanceSub').innerText = 'Combined Net Flow';
  }

  if (f.length > 0) {
    const mv = [...f].sort((a,b)=>parseFloat((b.Volume_Spike||'0').replace('x',''))-parseFloat((a.Volume_Spike||'0').replace('x','')))[0];
    if (mv) {
      document.getElementById('topVolStock').innerText = (mv.Company_Name||'').split(' ')[0] || '—';
      document.getElementById('topVolVal').innerText = 'Spike: ' + (mv.Volume_Spike || '—');
    }
    const mr = [...f].sort((a,b)=>(b.RSI_9||b.Monthly_RSI_9||0)-(a.RSI_9||a.Monthly_RSI_9||0))[0];
    if (mr) {
      document.getElementById('topRsiStock').innerText = (mr.Company_Name||'').split(' ')[0] || '—';
      document.getElementById('topRsiVal').innerText = 'RSI: ' + (mr.RSI_9||mr.Monthly_RSI_9||'—');
    }
  }
  renderTable(f);
}

// ── Render Main Table ─────────────────────────────────────────────
function renderTable(d) {
  const th = document.getElementById('tableHeader');
  const tb = document.getElementById('tableBody');
  tb.innerHTML = '';
  if (!d || d.length === 0) {
    th.innerHTML = '';
    tb.innerHTML = '<tr><td colspan="12"><div class="no-data"><div class="nd-icon">🔍</div><p>No breakout signals found. Try running a scan.</p></div></td></tr>';
    return;
  }
  if (currentTab === 'MONTHLY') {
    th.innerHTML = '<tr><th>Company / Ticker</th><th>Universe</th><th>Listed</th><th>Monthly Close ₹</th><th>Prev ATH ₹</th><th>ATH Gain %</th><th>Monthly RSI(9)</th><th>Category</th><th>Charts</th></tr>';
    d.forEach(i => {
      const isB = i.Ticker.endsWith('.BO');
      const ex = isB ? 'BSE' : 'NSE';
      const sy = i.Ticker.replace('.NS','').replace('.BO','');
      const tv = 'https://in.tradingview.com/chart/?symbol='+ex+':'+sy;
      const ci = 'https://chartink.com/stocks/'+sy.toLowerCase()+'.html';
      const tr = document.createElement('tr');
      tr.innerHTML = '<td><span class="stock-symbol" onclick="openChartModal('+JSON.stringify(i)+')">'+(i.Company_Name||i.Ticker)+'</span><br><small style="color:var(--text-muted)">'+i.Ticker+'</small></td>'+
        '<td><span style="font-size:11px;color:var(--text-muted)">'+(i.Universe||'')+'</span></td>'+
        '<td style="font-size:11px">'+(i.Listed_Date||'—')+'</td>'+
        '<td style="font-weight:700">₹'+numFmt(i.Monthly_Close)+'</td>'+
        '<td>₹'+numFmt(i.Prev_Monthly_ATH_High)+'</td>'+
        '<td style="color:#34d399;font-weight:700">'+(i.Monthly_ATH_Diff_Pct||'—')+'</td>'+
        '<td style="font-weight:700;color:#34d399">'+(i.Monthly_RSI_9||'—')+'</td>'+
        '<td style="font-size:11px;font-weight:600;color:#fbbf24">'+(i.Breakout_Category||'—')+'</td>'+
        '<td><div class="chart-links-group"><a href="'+tv+'" target="_blank" class="tv-btn">TV ↗</a><a href="'+ci+'" target="_blank" class="chartink-btn">Chartink ↗</a></div></td>';
      tb.appendChild(tr);
    });
  } else {
    th.innerHTML = '<tr><th>Company / Ticker</th><th>Score</th><th>Listed</th><th>Close ₹</th><th>Vol Surge</th><th>RSI(9)</th><th>Stop Loss</th><th>Target 1 (+10%)</th><th>Target 2 (+17%)</th><th>R:R</th><th>Chart</th><th>Links</th></tr>';
    d.forEach(i => {
      const isB = i.Ticker.endsWith('.BO');
      const ex = isB ? 'BSE' : 'NSE';
      const sy = i.Ticker.replace('.NS','').replace('.BO','');
      const tv = 'https://in.tradingview.com/chart/?symbol='+ex+':'+sy;
      const ci = 'https://chartink.com/stocks/'+sy.toLowerCase()+'.html';
      let scCls = 'score-mid';
      if ((i.Strength_Score||0) >= 85) scCls = 'score-high';
      else if ((i.Strength_Score||0) < 70) scCls = 'score-low';
      const tr = document.createElement('tr');
      tr.innerHTML = '<td><span class="stock-symbol" onclick="openChartModal('+JSON.stringify(i)+')">'+(i.Company_Name||i.Ticker)+'</span><br><small style="color:var(--text-muted)">'+i.Ticker+'</small></td>'+
        '<td><span class="score-pill '+scCls+'">'+(i.Strength_Score||80)+'/100</span></td>'+
        '<td style="font-size:11px;color:var(--text-muted)">'+(i.Listed_Date||'—')+'</td>'+
        '<td style="font-weight:700">₹'+numFmt(i.Close||i.Entry_Price)+'</td>'+
        '<td><span class="vol-badge">'+(i.Volume_Spike||'—')+'</span></td>'+
        '<td style="font-weight:700;color:#34d399">'+(i.RSI_9||'—')+'</td>'+
        '<td class="sl-price">₹'+numFmt(i.Stop_Loss)+'</td>'+
        '<td class="target1-price">₹'+numFmt(i.Target_1)+' <small style="color:var(--accent-green);font-weight:600">'+(i['Target_1_Gain_%']||i.Target_1_Gain_Pct||'+10%')+'</small></td>'+
        '<td class="target2-price">₹'+numFmt(i.Target_2)+' <small style="color:var(--accent-purple);font-weight:600">'+(i['Target_2_Gain_%']||i.Target_2_Gain_Pct||'+17%')+'</small></td>'+
        '<td style="font-weight:600">'+(i.Risk_Reward||'—')+'</td>'+
        '<td><button class="chart-btn-inline" onclick="openChartModal('+JSON.stringify(i)+')">📈 Chart</button></td>'+
        '<td><div class="chart-links-group"><a href="'+tv+'" target="_blank" class="tv-btn">TV ↗</a><a href="'+ci+'" target="_blank" class="chartink-btn">CI ↗</a></div></td>';
      tb.appendChild(tr);
    });
  }
}

// ── Chart Modal ───────────────────────────────────────────────────
let chartInstance = null;
let rsiChartInstance = null;
let currentModalStock = null;

function calcPositionSize() {
  if (!currentModalStock) return;
  const capital = parseFloat(document.getElementById('calcCapital').value) || 500000;
  const riskPct = parseFloat(document.getElementById('calcRiskPct').value) || 2.0;
  const entry = parseFloat(currentModalStock.Close || currentModalStock.Entry_Price || currentModalStock.Monthly_Close || 0);
  const sl = parseFloat(currentModalStock.Stop_Loss || 0);

  const maxRisk = (capital * riskPct) / 100.0;
  document.getElementById('resMaxRisk').innerText = '₹' + Math.round(maxRisk).toLocaleString();

  if (entry > 0 && sl > 0 && entry > sl) {
    const riskPerShare = entry - sl;
    const qty = Math.floor(maxRisk / riskPerShare);
    const posVal = Math.round(qty * entry);
    const posPct = ((posVal / capital) * 100).toFixed(1);
    document.getElementById('resQty').innerText = qty.toLocaleString() + ' shares';
    document.getElementById('resPosValue').innerText = '₹' + posVal.toLocaleString() + ' (' + posPct + '%)';
  } else {
    document.getElementById('resQty').innerText = '—';
    document.getElementById('resPosValue').innerText = '₹0';
  }
}

function openChartModal(stock) {
  document.getElementById('chartModal').classList.add('open');
  currentModalStock = typeof stock === 'string' ? { Ticker: stock, Close: 0, Stop_Loss: 0 } : stock;
  calcPositionSize();

  const ticker = typeof stock === 'string' ? stock : (stock.Ticker || '');
  const company = typeof stock === 'string' ? stock : (stock.Company_Name || ticker);
  const isB = ticker.endsWith('.BO');
  const ex = isB ? 'BSE' : 'NSE';
  const sy = ticker.replace('.NS','').replace('.BO','');
  document.getElementById('modalStockName').innerText = company;
  document.getElementById('modalStockTicker').innerText = ticker + ' | ' + ex;
  document.getElementById('modalTVLink').href = 'https://in.tradingview.com/chart/?symbol='+ex+':'+sy;

  // Levels
  const entryVal = typeof stock === 'object' ? (stock.Close || stock.Entry_Price) : null;
  const slVal = typeof stock === 'object' ? stock.Stop_Loss : null;
  const t1Val = typeof stock === 'object' ? stock.Target_1 : null;
  const t2Val = typeof stock === 'object' ? stock.Target_2 : null;
  const t3Val = typeof stock === 'object' ? stock.Target_3 : null;

  const levelsHtml = [
    entryVal ? '<span class="level-badge level-entry">📍 Entry: ₹'+numFmt(entryVal)+'</span>' : '',
    slVal ? '<span class="level-badge level-sl">🛑 SL: ₹'+numFmt(slVal)+'</span>' : '',
    t1Val ? '<span class="level-badge level-t1">🎯 T1: ₹'+numFmt(t1Val)+'</span>' : '',
    t2Val ? '<span class="level-badge level-t2">🚀 T2: ₹'+numFmt(t2Val)+'</span>' : '',
    t3Val ? '<span class="level-badge level-t3">🌙 T3: ₹'+numFmt(t3Val)+'</span>' : '',
  ].join('');
  document.getElementById('modalLevels').innerHTML = levelsHtml;

  // Show loading
  document.getElementById('chartContainer').innerHTML = '<div class="chart-loading">⏳ Fetching chart data from Yahoo Finance...</div>';
  document.getElementById('rsiContainer').innerHTML = '';

  // Fetch & render chart via proxy
  fetch('/api/chart?ticker='+encodeURIComponent(ticker)+'&period=90d')
    .then(r => r.json())
    .then(data => renderLightweightChart(data, stock))
    .catch(() => {
      document.getElementById('chartContainer').innerHTML =
        '<div class="chart-loading" style="flex-direction:column;gap:16px">' +
        '<div style="font-size:40px">📊</div>' +
        '<div>Chart data not available offline.<br>Click <a href="https://in.tradingview.com/chart/?symbol='+ex+':'+sy+'" target="_blank" style="color:#60a5fa;font-weight:700">TradingView ↗</a> for live chart.</div>' +
        '</div>';
    });
}

function renderLightweightChart(data, stock) {
  const chartEl = document.getElementById('chartContainer');
  const rsiEl = document.getElementById('rsiContainer');
  chartEl.innerHTML = '';
  rsiEl.innerHTML = '';

  if (!data || !data.candles || data.candles.length === 0) {
    chartEl.innerHTML = '<div class="chart-loading">No chart data available. <a href="#" onclick="closeModal()" style="color:#60a5fa">Close</a> and use TradingView link.</div>';
    return;
  }

  // Price chart
  const chart = LightweightCharts.createChart(chartEl, {
    width: chartEl.clientWidth,
    height: 330,
    layout: { background: { color: '#0d1525' }, textColor: '#94a3b8' },
    grid: { vertLines: { color: '#1e2d4a' }, horzLines: { color: '#1e2d4a' } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: '#1e2d4a' },
    timeScale: { borderColor: '#1e2d4a', timeVisible: true },
  });

  const candleSeries = chart.addCandlestickSeries({
    upColor: '#10b981', downColor: '#ef4444',
    borderUpColor: '#10b981', borderDownColor: '#ef4444',
    wickUpColor: '#10b981', wickDownColor: '#ef4444',
  });
  candleSeries.setData(data.candles);

  // Upper BB line
  if (data.bb_upper) {
    const bbSeries = chart.addLineSeries({ color: '#8b5cf6', lineWidth: 1.5, lineStyle: 2, title: 'BB Upper' });
    bbSeries.setData(data.bb_upper);
  }
  // BB SMA line
  if (data.bb_mid) {
    const bbMidSeries = chart.addLineSeries({ color: '#3b82f6', lineWidth: 1, lineStyle: 3, title: 'BB Mid' });
    bbMidSeries.setData(data.bb_mid);
  }

  // Horizontal price levels
  const entryPrice = stock.Close || stock.Entry_Price;
  if (entryPrice) {
    candleSeries.createPriceLine({ price: entryPrice, color: '#3b82f6', lineWidth: 1, lineStyle: 1, axisLabelVisible: true, title: 'Entry' });
  }
  if (stock.Stop_Loss) {
    candleSeries.createPriceLine({ price: stock.Stop_Loss, color: '#ef4444', lineWidth: 1, lineStyle: 1, axisLabelVisible: true, title: 'SL' });
  }
  if (stock.Target_1) {
    candleSeries.createPriceLine({ price: stock.Target_1, color: '#10b981', lineWidth: 1, lineStyle: 1, axisLabelVisible: true, title: 'T1' });
  }
  if (stock.Target_2) {
    candleSeries.createPriceLine({ price: stock.Target_2, color: '#8b5cf6', lineWidth: 1, lineStyle: 1, axisLabelVisible: true, title: 'T2' });
  }

  chart.timeScale().fitContent();
  chartInstance = chart;

  // RSI sub-chart
  if (data.rsi) {
    const rsiChart = LightweightCharts.createChart(rsiEl, {
      width: rsiEl.clientWidth,
      height: 130,
      layout: { background: { color: '#0d1525' }, textColor: '#94a3b8' },
      grid: { vertLines: { color: '#1e2d4a' }, horzLines: { color: '#1e2d4a' } },
      rightPriceScale: { borderColor: '#1e2d4a', scaleMargins: { top: 0.1, bottom: 0.1 } },
      timeScale: { borderColor: '#1e2d4a', timeVisible: true },
    });
    const rsiSeries = rsiChart.addLineSeries({ color: '#00f5d4', lineWidth: 2, title: 'RSI(9)' });
    rsiSeries.setData(data.rsi);
    rsiSeries.createPriceLine({ price: 60, color: '#f59e0b', lineWidth: 1, lineStyle: 2, title: 'RSI 60' });
    rsiSeries.createPriceLine({ price: 30, color: '#ef4444', lineWidth: 1, lineStyle: 2, title: 'RSI 30' });
    rsiChart.timeScale().fitContent();
    rsiChartInstance = rsiChart;
  }
}

function closeModal() {
  document.getElementById('chartModal').classList.remove('open');
  if (chartInstance) { chartInstance.remove(); chartInstance = null; }
  if (rsiChartInstance) { rsiChartInstance.remove(); rsiChartInstance = null; }
}
function closeChartModal(e) {
  if (e.target.id === 'chartModal') closeModal();
}

// ── Sector Heatmap ────────────────────────────────────────────────
function renderSectorHeatmap() {
  const grid = document.getElementById('heatmapGrid');
  grid.innerHTML = '';

  if (!dataSector || dataSector.length === 0) {
    grid.innerHTML = '<div class="no-data" style="grid-column:1/-1"><div class="nd-icon">🔥</div><p>No sector data yet. Run a scan to generate sector heatmap.</p></div>';
    document.getElementById('totalSectors').innerText = '—';
    document.getElementById('hottestSector').innerText = '—';
    document.getElementById('avgSectorScore').innerText = '—';
    document.getElementById('sectorScanTime').innerText = '—';
    return;
  }

  document.getElementById('totalSectors').innerText = dataSector.length;
  const hottest = dataSector[0];
  document.getElementById('hottestSector').innerText = (hottest.emoji||'') + ' ' + (hottest.sector||'—');
  document.getElementById('hottestSectorSub').innerText = hottest.count + ' breakout stocks';
  const totalScores = dataSector.reduce((a,b) => a + (b.avg_score||0), 0);
  document.getElementById('avgSectorScore').innerText = Math.round(totalScores / dataSector.length);
  document.getElementById('sectorScanTime').innerText = 'Last Scan';

  dataSector.forEach(sec => {
    const card = document.createElement('div');
    card.className = 'sector-card';
    card.style.setProperty('--sc-color', sec.color || '#64748b');
    const intensity = Math.min(sec.count / 5, 1);
    card.style.boxShadow = `0 0 ${Math.round(intensity * 20)}px ${sec.color}22`;

    const stocksHtml = (sec.stocks || []).slice(0, 8).map(s =>
      '<div class="sector-stock-item">' +
      '<span style="color:var(--text-main);font-weight:600">' + (s.name||'').split(' ')[0] + '</span>' +
      '<span style="color:' + (sec.color||'#64748b') + ';font-weight:700">' + (s.score||0) + '/100</span>' +
      '</div>'
    ).join('');

    card.innerHTML =
      '<div class="sector-header">' +
        '<div><div class="sector-name">' + (sec.sector||'Unknown') + '</div><div style="font-size:11px;color:var(--text-muted);margin-top:3px">' + (sec.count||0) + ' breakout stocks</div></div>' +
        '<div>' +
          '<div class="sector-emoji">' + (sec.emoji||'🔷') + '</div>' +
          '<div class="sector-count" style="text-align:center;margin-top:4px">' + (sec.count||0) + '</div>' +
        '</div>' +
      '</div>' +
      '<div class="sector-stats">' +
        '<div class="sector-stat"><div class="s-label">Avg Score</div><div class="s-val" style="color:' + (sec.color||'#64748b') + '">' + (sec.avg_score||0) + '</div></div>' +
        '<div class="sector-stat"><div class="s-label">Avg RSI(9)</div><div class="s-val">' + (sec.avg_rsi||0) + '</div></div>' +
      '</div>' +
      '<div class="sector-top-stock">🏆 Top: <span>' + (sec.top_stock||'—') + '</span></div>' +
      '<div style="margin-top:10px;text-align:right"><button class="btn-copy-report" data-sec="' + (sec.sector||'') + '" onclick="filterMainBySector(this, event)" style="font-size:10px;padding:3px 8px">Filter Breakouts ↗</button></div>' +
      '<div class="sector-stocks-list" id="secList_' + sec.sector.replace(/\s+/g,'_') + '">' + stocksHtml + '</div>';

    card.addEventListener('click', (e) => {
      if (e.target.tagName === 'BUTTON' || e.target.closest('button')) return;
      const listId = 'secList_' + sec.sector.replace(/\s+/g,'_');
      const el = document.getElementById(listId);
      if (el) el.classList.toggle('open');
    });
    grid.appendChild(card);
  });
}

function filterMainBySector(secName, evt) {
  if (evt) evt.stopPropagation();
  switchTab('DAILY');
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.value = secName;
    filterData();
    showToast('Filtered breakout stocks for ' + secName, '🔍');
  }
}

// ── Backtest Panel ────────────────────────────────────────────────
function renderBacktest() {
  const summaryGrid = document.getElementById('btSummaryGrid');
  const tbody = document.getElementById('btTableBody');
  summaryGrid.innerHTML = '';

  const s = btSummary;
  if (!s || s.total_trades === 0) {
    summaryGrid.innerHTML = '<div class="no-data" style="grid-column:1/-1"><div class="nd-icon">⏮️</div><p>No backtest data yet. Run a scan to generate backtesting results.</p></div>';
    tbody.innerHTML = '';
    return;
  }

  const cards = [
    { label: 'Total Trades', val: s.total_trades, sub: 'Historical signals', cls: '' },
    { label: 'Win Rate', val: s.win_rate_pct + '%', sub: s.wins + ' winning trades', cls: 'outcome-win' },
    { label: 'Avg Win Gain', val: '+' + s.avg_gain_pct + '%', sub: 'Per winning trade', cls: 'outcome-win' },
    { label: 'Avg Loss', val: s.avg_loss_pct + '%', sub: 'Per losing trade', cls: 'outcome-loss' },
    { label: 'Expectancy', val: (s.expectancy_pct > 0 ? '+' : '') + s.expectancy_pct + '%', sub: 'Per trade expected', cls: s.expectancy_pct >= 0 ? 'outcome-win' : 'outcome-loss' },
    { label: 'Best Trade', val: '+' + s.best_trade_pct + '%', sub: 'Max single gain', cls: 'outcome-win' },
    { label: 'Worst Trade', val: s.worst_trade_pct + '%', sub: 'Max single loss', cls: 'outcome-loss' },
    { label: 'Avg Days Held', val: s.avg_days_held, sub: 'Days to exit', cls: '' },
  ];

  cards.forEach(c => {
    const card = document.createElement('div');
    card.className = 'bt-card';
    card.innerHTML = '<div class="b-label">' + c.label + '</div><div class="b-val ' + c.cls + '">' + c.val + '</div><div class="b-sub">' + c.sub + '</div>';
    summaryGrid.appendChild(card);
  });

  tbody.innerHTML = '';
  if (!dataBt || dataBt.length === 0) return;
  [...dataBt].sort((a,b) => (b.Gain_Pct||0) - (a.Gain_Pct||0)).forEach(row => {
    const tr = document.createElement('tr');
    const gainCls = (row.Gain_Pct||0) > 0 ? 'gain-positive' : 'gain-negative';
    const outcomeCls = row.Outcome === 'WIN' ? 'badge-win' : row.Outcome === 'LOSS' ? 'badge-loss' : 'badge-timeout';
    tr.innerHTML =
      '<td><span style="font-weight:700;color:#60a5fa">' + (row.Company||row.Ticker||'') + '</span><br><small style="color:var(--text-muted)">' + (row.Ticker||'') + '</small></td>' +
      '<td style="font-size:12px;color:var(--text-muted)">' + (row.Entry_Date||'—') + '</td>' +
      '<td style="font-size:12px;color:var(--text-muted)">' + (row.Exit_Date||'—') + '</td>' +
      '<td style="font-weight:700">₹' + numFmt(row.Entry_Price) + '</td>' +
      '<td style="font-weight:700">₹' + numFmt(row.Exit_Price) + '</td>' +
      '<td class="' + gainCls + '">' + (row.Gain_Pct > 0 ? '+' : '') + (row.Gain_Pct||0) + '%</td>' +
      '<td>' + (row.Days_Held||0) + 'd</td>' +
      '<td><span class="outcome-badge ' + outcomeCls + '">' + (row.Outcome||'—') + '</span></td>';
    tbody.appendChild(tr);
  });
}

// ── IPO Tracker ───────────────────────────────────────────────────
function filterIPOYear(year, btn) {
  ipoYearFilter = year;
  document.querySelectorAll('.ipo-year-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  renderIPOTable();
}

function triggerIpoModal(btn, evt) {
  if (evt) evt.stopPropagation();
  const ticker = btn.getAttribute('data-ticker');
  const name = btn.getAttribute('data-name');
  openChartModal(ticker, name, '75', '80', '1.8x', '0', '0', '0', '0', '0');
}

function renderIPOTable() {
  const sort = document.getElementById('ipoSortSel') ? document.getElementById('ipoSortSel').value : 'DATE_DESC';
  const query = document.getElementById('ipoSearchInput') ? document.getElementById('ipoSearchInput').value.toUpperCase().trim() : '';
  const exFilter = document.getElementById('ipoExchangeSel') ? document.getElementById('ipoExchangeSel').value : 'ALL';
  let d = [...dataIpo];

  if (ipoYearFilter !== 'ALL') {
    d = d.filter(x => String(x.Listing_Year) === ipoYearFilter);
  }

  if (exFilter === 'NSE') {
    d = d.filter(x => (x.Exchange || '').includes('NSE') || (x.Ticker || '').endsWith('.NS'));
  } else if (exFilter === 'BSE') {
    d = d.filter(x => (x.Exchange || '').includes('BSE') || (x.Ticker || '').endsWith('.BO'));
  }

  if (query) {
    d = d.filter(x => (x.Company_Name || '').toUpperCase().includes(query) || (x.Ticker || '').toUpperCase().includes(query));
  }

  if (sort === 'OVERALL_DESC') d.sort((a,b) => (b.Overall_Gain_Pct||0) - (a.Overall_Gain_Pct||0));
  else if (sort === 'OVERALL_ASC') d.sort((a,b) => (a.Overall_Gain_Pct||0) - (b.Overall_Gain_Pct||0));
  else if (sort === 'LISTING_DESC') d.sort((a,b) => (b.Listing_Gain_Pct||0) - (a.Listing_Gain_Pct||0));
  else if (sort === 'NAME_ASC') d.sort((a,b) => (a.Company_Name||'').localeCompare(b.Company_Name||''));
  else if (sort === 'DATE_DESC') d.sort((a,b) => (b.Listed_Date||'').localeCompare(a.Listed_Date||''));

  ipoFilteredData = d;
  const counterEl = document.getElementById('ipoCounter');
  if (counterEl) counterEl.innerText = 'Showing ' + d.length + ' of ' + dataIpo.length + ' IPOs';

  const tbody = document.getElementById('ipoTableBody');
  tbody.innerHTML = '';

  if (!d || d.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9"><div class="no-data"><div class="nd-icon">🏆</div><p>No matching IPOs found.</p></div></td></tr>';
    return;
  }

  d.forEach((row, idx) => {
    const ticker = row.Ticker || 'N/A';
    const isB = ticker.endsWith('.BO');
    const ex = isB ? 'BSE' : 'NSE';
    const sy = ticker.replace('.NS','').replace('.BO','');
    const tv = ticker !== 'N/A' ? 'https://in.tradingview.com/chart/?symbol='+ex+':'+sy : '#';
    const ci = ticker !== 'N/A' ? 'https://chartink.com/stocks/'+sy.toLowerCase()+'.html' : '#';

    const lg = row.Listing_Gain_Pct;
    const og = row.Overall_Gain_Pct;
    const lgStr = lg != null ? (lg > 0 ? '+' : '') + lg + '%' : '—';
    const ogStr = og != null ? (og > 0 ? '+' : '') + og + '%' : '—';
    const lgCls = lg == null ? '' : lg > 0 ? 'gain-positive' : lg < 0 ? 'gain-negative' : 'gain-flat';
    const ogCls = og == null ? '' : og >= 50 ? 'gain-positive' : og >= 0 ? 'gain-flat' : 'gain-negative';

    const status = row.Performance_Status || '—';
    let statusBg = 'rgba(100,116,139,.2)';
    let statusColor = '#94a3b8';
    if (status.includes('Active') || status.includes('Multibagger') || status.includes('Strong')) { statusBg='rgba(16,185,129,.15)'; statusColor='#34d399'; }
    else if (status.includes('Gainer'))  { statusBg='rgba(245,158,11,.1)'; statusColor='#fbbf24'; }
    else if (status.includes('Loss'))    { statusBg='rgba(239,68,68,.1)'; statusColor='#f87171'; }

    const rankBadge = idx < 3 ? ['🥇','🥈','🥉'][idx] : '';

    const tr = document.createElement('tr');
    if (ticker !== 'N/A') tr.style.cursor = 'pointer';
    tr.innerHTML =
      '<td>' + rankBadge + ' <span style="font-weight:700;color:#60a5fa">' + (row.Company_Name||'—') + '</span><br><small style="color:var(--text-muted)">' + ticker + ' &bull; ' + (row.Exchange||ex) + '</small></td>' +
      '<td style="font-size:11px">' + (row.Listed_Date||'—') + '</td>' +
      '<td style="font-weight:700">' + (row.IPO_Issue_Price ? '₹' + numFmt(row.IPO_Issue_Price) : '—') + '</td>' +
      '<td>' + (row.Listing_Day_Price ? '₹' + numFmt(row.Listing_Day_Price) : '—') + '</td>' +
      '<td style="font-weight:700">' + (row.Current_Price ? '₹' + numFmt(row.Current_Price) : '—') + '</td>' +
      '<td class="' + lgCls + '">' + lgStr + '</td>' +
      '<td class="' + ogCls + '" style="font-size:14px;font-weight:800">' + ogStr + '</td>' +
      '<td><span class="perf-badge" style="background:' + statusBg + ';color:' + statusColor + '">' + status + '</span></td>' +
      '<td><div class="chart-links-group" onclick="event.stopPropagation()">' + (ticker!=='N/A'?'<button class="btn-chart-modal" data-ticker="' + ticker + '" data-name="' + (row.Company_Name||'') + '" onclick="triggerIpoModal(this, event)">📈</button><a href="'+tv+'" target="_blank" class="tv-btn">TV ↗</a>':'—') + '</div></td>';

    if (ticker !== 'N/A') {
      tr.addEventListener('click', (e) => {
        if (e.target.tagName === 'A' || e.target.tagName === 'BUTTON' || e.target.closest('a') || e.target.closest('button')) return;
        openChartModal(ticker, row.Company_Name || ticker, '75', '80', '1.8x', '0', '0', '0', '0', '0');
      });
    }

    tbody.appendChild(tr);
  });
}

// ── AI Panel ──────────────────────────────────────────────────────
const TIER_COLORS = {1:'#ef4444',2:'#f97316',3:'#f59e0b',4:'#10b981',5:'#64748b'};
const TIER_BG    = {1:'rgba(239,68,68,.15)',2:'rgba(249,115,22,.15)',3:'rgba(245,158,11,.15)',4:'rgba(16,185,129,.15)',5:'rgba(100,116,139,.15)'};

function renderAIPanel() {
  if (!aiReport || !aiReport.market_summary) {
    document.getElementById('aiSentiment').innerText = 'No AI data yet';
    document.getElementById('aiSummaryDesc').innerText = 'Run a scan to generate AI analysis.';
    document.getElementById('aiCardsGrid').innerHTML = '<div class="no-data"><div class="nd-icon">&#129302;</div><p>Click RUN SCAN NOW to generate AI reports for all stocks.</p></div>';
    return;
  }
  const ms = aiReport.market_summary;
  document.getElementById('aiSentiment').innerText = ms.sentiment || 'NEUTRAL';
  document.getElementById('aiSummaryDesc').innerText = ms.sentiment_desc || '';
  const stats = [
    {label:'Signals Found', val: ms.total_signals || 0},
    {label:'Premium (Tier 1)', val: ms.tier1_count || 0},
    {label:'Strong (Tier 2)', val: ms.tier2_count || 0},
    {label:'Avg Score', val: (ms.avg_score || 0) + '/100'},
    {label:'Avg RSI(9)', val: ms.avg_rsi || 0},
    {label:'Scan Time', val: ms.scan_time || '-'},
  ];
  document.getElementById('aiStatsRow').innerHTML = stats.map(s =>
    '<div class="ai-stat"><span>' + s.val + '</span>' + s.label + '</div>'
  ).join('');
  aiFilteredReports = [...(aiReport.reports || [])];
  renderAICards();
}

function filterAiTier(tier, btn) {
  aiTierFilter = tier;
  document.querySelectorAll('.ai-tier-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  if (!aiReport || !aiReport.reports) return;
  aiFilteredReports = tier === 0 ? [...aiReport.reports] : aiReport.reports.filter(r => r.tier === tier);
  renderAICards();
}

function renderAICards() {
  const grid = document.getElementById('aiCardsGrid');
  const countEl = document.getElementById('aiSignalCount');
  grid.innerHTML = '';
  if (!aiFilteredReports || aiFilteredReports.length === 0) {
    grid.innerHTML = '<div class="no-data" style="grid-column:1/-1"><div class="nd-icon">&#129302;</div><p>No signals in this tier. Try a different filter.</p></div>';
    if (countEl) countEl.innerText = '';
    return;
  }
  if (countEl) countEl.innerText = aiFilteredReports.length + ' signals';

  aiFilteredReports.forEach(r => {
    const card = document.createElement('div');
    card.className = 'ai-stock-card';
    const color = TIER_COLORS[r.tier] || '#64748b';
    const bg = TIER_BG[r.tier] || 'rgba(100,116,139,.1)';
    card.style.borderTopColor = color;
    card.style.borderTopWidth = '3px';

    const warnings = (r.risk_warnings || []).filter(w => w.toLowerCase().includes('warning') || w.toLowerCase().includes('extreme') || w.toLowerCase().includes('decline') || w.toLowerCase().includes('low'));
    const warnHtml = warnings.length > 0
      ? '<div class="ai-warn">&#9888; ' + warnings.join(' | ') + '</div>'
      : '';

    const isB = (r.ticker||'').endsWith('.BO');
    const ex = isB ? 'BSE' : 'NSE';
    const sy = (r.ticker||'').replace('.NS','').replace('.BO','');
    const tv = 'https://in.tradingview.com/chart/?symbol=' + ex + ':' + sy;

    card.innerHTML =
      '<div class="ai-card-header">' +
        '<div class="ai-card-left">' +
          '<div class="ai-company"><a href="' + tv + '" target="_blank" style="color:#60a5fa;text-decoration:none">' + (r.company||r.ticker) + '</a></div>' +
          '<div class="ai-ticker">' + (r.ticker||'') + ' &nbsp;|&nbsp; ' + ex + '</div>' +
        '</div>' +
        '<div class="ai-tier-badge" style="background:' + bg + ';color:' + color + ';border:1px solid ' + color + '33">' +
          (r.tier_emoji||'') + ' ' + (r.tier_label||'') +
        '</div>' +
      '</div>' +
      '<div class="ai-card-body">' +
        '<div class="ai-report-pre">' + (r.report_text||'No report available').replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</div>' +
        warnHtml +
      '</div>' +
      '<div class="ai-card-footer">' +
        (r.close ? '<span class="ai-trade-pill entry">Entry &#8377;' + numFmt(r.close) + '</span>' : '') +
        (r.stop_loss ? '<span class="ai-trade-pill sl">SL &#8377;' + numFmt(r.stop_loss) + '</span>' : '') +
        (r.target_1 ? '<span class="ai-trade-pill t1">T1 &#8377;' + numFmt(r.target_1) + '</span>' : '') +
        '<button class="btn-copy-report" onclick="copyReport(this)" data-report="' + encodeURIComponent(r.report_text||'') + '">Copy Report</button>' +
      '</div>';
    grid.appendChild(card);
  });
}

function copyReport(btn, ticker) {
  const encoded = btn.getAttribute('data-report');
  const text = decodeURIComponent(encoded);
  navigator.clipboard.writeText(text).then(() => {
    btn.innerText = 'Copied!';
    setTimeout(() => { btn.innerText = 'Copy Report'; }, 2000);
  }).catch(() => {
    showToast('Could not copy. Select text manually.', 'ℹ️');
  });
}

// ── Export CSV ────────────────────────────────────────────────────
function exportActiveCSV() {

  let d = currentFilteredData;
  if (currentTab === 'IPO_TRACKER') d = ipoFilteredData;
  if (!d || d.length === 0) return showToast('No data to export.', '⚠️');
  const k = Object.keys(d[0]);
  let c = 'data:text/csv;charset=utf-8,' + k.join(',') + '\\n';
  d.forEach(r => { c += k.map(x => '"' + (r[x]||'') + '"').join(',') + '\\n'; });
  const a = document.createElement('a');
  a.href = encodeURI(c);
  a.download = 'stoks_export_' + currentTab + '.csv';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  showToast('CSV exported!', '📥');
}

// ── Utilities ─────────────────────────────────────────────────────
function numFmt(v) {
  if (v == null || v === '' || isNaN(v)) return '—';
  return parseFloat(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ── Init ──────────────────────────────────────────────────────────
filterData();
</script>
</body>
</html>"""

    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("SUCCESS: STOKS V5.0 Dashboard generated -> dashboard.html & index.html")

    try:
        from build_mobile_dashboard import build_mobile_dashboard
        build_mobile_dashboard()
    except Exception as e:
        print("Mobile dashboard build warning:", e)

if __name__ == "__main__":
    build_dashboard()
