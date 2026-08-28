"""
config.py — Central configuration for Crude MCX Signal Dashboard
All tunable parameters in one place.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── Upstox Credentials ────────────────────────────────────────────────────────
UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY", "")
UPSTOX_API_SECRET = os.getenv("UPSTOX_API_SECRET", "")
UPSTOX_REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI", "http://127.0.0.1:8000/callback")
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "")
TOKEN_EXPIRY_DATE = os.getenv("TOKEN_EXPIRY_DATE", "")

# True if we have a direct Analytics token (1-year validity)
HAS_ANALYTICS_TOKEN = bool(UPSTOX_ACCESS_TOKEN and len(UPSTOX_ACCESS_TOKEN) > 20)

# ─── Instrument Settings ────────────────────────────────────────────────────────
MCX_SEGMENT = "MCX_FO"
CRUDE_SYMBOL_KEYWORD = "CRUDEOIL"
INSTRUMENT_TYPE = "FUT"

# ─── Signal Engine Settings ────────────────────────────────────────────────────
PRIMARY_TIMEFRAME = "30minute"
ENTRY_TIMEFRAME = "1minute"

EMA_FAST = 9
EMA_MID = 21
EMA_SLOW = 50

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
RSI_NEUTRAL_LOW = 40
RSI_NEUTRAL_HIGH = 60

HIGH_CONFIDENCE_THRESHOLD = 5
MED_CONFIDENCE_THRESHOLD = 3

PIVOT_LEVELS = ["S3", "S2", "S1", "PP", "R1", "R2", "R3"]
PIVOT_PROXIMITY_RS = 8.0

# ─── Risk Management Defaults (1-Lot ATM Options) ──────────────────────────────
DEFAULT_LOTS = 1
DEFAULT_SL_POINTS = 22.0
DEFAULT_TARGET1_POINTS = 48.0
DEFAULT_TARGET2_POINTS = 80.0
DEFAULT_TARGET3_POINTS = 120.0
RISK_REWARD_MIN = 2.0

# ─── Session Settings ─────────────────────────────────────────────────────────
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MIN = 0
MARKET_CLOSE_HOUR = 23
MARKET_CLOSE_MIN = 30
IST_TIMEZONE = "Asia/Kolkata"

# ─── UI & Chart Settings ───────────────────────────────────────────────────────
AUTO_REFRESH_SECONDS = 5
CANDLES_TO_SHOW = 48
CHART_HEIGHT = 480
COLOR_BULLISH = "#00D084"
COLOR_BEARISH = "#FF4B4B"
COLOR_NEUTRAL = "#FFAA00"
COLOR_BACKGROUND = "#0E1117"
COLOR_CARD = "#1E222D"
COLOR_ACCENT = "#2962FF"

# ─── News Monitor Settings ─────────────────────────────────────────────────────
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "")
NEWS_REFRESH_SECONDS = 300
MAX_NEWS_ITEMS = 10

NEWS_RSS_FEEDS = [
    {"name": "OilPrice.com", "url": "https://oilprice.com/rss/main"},
    {"name": "Reuters Energy", "url": "https://feeds.reuters.com/reuters/businessNews"},
]

NEWS_BULLISH_KEYWORDS = [
    "opec cut", "supply cut", "tensions", "escalat", "drawdown",
    "inventory drop", "crude rally", "oil surges", "strike", "disruption",
    "embargo", "sanctions", "pipeline leak", "middle east war", "attacks"
]

NEWS_BEARISH_KEYWORDS = [
    "opec hike", "supply increase", "inventory build", "stockpile rise",
    "crude falls", "oil drops", "recession", "demand slump", "ceasefire",
    "iea downgrade", "output boost", "economic slowdown", "fed hike"
]

# ─── Alert & Notification Settings ─────────────────────────────────────────────
ENABLE_SOUND_ALERTS = True
ALERT_COOLDOWN_SECONDS = 300
ENABLE_TELEGRAM = False
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ─── Upstox API Endpoints ─────────────────────────────────────────────────────
BASE_URL = "https://api.upstox.com/v2"
HISTORY_URL = f"{BASE_URL}/historical-candle"
INTRADAY_URL = f"{BASE_URL}/historical-candle/intraday"
QUOTE_URL = f"{BASE_URL}/market-quote/quotes"
TOKEN_URL = f"{BASE_URL}/login/authorization/token"
FEED_URL = "wss://api.upstox.com/v2/feed/market-data-feed"
