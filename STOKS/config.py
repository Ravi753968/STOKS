import os

# Production Configuration Settings V4.1
BASE_DIR = r"d:\STOKS"
CACHE_DIR = os.path.join(BASE_DIR, "cache")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
ALERTS_DIR = os.path.join(BASE_DIR, "alerts")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(ALERTS_DIR, exist_ok=True)

# Quantitative Parameters
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2.0
RSI_PERIOD = 9
RSI_THRESHOLD = 60.0
VOLUME_SURGE_MIN = 1.5
ATR_PERIOD = 14

# Stock Universes
EXCEL_IPO_FILE = os.path.join(BASE_DIR, "BSE MAIN BOARD IPO.xlsx")  # emergency fallback only
IPO_START_DATE = "2022-01-01"   # BSE+NSE Main Board IPOs from 2022 onwards
IPO_END_DATE   = "2026-12-31"   # Inclusive upper bound
IPO_CACHE_TTL_HOURS = 24        # Refresh live IPO list every 24 hours

# Server Config
PORT = 5005
