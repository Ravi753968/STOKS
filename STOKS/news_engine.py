"""
STOKS V4.2 — Live Stock News & Catalyst Engine
Scrapes live Google News RSS feeds for breakout stocks in parallel.
Classifies news headlines into catalysts: EARNINGS, ORDER_WIN, BLOCK_DEAL, EXPANSION, GENERAL.
Generates stock_news_data.json for dashboard & AI integration.
"""
import requests
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from prod_logger import log_info, log_error

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

# Catalyst Keyword Rules
CATALYST_PATTERNS = [
    (r"\b(q1|q2|q3|q4|quarter|profit|revenue|pat|ebitda|result|earnings|growth|jump|surge|soars|up \d+%)\b", "EARNINGS", "🟢 Earnings Surge", "#10b981"),
    (r"\b(order|contract|deal|bag|secures|wins|awarded|mandate|project)\b", "ORDER_WIN", "📜 Order Win", "#3b82f6"),
    (r"\b(block deal|stake|fii|promoter|acquire|buyout|fundraise|investment|shares)\b", "BLOCK_DEAL", "🤝 Block Deal / Stake", "#f59e0b"),
    (r"\b(expansion|plant|factory|fda|approval|capacity|new facility|launch|commission|patent)\b", "EXPANSION", "🏭 Expansion / Approval", "#8b5cf6"),
]


def _classify_catalyst(title):
    """Classify headline into a catalyst category."""
    title_lower = title.lower()
    for pattern, cat_key, cat_label, color in CATALYST_PATTERNS:
        if re.search(pattern, title_lower):
            return cat_key, cat_label, color
    return "GENERAL", "📰 Market News", "#64748b"


def _fetch_stock_news(item):
    """Fetch latest Google News RSS item for a single ticker."""
    ticker, company_name = item
    raw_symbol = ticker.replace(".NS", "").replace(".BO", "")
    clean_company = re.sub(r'\(.*?\)', '', company_name).replace("LIMITED", "").replace("LTD", "").strip()
    query_name = clean_company.split()[0] if len(clean_company.split()) > 0 else raw_symbol

    url = f"https://news.google.com/rss/search?q={requests.utils.quote(query_name + ' stock india')}&hl=en-IN&gl=IN&ceid=IN:en"
    articles = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            root = ET.fromstring(resp.text)
            for item_node in root.findall("./channel/item")[:3]:
                title = item_node.findtext("title", "").strip()
                link = item_node.findtext("link", "").strip()
                pub_date = item_node.findtext("pubDate", "").strip()

                # Clean title (remove source suffix like "- Economic Times")
                clean_title = re.sub(r'\s*-\s*[^-]+$', '', title)

                cat_key, cat_label, cat_color = _classify_catalyst(clean_title)

                articles.append({
                    "title": clean_title,
                    "link": link,
                    "pub_date": pub_date,
                    "catalyst_key": cat_key,
                    "catalyst_label": cat_label,
                    "catalyst_color": cat_color,
                })
    except Exception:
        pass

    top_catalyst = articles[0]["catalyst_label"] if articles else "📰 Market News"
    top_headline = articles[0]["title"] if articles else f"Recent volume activity and price momentum observed for {clean_company}."

    return ticker, {
        "ticker": ticker,
        "company": company_name,
        "top_headline": top_headline,
        "top_catalyst": top_catalyst,
        "articles": articles,
    }


def fetch_live_market_news():
    """Fetch news for all active breakout tickers concurrently."""
    log_info("Fetching Live Stock News & Catalysts...")

    # Load breakout tickers from CSVs
    all_dfs = []
    csv_files = ["recent_ipo_breakouts_5y.csv", "master_scan_results.csv", "monthly_ath_breakouts.csv"]
    for f in csv_files:
        if os.path.exists(f):
            try:
                all_dfs.append(pd.read_csv(f))
            except Exception:
                pass

    if not all_dfs:
        log_error("No CSV files found for news fetching.")
        return {}

    combined = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=["Ticker"]).reset_index(drop=True)
    items = [(row.get("Ticker", ""), str(row.get("Company_Name", ""))) for _, row in combined.iterrows() if row.get("Ticker")]

    log_info(f"Fetching live news for {len(items)} breakout stocks in parallel...")

    news_map = {}
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(_fetch_stock_news, item): item for item in items}
        for future in as_completed(futures):
            try:
                t, news_data = future.result()
                news_map[t] = news_data
            except Exception:
                pass

    output_path = "stock_news_data.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(news_map, f, indent=2, ensure_ascii=False)
        log_info(f"SUCCESS: Live News data saved -> {output_path} ({len(news_map)} stocks mapped)")
    except Exception as e:
        log_error(f"Failed to save stock_news_data.json: {e}")

    return news_map


if __name__ == "__main__":
    import pandas as pd
    fetch_live_market_news()
