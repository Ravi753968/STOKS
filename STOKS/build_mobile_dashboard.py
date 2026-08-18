"""
STOKS V5.0 — Mobile Workstation Generator (mobile.html)
Generates a dedicated, native-app-like mobile web UI for smartphone screens.
"""
import pandas as pd
import json
import os
import re

def compact_records(df):
    if df is None or df.empty:
        return '[]'
    records = df.to_dict(orient="records")
    return json.dumps(records, separators=(",", ":"), ensure_ascii=False)

def load_json_file(path, default='[]'):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.dumps(json.load(f), separators=(",", ":"), ensure_ascii=False)
        except Exception:
            pass
    return default

def build_mobile_dashboard():
    print("Building STOKS V5.0 Mobile Workstation (mobile.html)...")

    # Load data files
    df_5y = pd.read_csv("recent_ipo_breakouts_5y.csv") if os.path.exists("recent_ipo_breakouts_5y.csv") else pd.DataFrame()
    df_daily = pd.read_csv("master_scan_results.csv") if os.path.exists("master_scan_results.csv") else pd.DataFrame()
    df_ipo = pd.read_csv("ipo_performance_data.csv") if os.path.exists("ipo_performance_data.csv") else pd.DataFrame()

    records_5y    = compact_records(df_5y)
    records_daily = compact_records(df_daily)
    records_ipo   = compact_records(df_ipo)
    records_sector= load_json_file("sector_heatmap_data.json")
    ai_report     = load_json_file("ai_analysis_report.json", '{}')
    fii_dii_json  = load_json_file("fii_dii_data.json", '{}')

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>STOKS Mobile — Institutional Breakout App</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
<style>
:root{--bg:#0b0f19;--card-bg:#151c2c;--border:rgba(255,255,255,.08);--accent-blue:#3b82f6;--accent-green:#10b981;--accent-amber:#f59e0b;--accent-red:#ef4444;--text:#f8fafc;--muted:#94a3b8}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);padding-bottom:70px;user-select:none}
/* Header */
header{background:linear-gradient(180deg,#151c2c,#0b0f19);padding:14px 16px;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100;display:flex;align-items:center;justify-content:space-between}
.h-title{font-size:16px;font-weight:900;background:linear-gradient(90deg,#60a5fa,#3b82f6);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.h-sub{font-size:10px;color:var(--muted)}
.btn-scan-m{background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff;border:none;padding:7px 12px;border-radius:20px;font-size:11px;font-weight:800;cursor:pointer}
/* Bottom Nav */
.bottom-nav{position:fixed;bottom:0;left:0;right:0;height:60px;background:#131926;border-top:1px solid var(--border);display:flex;justify-content:space-around;align-items:center;z-index:1000}
.nav-item{display:flex;flex-direction:column;align-items:center;color:var(--muted);font-size:10px;font-weight:600;text-decoration:none;cursor:pointer;padding:6px 0;width:20%}
.nav-item.active{color:#60a5fa}
.nav-icon{font-size:18px;margin-bottom:2px}
/* Content */
.m-container{padding:12px 14px}
.m-search-bar{margin-bottom:12px;display:flex;gap:8px}
.m-input{flex:1;background:var(--card-bg);border:1px solid var(--border);color:#fff;padding:10px 14px;border-radius:10px;font-size:13px;outline:none}
/* Stock Card */
.stock-card-m{background:var(--card-bg);border:1px solid var(--border);border-radius:14px;padding:14px;margin-bottom:12px;position:relative}
.sc-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px}
.sc-name{font-size:14px;font-weight:800;color:#60a5fa}
.sc-ticker{font-size:11px;color:var(--muted)}
.sc-price{font-size:16px;font-weight:900;color:#fff;text-align:right}
.sc-badges{display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap}
.sc-pill{font-size:10px;font-weight:800;padding:3px 8px;border-radius:6px;background:rgba(255,255,255,.06)}
.sc-pill.green{color:#34d399;background:rgba(16,185,129,.12)}
.sc-pill.amber{color:#fbbf24;background:rgba(245,158,11,.12)}
.sc-levels{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;background:rgba(0,0,0,.2);padding:8px;border-radius:8px;text-align:center;font-size:11px;margin-bottom:10px}
.sc-levels div span{display:block;font-size:9px;color:var(--muted);font-weight:700}
.sc-actions{display:flex;gap:8px}
.btn-m-action{flex:1;background:rgba(59,130,246,.15);border:1px solid rgba(59,130,246,.3);color:#60a5fa;padding:8px;border-radius:8px;font-size:12px;font-weight:800;cursor:pointer;text-align:center;text-decoration:none}
/* Macro Card */
.macro-card-m{background:linear-gradient(135deg,rgba(59,130,246,.12),rgba(16,185,129,.08));border:1px solid rgba(59,130,246,.3);border-radius:14px;padding:14px;margin-bottom:14px}
.mc-title{font-size:11px;color:#93c5fd;font-weight:800;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.mc-val{font-size:18px;font-weight:900;color:#fff}
/* Modal */
.modal-m{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.85);z-index:2000;display:none;flex-direction:column;padding:14px;overflow-y:auto}
.modal-m.open{display:flex}
.modal-m-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.btn-close-m{background:var(--card-bg);border:1px solid var(--border);color:#fff;width:32px;height:32px;border-radius:50%;font-size:16px;cursor:pointer}
</style>
</head>
<body>

<header>
  <div>
    <div class="h-title">⚡ STOKS MOBILE</div>
    <div class="h-sub">Breakouts · AI · FII Flows</div>
  </div>
  <button class="btn-scan-m" onclick="triggerScanM()">🔄 Scan</button>
</header>

<!-- Main Container -->
<div class="m-container">

  <!-- FII/DII Summary Card -->
  <div class="macro-card-m" id="fiiCardM">
    <div class="mc-title">🏦 FII / DII Institutional Stance</div>
    <div class="mc-val" id="fiiStanceM">Loading...</div>
    <div style="font-size:11px;color:var(--muted);margin-top:4px" id="fiiNetM"></div>
  </div>

  <!-- Search Bar -->
  <div class="m-search-bar">
    <input type="text" id="mSearch" class="m-input" placeholder="Search stock or symbol..." onkeyup="renderMobileCards()">
  </div>

  <!-- Stock Cards Grid -->
  <div id="mCardsGrid"></div>

</div>

<!-- Bottom Navigation Bar -->
<nav class="bottom-nav">
  <div class="nav-item active" onclick="switchTabM('DAILY',this)">
    <div class="nav-icon">🎯</div>Breakouts
  </div>
  <div class="nav-item" onclick="switchTabM('AI',this)">
    <div class="nav-icon">🤖</div>AI Intel
  </div>
  <div class="nav-item" onclick="switchTabM('FII',this)">
    <div class="nav-icon">🏦</div>FII Flows
  </div>
  <div class="nav-item" onclick="switchTabM('IPO',this)">
    <div class="nav-icon">🏆</div>IPOs
  </div>
  <div class="nav-item" onclick="switchTabM('SECTOR',this)">
    <div class="nav-icon">🔥</div>Sectors
  </div>
</nav>

<!-- Mobile Chart Modal -->
<div class="modal-m" id="mChartModal">
  <div class="modal-m-header">
    <div>
      <div id="mModalTitle" style="font-size:16px;font-weight:900;color:#60a5fa"></div>
      <div id="mModalTicker" style="font-size:11px;color:var(--muted)"></div>
    </div>
    <button class="btn-close-m" onclick="closeModalM()">✕</button>
  </div>
  <div id="mChartBox" style="height:260px;width:100%;margin-bottom:10px"></div>
  <div id="mRsiBox" style="height:100px;width:100%"></div>
</div>

<script>
const data5y     = """ + records_5y + """;
const dataDaily  = """ + records_daily + """;
const dataIpo    = """ + records_ipo + """;
const dataSector = """ + records_sector + """;
const aiReport   = """ + ai_report + """;
const fiiDiiData = """ + fii_dii_json + """;

let currentTabM = 'DAILY';

function initM() {
  if (fiiDiiData && fiiDiiData.institutional_bias) {
    document.getElementById('fiiStanceM').innerText = fiiDiiData.institutional_bias;
    document.getElementById('fiiNetM').innerText = 'FII: Rs ' + (fiiDiiData.fii_cash_net||0) + ' Cr  |  DII: Rs ' + (fiiDiiData.dii_cash_net||0) + ' Cr';
  }
  renderMobileCards();
}

function switchTabM(t, btn) {
  currentTabM = t;
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  renderMobileCards();
}

function renderMobileCards() {
  const grid = document.getElementById('mCardsGrid');
  const q = document.getElementById('mSearch').value.toUpperCase();
  grid.innerHTML = '';

  let list = [];
  if (currentTabM === 'DAILY') list = dataDaily;
  else if (currentTabM === 'IPO') list = dataIpo;
  else if (currentTabM === 'AI') list = (aiReport.reports || []);

  if (q) {
    list = list.filter(x => (x.Company_Name||x.company||'').toUpperCase().includes(q) || (x.Ticker||x.ticker||'').toUpperCase().includes(q));
  }

  if (!list || list.length === 0) {
    grid.innerHTML = '<div style="text-align:center;padding:40px;color:var(--muted)">No signals found.</div>';
    return;
  }

  list.forEach(s => {
    const card = document.createElement('div');
    card.className = 'stock-card-m';
    const ticker = s.Ticker || s.ticker || '';
    const name = s.Company_Name || s.company || ticker;
    const price = s.Close || s.close || s.Current_Price || 0;
    const rsi = s.RSI_9 || s.rsi || 0;
    const vol = s.Volume_Spike || s.vol || '1.5x';
    const sl = s.Stop_Loss || s.stop_loss || 0;
    const t1 = s.Target_1 || s.target_1 || 0;

    const isB = ticker.endsWith('.BO');
    const ex = isB ? 'BSE' : 'NSE';
    const sy = ticker.replace('.NS','').replace('.BO','');
    const tv = 'https://in.tradingview.com/chart/?symbol=' + ex + ':' + sy;

    card.innerHTML =
      '<div class="sc-header">' +
        '<div><div class="sc-name">' + name + '</div><div class="sc-ticker">' + ticker + ' • ' + ex + '</div></div>' +
        '<div class="sc-price">₹' + numFmt(price) + '</div>' +
      '</div>' +
      '<div class="sc-badges">' +
        (rsi ? '<span class="sc-pill green">RSI ' + rsi + '</span>' : '') +
        (vol ? '<span class="sc-pill amber">Vol ' + vol + '</span>' : '') +
      '</div>' +
      '<div class="sc-levels">' +
        '<div><span>ENTRY</span>₹' + numFmt(price) + '</div>' +
        '<div><span>STOP LOSS</span>₹' + numFmt(sl) + '</div>' +
        '<div><span>TARGET 1</span>₹' + numFmt(t1) + '</div>' +
      '</div>' +
      '<div class="sc-actions">' +
        '<button class="btn-m-action" data-ticker="' + ticker + '" data-name="' + name.replace(/"/g, '&quot;') + '" onclick="openModalM(this)">📈 Price Chart</button>' +
        '<a href="' + tv + '" target="_blank" class="btn-m-action" style="background:rgba(255,255,255,.05);color:var(--text);border-color:var(--border)">TradingView ↗</a>' +
      '</div>';

    grid.appendChild(card);
  });
}

function openModalM(btn) {
  const ticker = btn.getAttribute('data-ticker');
  const name = btn.getAttribute('data-name');
  document.getElementById('mChartModal').classList.add('open');
  document.getElementById('mModalTitle').innerText = name;
  document.getElementById('mModalTicker').innerText = ticker;
  // Load chart
  fetch('/api/chart?ticker=' + encodeURIComponent(ticker) + '&period=60d')
    .then(r => r.json())
    .then(d => renderChartM(d));
}

function closeModalM() {
  document.getElementById('mChartModal').classList.remove('open');
}

function renderChartM(d) {
  if (!d || !d.candles) return;
  const container = document.getElementById('mChartBox');
  container.innerHTML = '';
  const chart = LightweightCharts.createChart(container, {
    layout: { backgroundColor: '#151c2c', textColor: '#94a3b8' },
    grid: { vertLines: { color: 'rgba(255,255,255,.05)' }, horzLines: { color: 'rgba(255,255,255,.05)' } },
    timeScale: { borderColor: 'rgba(255,255,255,.1)' },
  });
  const series = chart.addCandlestickSeries({ upColor: '#10b981', downColor: '#ef4444' });
  series.setData(d.candles);
}

function numFmt(v) { return v ? parseFloat(v).toFixed(2) : '—'; }
function triggerScanM() { alert('Scan triggered in background!'); fetch('/api/scan',{method:'POST'}); }

initM();
</script>
</body>
</html>"""

    with open("mobile.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("SUCCESS: STOKS V5.0 Mobile Workstation generated -> mobile.html")

if __name__ == "__main__":
    build_mobile_dashboard()
