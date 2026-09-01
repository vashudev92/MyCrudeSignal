"""
dashboard.py — Institutional MCX Crude Oil Live Signal & Analytics Terminal
Classic Minimal Light Theme: Compact, Clean, 3-Button Quick Switcher in Live Execution Tab,
Real-Time Market Tracking, Reactive Strategy Lab, and Single-Trade Capital Lock.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List
import pytz

# ─── Page Configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Crude MCX Terminal",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from config import (
    UPSTOX_API_KEY, UPSTOX_API_SECRET,
    IST_TIMEZONE, MARKET_OPEN_HOUR, MARKET_OPEN_MIN, MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN,
    HAS_ANALYTICS_TOKEN,
)
from upstox_client import get_client, TokenManager, UpstoxClient
from instrument_finder import get_active_crude_instrument_key
from indicators import calculate_pivot_points, compute_indicators, PivotLevels
from signal_engine import SignalEngine, SignalType, SignalConfidence
from news_monitor import get_news_monitor
from alert_manager import get_alert_manager, send_telegram_test_message, get_telegram_creds, send_telegram_message
from backtester import CrudeBacktester, BacktestReport, calculate_mcx_option_charges
from background_scanner import start_background_scanner
from commodity_registry import COMMODITY_REGISTRY, get_commodity_spec, calculate_commodity_option_charges
from strategy_presets import (
    get_active_strategy_config,
    save_active_strategy_config,
    get_commodity_presets,
    CommodityStrategyConfig,
    get_saved_strategies_for_asset,
    save_custom_strategy,
    rename_custom_strategy,
    delete_custom_strategy,
    deploy_strategy_to_asset
)
from stock_momentum_scanner import (
    NSE_STOCK_UNIVERSE,
    run_stock_momentum_scanner,
    backtest_stock_momentum_scanner,
    ScannerSignal,
    ScannerBacktestReport
)
import os
import textwrap

IST = pytz.timezone(IST_TIMEZONE)

def save_telegram_env_credentials(bot_token: str, chat_id: str):
    """Saves Telegram Bot Token and Chat ID to local .env and environment variables."""
    os.environ["TELEGRAM_BOT_TOKEN"] = bot_token.strip()
    os.environ["TELEGRAM_CHAT_ID"] = chat_id.strip()
    os.environ["ENABLE_TELEGRAM"] = "True"

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    found_token, found_chat, found_enable = False, False, False
    new_lines = []
    for line in lines:
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            new_lines.append(f'TELEGRAM_BOT_TOKEN="{bot_token.strip()}"\n')
            found_token = True
        elif line.startswith("TELEGRAM_CHAT_ID="):
            new_lines.append(f'TELEGRAM_CHAT_ID="{chat_id.strip()}"\n')
            found_chat = True
        elif line.startswith("ENABLE_TELEGRAM="):
            new_lines.append('ENABLE_TELEGRAM=True\n')
            found_enable = True
        else:
            new_lines.append(line)

    if not found_token:
        new_lines.append(f'TELEGRAM_BOT_TOKEN="{bot_token.strip()}"\n')
    if not found_chat:
        new_lines.append(f'TELEGRAM_CHAT_ID="{chat_id.strip()}"\n')
    if not found_enable:
        new_lines.append('ENABLE_TELEGRAM=True\n')

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

# ─── 3 Verified Profitable Strategy Setups (From Backtest Audits) ──────────────
SETUPS = {
    "SETUP1": {
        "id": "SETUP1",
        "title": "🎯 Setup 1: RSI + MACD Confluence",
        "badge": "+47.1% Net ROI (1:2.2 RR)",
        "model": "🎯 RSI + MACD Confluence",
        "sl_pts": 25.0,
        "t1_rr": 2.2,
        "t2_rr": 3.5,
        "regime": "🎯 Balanced Quality (ADX >= 18)",
        "trailing": "❌ Pure Fixed SL",
        "session": "🔥 US Prime Session (16:30 - 22:30 IST)",
        "max_trades": 3,
        "desc": "3-Month Audit: +₹47,064 Net P&L, 44.3% Win Rate, 1.79 Profit Factor, ₹16k Max DD."
    },
    "SETUP2": {
        "id": "SETUP2",
        "title": "📰 Setup 2: Energy News Breakout",
        "badge": "+47.7% Net ROI (1:2.5 RR)",
        "model": "📰 High-Impact Energy News Breakout",
        "sl_pts": 25.0,
        "t1_rr": 2.5,
        "t2_rr": 3.5,
        "regime": "🎯 Balanced Quality (ADX >= 18)",
        "trailing": "❌ Pure Fixed SL",
        "session": "🔥 US Prime Session (16:30 - 22:30 IST)",
        "max_trades": 10,
        "desc": "3-Month Audit: +₹47,713 Net P&L, 37.5% Win Rate, 1.42 Profit Factor, ₹23k Max DD."
    },
    "SETUP3": {
        "id": "SETUP3",
        "title": "📊 Setup 3: Standard Pivot Breakout",
        "badge": "+33.6% Net ROI (1:3.0 RR)",
        "model": "📊 Standard Pivot Breakout",
        "sl_pts": 25.0,
        "t1_rr": 3.0,
        "t2_rr": 3.5,
        "regime": "🎯 Balanced Quality (ADX >= 18)",
        "trailing": "❌ Pure Fixed SL",
        "session": "🔥 US Prime Session (16:30 - 22:30 IST)",
        "max_trades": 10,
        "desc": "3-Month Audit: +₹33,597 Net P&L, 35.7% Win Rate, 1.26 Profit Factor, ₹21k Max DD."
    }
}


# ─── Classic Minimal Light Stylesheet ──────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700;800&display=swap');

    /* Global App Container */
    .stApp {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 0.8rem !important;
        padding-left: 1.0rem !important;
        padding-right: 1.0rem !important;
        max-width: 99% !important;
    }

    /* Minimalist Top Navbar */
    .mini-nav {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 6px 14px;
        margin-bottom: 8px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }
    .mini-nav-title {
        font-size: 0.95rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.01em;
    }
    .mini-nav-sub {
        font-size: 0.65rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .mini-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 4px;
        background: #F1F5F9;
        color: #0369A1;
        border: 1px solid #BAE6FD;
    }

    /* Compact Segmented Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: #E2E8F0 !important;
        border-radius: 6px !important;
        padding: 3px !important;
        gap: 4px !important;
        border: 1px solid #CBD5E1 !important;
        display: inline-flex !important;
        margin-bottom: 8px !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 4px !important;
        color: #475569 !important;
        font-weight: 700 !important;
        font-size: 0.78rem !important;
        padding: 4px 16px !important;
        border: none !important;
        background: transparent !important;
    }
    .stTabs [aria-selected="true"] {
        background: #FFFFFF !important;
        color: #0F172A !important;
        font-weight: 800 !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06) !important;
    }
    .stTabs [data-baseweb="tab-border"], .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }

    /* Minimal Panels & Cards */
    .mini-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 8px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    .mini-card-header {
        font-size: 0.68rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #475569;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* Market Pulse Strip */
    .pulse-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        align-items: center;
        justify-content: space-between;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 5px 12px;
        margin-bottom: 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #475569;
    }

    /* KPI Metric Tiles */
    .mini-tile {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 6px 8px;
        text-align: center;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    .mini-tile-lbl {
        font-size: 0.62rem;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin-bottom: 1px;
    }
    .mini-tile-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.05rem;
        font-weight: 800;
        line-height: 1.2;
    }
    .mini-tile-sub {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        color: #94A3B8;
        margin-top: 1px;
    }

    /* Live Hero Cards */
    .hero-light-buy {
        background: linear-gradient(135deg, #ECFDF5 0%, #FFFFFF 100%);
        border: 1.5px solid #10B981;
        border-radius: 6px;
        padding: 10px 12px;
        margin-bottom: 8px;
    }
    .hero-light-sell {
        background: linear-gradient(135deg, #FFF1F2 0%, #FFFFFF 100%);
        border: 1.5px solid #F43F5E;
        border-radius: 6px;
        padding: 10px 12px;
        margin-bottom: 8px;
    }
    .hero-light-wait {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 10px 12px;
        margin-bottom: 8px;
    }
    .hero-light-active {
        background: linear-gradient(135deg, #F0F9FF 0%, #FFFFFF 100%);
        border: 1.5px solid #0284C7;
        border-radius: 6px;
        padding: 10px 12px;
        margin-bottom: 8px;
    }

    /* Form Controls */
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.20rem !important;
    }
    .stSelectbox label, .stNumberInput label, .stDateInput label, .stSlider label, .stTextInput label {
        font-size: 0.68rem !important;
        font-weight: 700 !important;
        color: #475569 !important;
        margin-bottom: 2px !important;
    }
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        color: #0F172A !important;
        min-height: 30px !important;
        height: 30px !important;
        font-size: 0.78rem !important;
        border-radius: 4px !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
    }
    div[data-baseweb="select"] span {
        color: #0F172A !important;
    }
    .stButton > button {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #CBD5E1 !important;
        min-height: 30px !important;
        height: 30px !important;
        font-size: 0.76rem !important;
        font-weight: 700 !important;
        border-radius: 4px !important;
        padding: 2px 10px !important;
    }
    .stButton > button:hover {
        background-color: #F1F5F9 !important;
        border-color: #94A3B8 !important;
    }
    .stButton > button[kind="primary"] {
        background: #0284C7 !important;
        border: 1px solid #0284C7 !important;
        color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #0369A1 !important;
    }

    /* Radio Pills */
    div[data-testid="stRadio"] > div {
        display: flex;
        flex-direction: row;
        gap: 6px;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ─── Session State Initialization ─────────────────────────────────────────────
if "active_live_trade" not in st.session_state:
    st.session_state["active_live_trade"] = None

if "live_trade_history" not in st.session_state:
    st.session_state["live_trade_history"] = []

if "active_live_setup" not in st.session_state:
    st.session_state["active_live_setup"] = "SETUP1"


# ─── Color-Coded P&L Formatting Helpers ────────────────────────────────────────

def style_pnl_matrix(df: pd.DataFrame) -> Any:
    """Applies clean minimalist green/red color styling across all P&L columns."""
    def pnl_color_rule(val):
        if isinstance(val, (int, float)):
            if val > 0:
                return 'color: #059669; font-weight: 800; background-color: #ECFDF5;'
            elif val < 0:
                return 'color: #DC2626; font-weight: 800; background-color: #FEF2F2;'
            return 'color: #64748B; font-weight: 600;'
        elif isinstance(val, str):
            clean = val.strip()
            if clean.startswith("+₹") or "WIN" in clean or "PROFIT" in clean:
                return 'color: #059669; font-weight: 800; background-color: #ECFDF5;'
            elif clean.startswith("-₹") or "LOSS" in clean:
                return 'color: #DC2626; font-weight: 800; background-color: #FEF2F2;'
            elif "SCRATCH" in clean or "BREAKEVEN" in clean:
                return 'color: #D97706; font-weight: 700; background-color: #FFFBEB;'
        return ''

    return df.style.map(pnl_color_rule)


# ─── Fast In-Memory Cached Data Engines ─────────────────────────────────────────

@st.cache_data(ttl=8, show_spinner=False)
def get_cached_live_market_stream(token: str, commodity_key: str = "CRUDEOIL") -> tuple[pd.DataFrame, dict, dict]:
    client = get_client()
    if token:
        try:
            instrument_key = get_active_crude_instrument_key(token, commodity_key=commodity_key)
            df_candles = client.get_intraday_candles(instrument_key, interval="30minute")
            if df_candles.empty or len(df_candles) < 20:
                df_candles = client.get_historical_candles(instrument_key, interval="30minute", days_back=4)
            live_quote = client.get_live_quote(instrument_key)
            prev_day_ohlc = client.get_previous_day_ohlc(instrument_key)
            return df_candles, live_quote, prev_day_ohlc
        except Exception:
            pass

    df_demo, _ = get_demo_historical_dataset(days=4, commodity_key=commodity_key)
    return df_demo, {}, {}


@st.cache_data(ttl=300, show_spinner=False)
def get_cached_news_sentiment() -> tuple[str, list]:
    monitor = get_news_monitor()
    monitor.refresh()
    return monitor.get_overall_sentiment(), monitor.get_news()


@st.cache_data(show_spinner=False)
def get_demo_historical_dataset(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    days: int = 30,
    commodity_key: str = "CRUDEOIL"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    np.random.seed(101)
    spec = get_commodity_spec(commodity_key)

    end_dt = end_date if end_date else datetime.now(IST).date()
    start_dt = start_date if start_date else (end_dt - timedelta(days=days))
    pre_start_dt = start_dt - timedelta(days=8)

    daily_dates = pd.date_range(start=pre_start_dt, end=end_dt, freq='B')
    base_price = spec.base_spot_estimate
    daily_rows = []
    
    current_regime = 0.8
    for i, d in enumerate(daily_dates):
        if i % 15 == 0:
            current_regime = np.random.choice([1.2, -1.1, 0.1, 1.4, -1.3])
        
        day_drift = current_regime * np.random.uniform(spec.default_sl_pts * 0.8, spec.default_sl_pts * 2.0)
        base_price = max(spec.base_spot_estimate * 0.7, min(spec.base_spot_estimate * 1.3, base_price + day_drift + np.random.normal(0, spec.default_sl_pts * 0.5)))
        d_range = np.random.uniform(spec.default_sl_pts * 2.5, spec.default_sl_pts * 5.5)
        d_high = base_price + d_range * np.random.uniform(0.4, 0.7)
        d_low = base_price - d_range * np.random.uniform(0.4, 0.7)
        d_open = base_price + np.random.uniform(-spec.default_sl_pts * 0.4, spec.default_sl_pts * 0.4)
        d_close = base_price + (day_drift * 0.5) + np.random.uniform(-spec.default_sl_pts * 0.3, spec.default_sl_pts * 0.3)

        daily_rows.append({
            "datetime": pd.to_datetime(d),
            "open": round(d_open, 2),
            "high": round(max(d_high, d_open, d_close), 2),
            "low": round(min(d_low, d_open, d_close), 2),
            "close": round(d_close, 2),
            "volume": int(np.random.uniform(50000, 120000)),
        })
    df_daily = pd.DataFrame(daily_rows)

    intraday_rows = []
    for row in daily_rows:
        day_d = row["datetime"].date()
        candle_times = [
            datetime.combine(day_d, datetime.strptime(f"{h:02d}:{m:02d}", "%H:%M").time())
            for h in range(9, 24)
            for m in (0, 30)
            if not (h == 23 and m > 30)
        ]
        curr_p = row["open"]
        day_trend_slope = (row["close"] - row["open"]) / len(candle_times)
        
        for t in candle_times:
            is_us_session = (17 <= t.hour <= 22)
            step_vol = spec.default_sl_pts * 0.45 if is_us_session else spec.default_sl_pts * 0.15
            drift = day_trend_slope * (1.8 if is_us_session else 0.4)
            
            curr_p = max(row["low"], min(row["high"], curr_p + drift + np.random.normal(0, step_vol)))
            c_high = curr_p + np.random.uniform(spec.tick_size * 2, spec.default_sl_pts * 0.35 if is_us_session else spec.default_sl_pts * 0.15)
            c_low = curr_p - np.random.uniform(spec.tick_size * 2, spec.default_sl_pts * 0.35 if is_us_session else spec.default_sl_pts * 0.15)
            c_open = curr_p + np.random.uniform(-spec.default_sl_pts * 0.1, spec.default_sl_pts * 0.1)

            intraday_rows.append({
                "datetime": t,
                "open": round(c_open, 2),
                "high": round(max(c_open, curr_p, c_high), 2),
                "low": round(min(c_open, curr_p, c_low), 2),
                "close": round(curr_p, 2),
                "volume": int(np.random.uniform(2000, 6500) if is_us_session else np.random.uniform(400, 1200)),
            })

    df_intraday = pd.DataFrame(intraday_rows)
    return df_intraday, df_daily


@st.cache_data(ttl=180, show_spinner=False)
def get_cached_historical_data(
    instrument_key: str,
    from_date: str,
    to_date: str,
    interval: str = "30minute",
    token: str = "",
    commodity_key: str = "CRUDEOIL"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    client = get_client()
    if token:
        try:
            df_candles = client.get_historical_candles(
                instrument_key, interval=interval, from_date=from_date, to_date=to_date
            )
            df_daily = client.get_historical_candles(
                instrument_key, interval="day",
                from_date=(datetime.strptime(from_date, "%Y-%m-%d") - timedelta(days=10)).strftime("%Y-%m-%d"),
                to_date=to_date
            )
            if not df_candles.empty and len(df_candles) >= 10:
                return df_candles, df_daily
        except Exception:
            pass

    s_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
    e_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
    return get_demo_historical_dataset(start_date=s_dt, end_date=e_dt, commodity_key=commodity_key)


# ─── Instant Reactive Backtest Function ───────────────────────────────────────
@st.cache_data(show_spinner=False)
def execute_reactive_backtest(
    strategy_model: str,
    from_date_str: str,
    to_date_str: str,
    sl_pts: float,
    t1_rr: float,
    session_filter: str,
    max_daily_trades: int,
    lots: int,
    initial_capital: float,
    market_regime: str,
    use_breakeven: bool,
    be_trigger_pts: float,
    token_str: str,
    commodity_key: str = "CRUDEOIL"
) -> BacktestReport:
    instrument_key = get_active_crude_instrument_key(token_str, commodity_key=commodity_key)
    df_bt_candles, df_bt_daily = get_cached_historical_data(
        instrument_key=instrument_key,
        from_date=from_date_str,
        to_date=to_date_str,
        interval="30minute",
        token=token_str,
        commodity_key=commodity_key
    )
    s_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
    e_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()

    tester = CrudeBacktester(df_candles=df_bt_candles, df_daily=df_bt_daily)
    report = tester.run(
        start_date=s_date,
        end_date=e_date,
        strategy_model=strategy_model,
        sl_pts=sl_pts,
        t1_rr=t1_rr,
        t2_rr=3.5,
        use_breakeven=use_breakeven,
        be_trigger_pts=be_trigger_pts,
        session_filter=session_filter,
        market_regime=market_regime,
        max_daily_trades=max_daily_trades,
        lots=lots,
        initial_capital=initial_capital
    )
    return report


def check_credentials() -> bool:
    if HAS_ANALYTICS_TOKEN:
        return True
    return bool(UPSTOX_API_KEY and UPSTOX_API_SECRET and UPSTOX_API_KEY != "your_api_key_here")


def is_market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() in (5, 6):
        return False
    open_time = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MIN, second=0)
    close_time = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MIN, second=0)
    return open_time <= now <= close_time


# ─── Main Application ─────────────────────────────────────────────────────────

def main():
    # ── Master Security PIN Gate (Optional via Secrets) ────────────────────────
    app_pin = ""
    try:
        if hasattr(st, "secrets") and "APP_PIN" in st.secrets:
            app_pin = str(st.secrets["APP_PIN"]).strip()
        elif os.getenv("APP_PIN"):
            app_pin = os.getenv("APP_PIN", "").strip()
    except Exception:
        pass

    if app_pin:
        if not st.session_state.get("pin_authenticated", False):
            st.markdown("""
            <div style="max-width:420px; margin:40px auto; padding:24px; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; box-shadow:0 4px 16px rgba(0,0,0,0.06); text-align:center;">
                <div style="font-size:2.2rem; margin-bottom:8px;">🔒</div>
                <h3 style="margin:0 0 4px 0; color:#0F172A; font-family:'Plus Jakarta Sans',sans-serif; font-size:1.1rem; font-weight:800;">CRUDE MCX PRO TERMINAL</h3>
                <p style="color:#64748B; font-size:0.78rem; margin-bottom:16px;">This terminal is private. Enter your security PIN to unlock.</p>
            </div>
            """, unsafe_allow_html=True)
            col_p1, col_p2, col_p3 = st.columns([1, 1.4, 1])
            with col_p2:
                entered_pin = st.text_input("Security PIN", type="password", key="pin_gate_input", placeholder="Enter PIN...")
                if st.button("🔓 Unlock Dashboard", type="primary", use_container_width=True):
                    if entered_pin.strip() == app_pin:
                        st.session_state["pin_authenticated"] = True
                        st.rerun()
                    else:
                        st.error("Incorrect PIN. Access denied.")
            st.stop()

    # ── Launch 24/7 Autonomous Background Scanner Daemon ──────────────────────
    start_background_scanner()

    market_open = is_market_open()
    status_bg = "#ECFDF5" if market_open else "#FFF1F2"
    status_color = "#059669" if market_open else "#DC2626"
    status_border = "#A7F3D0" if market_open else "#FECDD3"
    status_text = "MARKET OPEN" if market_open else "MARKET CLOSED"
    now_ist_str = datetime.now(IST).strftime("%H:%M:%S IST")

    # ── Active Asset Selection Pills (MCX Commodities & NSE/BSE Indices) ──────
    all_asset_pills = {
        "CRUDEOIL": "🛢️ CRUDE OIL",
        "GOLD": "🪙 GOLD MINI",
        "SILVER": "🥈 SILVER MINI",
        "NATURALGAS": "🔥 NAT GAS",
        "NIFTY": "📈 NIFTY 50",
        "BANKNIFTY": "🏦 BANK NIFTY",
        "FINNIFTY": "💳 FIN NIFTY",
        "SENSEX": "🏛️ SENSEX",
        "MIDCPNIFTY": "⚡ MIDCAP NIFTY",
    }

    if "selected_comm_key" not in st.session_state:
        st.session_state["selected_comm_key"] = "CRUDEOIL"

    def _handle_header_pill_change():
        chosen_lbl = st.session_state.get("commodity_header_selector")
        for k, v in all_asset_pills.items():
            if v == chosen_lbl:
                st.session_state["selected_comm_key"] = k
                break

    curr_comm = st.session_state["selected_comm_key"]
    curr_pill_lbl = all_asset_pills.get(curr_comm, "🛢️ CRUDE OIL")
    if "commodity_header_selector" not in st.session_state or st.session_state["commodity_header_selector"] not in all_asset_pills.values():
        st.session_state["commodity_header_selector"] = curr_pill_lbl
    elif all_asset_pills.get(curr_comm) != st.session_state["commodity_header_selector"]:
        st.session_state["commodity_header_selector"] = curr_pill_lbl

    col_nav1, col_nav2 = st.columns([3.2, 0.8])
    with col_nav1:
        st.radio(
            "Select Active Asset",
            list(all_asset_pills.values()),
            key="commodity_header_selector",
            on_change=_handle_header_pill_change,
            horizontal=True,
            label_visibility="collapsed"
        )

    comm_key = st.session_state["selected_comm_key"]
    spec = get_commodity_spec(comm_key)

    # Clean Classic Light Navbar
    st.markdown(f"""
    <div class="mini-nav">
        <div>
            <span class="mini-nav-title">{spec.icon} {spec.name.upper()} TERMINAL</span>
            <span style="color:#CBD5E1; margin:0 8px;">|</span>
            <span class="mini-nav-sub">Multi-Asset Options Live Engine & Backtester (MCX & NSE/BSE)</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
            <div style="display:flex; align-items:center; gap:5px; font-family:'JetBrains Mono',monospace; font-size:0.72rem; background:{status_bg}; padding:2px 8px; border-radius:4px; border:1px solid {status_border};">
                <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background-color:{status_color};"></span>
                <span style="color:{status_color}; font-weight:700;">{status_text}</span>
                <span style="color:#94A3B8;">|</span>
                <span style="color:#64748B;">{now_ist_str}</span>
            </div>
            <span class="mini-badge">{spec.segment}:{spec.symbol_keyword} ({spec.active_lot_size} {spec.lot_unit})</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_live, tab_audit, tab_backtest, tab_scanner = st.tabs([
        "⚡ Live Execution & Signals",
        "📜 Live System Trade Journal & History",
        "📊 Strategy Lab & Backtester",
        "🚀 Institutional NSE Stock Scanner"
    ])

    client = get_client()
    token_manager = client.token_manager
    alert_mgr = get_alert_manager()
    engine = SignalEngine()

    has_live_token = check_credentials()
    token_str = token_manager.get_token() if has_live_token else ""

    strategy_options = [
        "🎯 RSI + MACD Confluence",
        "💎 ICT & Fair Value Gap (FVG) + Liquidity Sweep",
        "📰 High-Impact Energy News Breakout",
        "🔄 20 EMA / Pivot Pullback",
        "⚡ Supertrend & 20 EMA Momentum",
        "📊 Standard Pivot Breakout"
    ]

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1: LIVE SIGNALS & ACTIVE POSITION LOCK-IN
    # ════════════════════════════════════════════════════════════════════════
    with tab_live:
        df_candles, live_quote, prev_day_ohlc = get_cached_live_market_stream(token_str, commodity_key=comm_key)
        news_flag, news_items = get_cached_news_sentiment()

        if prev_day_ohlc:
            pivot = calculate_pivot_points(
                prev_high=prev_day_ohlc["high"],
                prev_low=prev_day_ohlc["low"],
                prev_close=prev_day_ohlc["close"],
                date=prev_day_ohlc.get("date", "")
            )
        else:
            pivot = calculate_pivot_points(
                prev_high=float(df_candles["high"].iloc[-30:-1].max()),
                prev_low=float(df_candles["low"].iloc[-30:-1].min()),
                prev_close=float(df_candles["close"].iloc[-2])
            )

        indicators = compute_indicators(df_candles, pivot)

        ltp = float(live_quote.get("ltp", 0.0)) if live_quote else 0.0
        if ltp <= 0:
            ltp = float(indicators.close)
        
        prev_close_price = float(live_quote.get("prev_close", indicators.close)) if live_quote else indicators.close
        price_change = ltp - prev_close_price
        price_change_pct = (price_change / prev_close_price * 100.0) if prev_close_price else 0.0

        active_trade = st.session_state.get("active_live_trade")
        active_setup_key = st.session_state.get("active_live_setup", "SETUP1")
        cur_setup = SETUPS.get(active_setup_key, SETUPS["SETUP1"])

        # ── MULTI-ASSET LIVE RADAR OVERVIEW ───────────────────────────────────
        all_specs = COMMODITY_REGISTRY
        tile_list = []
        for k_ast, sp in all_specs.items():
            ast_cfg = get_active_strategy_config(k_ast)
            p_str = f"{ltp:,.0f}" if k_ast == comm_key else (f"{sp.base_spot_estimate:,.0f}" if sp.tick_size >= 1.0 else f"{sp.base_spot_estimate:.1f}")
            is_sel = (k_ast == comm_key)
            bg_c = "#EFF6FF" if is_sel else "#FFFFFF"
            bd_c = "#3B82F6" if is_sel else "#CBD5E1"
            tg_txt = ("🟢 " + ast_cfg.strategy_model.split(" ")[1]) if ast_cfg.enabled else "⏸️ Muted"
            tg_col = "#059669" if ast_cfg.enabled else "#94A3B8"
            tile_html = (
                f'<div style="padding:4px 6px; background:{bg_c}; border:1.5px solid {bd_c}; border-radius:5px;">'
                f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                f'<span style="font-weight:700;">{sp.icon} {sp.key}</span><b>₹{p_str}</b>'
                f'</div>'
                f'<div style="font-size:0.62rem; color:{tg_col}; font-weight:600; margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">'
                f'{tg_txt} ({ast_cfg.sl_pts:.0f}p)'
                f'</div>'
                f'</div>'
            )
            tile_list.append(tile_html)

        radar_body = "".join(tile_list)
        full_radar_html = (
            f'<div class="mini-card" style="padding:6px 12px; margin-bottom:6px; background:#F8FAFC; border-color:#E2E8F0;">'
            f'<div style="font-size:0.65rem; font-weight:800; color:#334155; margin-bottom:4px; text-transform:uppercase; letter-spacing:0.04em;">🌐 MULTI-ASSET 24/7 SCANNER RADAR (MCX COMMODITIES & NSE/BSE INDICES):</div>'
            f'<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 6px; font-family:\'JetBrains Mono\',monospace; font-size:0.72rem;">'
            f'{radar_body}'
            f'</div>'
            f'</div>'
        )
        st.markdown(full_radar_html, unsafe_allow_html=True)

        with st.expander("🎛️ Manage Multi-Asset 24/7 Live Telegram Alert States (9 Assets)", expanded=False):
            st.caption("Enable or mute alerts for any asset, and choose which saved strategy to deploy for 24/7 scanning.")
            
            def _handle_strat_deploy(asset_k):
                sel_id = st.session_state.get(f"mgr_sel_strat_{asset_k}")
                if sel_id:
                    deploy_strategy_to_asset(asset_k, sel_id)

            st.markdown("**🛢️ MCX Commodities**")
            col_mcx = st.columns(4)
            mcx_keys = ["CRUDEOIL", "GOLD", "SILVER", "NATURALGAS"]
            for idx_m, k_m in enumerate(mcx_keys):
                sp_m = get_commodity_spec(k_m)
                cfg_m = get_active_strategy_config(k_m)
                strats_m = get_saved_strategies_for_asset(k_m)
                with col_mcx[idx_m]:
                    st.markdown(f"**{sp_m.icon} {sp_m.name}**", unsafe_allow_html=True)
                    strat_ids = [s["id"] for s in strats_m]
                    curr_strat_id = next((s["id"] for s in strats_m if s.get("name") == cfg_m.title), strat_ids[0])
                    curr_idx = strat_ids.index(curr_strat_id) if curr_strat_id in strat_ids else 0

                    st.selectbox(
                        "Active Strategy",
                        options=strat_ids,
                        index=curr_idx,
                        format_func=lambda sid: next((s["name"] for s in strats_m if s["id"] == sid), sid),
                        key=f"mgr_sel_strat_{k_m}",
                        on_change=_handle_strat_deploy,
                        args=(k_m,),
                        label_visibility="collapsed"
                    )

                    st.markdown(f"<div style='font-size:0.70rem; color:#475569; margin-top:2px;'>SL: {cfg_m.sl_pts:.0f}p | 1:{cfg_m.t1_rr:.1f} RR</div>", unsafe_allow_html=True)
                    tg_val = st.toggle("Live Alerts", value=cfg_m.enabled, key=f"mgr_tg_{k_m}")
                    if tg_val != cfg_m.enabled:
                        cfg_m.enabled = tg_val
                        save_active_strategy_config(cfg_m)
                        st.rerun()

            st.divider()
            st.markdown("**📈 NSE & BSE Equity Indices**")
            col_idx = st.columns(5)
            idx_keys = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]
            for idx_i, k_i in enumerate(idx_keys):
                sp_i = get_commodity_spec(k_i)
                cfg_i = get_active_strategy_config(k_i)
                strats_i = get_saved_strategies_for_asset(k_i)
                with col_idx[idx_i]:
                    st.markdown(f"**{sp_i.icon} {sp_i.name}**", unsafe_allow_html=True)
                    strat_ids_i = [s["id"] for s in strats_i]
                    curr_strat_id_i = next((s["id"] for s in strats_i if s.get("name") == cfg_i.title), strat_ids_i[0])
                    curr_idx_i = strat_ids_i.index(curr_strat_id_i) if curr_strat_id_i in strat_ids_i else 0

                    st.selectbox(
                        "Active Strategy",
                        options=strat_ids_i,
                        index=curr_idx_i,
                        format_func=lambda sid: next((s["name"] for s in strats_i if s["id"] == sid), sid),
                        key=f"mgr_sel_strat_{k_i}",
                        on_change=_handle_strat_deploy,
                        args=(k_i,),
                        label_visibility="collapsed"
                    )

                    st.markdown(f"<div style='font-size:0.70rem; color:#475569; margin-top:2px;'>SL: {cfg_i.sl_pts:.0f}p | 1:{cfg_i.t1_rr:.1f} RR</div>", unsafe_allow_html=True)
                    tg_val = st.toggle("Live Alerts", value=cfg_i.enabled, key=f"mgr_tg_{k_i}")
                    if tg_val != cfg_i.enabled:
                        cfg_i.enabled = tg_val
                        save_active_strategy_config(cfg_i)
                        st.rerun()

        active_cfg = get_active_strategy_config(comm_key)

        # ── 4-Condition Real-Time Indicator Alignment Diagnostic Strip ────────
        st_color = "#059669" if indicators.st_fast_dir == 1 else "#DC2626"
        st_txt = f"11,2: ₹{indicators.st_fast:.0f} {'▲ BULL' if indicators.st_fast_dir == 1 else '▼ BEAR'}"
        macd_ok = (indicators.macd_line > 0 and indicators.macd_histogram > 0) or (indicators.macd_line < 0 and indicators.macd_histogram < 0)
        macd_color = "#059669" if (indicators.macd_line > 0 and indicators.macd_histogram > 0) else ("#DC2626" if (indicators.macd_line < 0 and indicators.macd_histogram < 0) else "#64748B")
        macd_txt = f"Line {indicators.macd_line:+.2f} | Hist {indicators.macd_histogram:+.2f}"
        rsi_color = "#059669" if indicators.rsi >= 60 else ("#DC2626" if indicators.rsi <= 40 else "#D97706")
        vol_color = "#059669" if indicators.vol_above_sma20 else "#64748B"
        vol_txt = f"{indicators.volume:,.0f} vs 20-SMA {indicators.avg_volume_20:,.0f}"

        st.markdown(f"""
        <div class="mini-card" style="padding:6px 12px; margin-bottom:6px; background:#F8FAFC; border-color:#CBD5E1;">
            <div style="font-size:0.64rem; font-weight:800; color:#475569; margin-bottom:4px; text-transform:uppercase; letter-spacing:0.04em;">⚡ Live Market Technical Indicator Alignment:</div>
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 8px; font-family:'JetBrains Mono',monospace; font-size:0.72rem;">
                <div style="border-left: 3px solid {st_color}; padding-left: 6px;">
                    <span style="color:#64748B;">1. SUPERTREND:</span> <b style="color:{st_color};">{st_txt}</b>
                </div>
                <div style="border-left: 3px solid {macd_color}; padding-left: 6px;">
                    <span style="color:#64748B;">2. MACD:</span> <b style="color:{macd_color};">{macd_txt}</b>
                </div>
                <div style="border-left: 3px solid {rsi_color}; padding-left: 6px;">
                    <span style="color:#64748B;">3. RSI(14):</span> <b style="color:{rsi_color};">{indicators.rsi:.1f}</b> <span style="color:#94A3B8;">(>60/>40)</span>
                </div>
                <div style="border-left: 3px solid {vol_color}; padding-left: 6px;">
                    <span style="color:#64748B;">4. VOLUME:</span> <b style="color:{vol_color};">{vol_txt}</b>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Active Live Setup Banner
        status_tag = "🟢 TELEGRAM SIGNALS ACTIVE" if active_cfg.enabled else "⏸️ TELEGRAM SIGNALS PAUSED"
        status_tag_color = "#059669" if active_cfg.enabled else "#DC2626"

        st.markdown(f"""
        <div class="mini-card" style="background:#F0F9FF; border-color:#BAE6FD; padding:6px 12px; margin-bottom:6px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
                <div style="display:flex; align-items:center; gap:6px;">
                    <span style="font-size:0.68rem; font-weight:800; color:#0369A1; letter-spacing:0.04em;">ACTIVE LIVE SETUP:</span>
                    <span style="font-family:'JetBrains Mono',monospace; font-size:0.82rem; font-weight:800; color:#0F172A;">{active_cfg.title}</span>
                    <span style="font-family:'JetBrains Mono',monospace; font-size:0.68rem; font-weight:700; color:{status_tag_color}; margin-left:6px;">({status_tag})</span>
                </div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:#475569; display:flex; gap:10px; flex-wrap:wrap;">
                    <span>SL: <b>{active_cfg.sl_pts:.1f} pts</b></span>
                    <span>Target 1: <b style="color:#059669;">1:{active_cfg.t1_rr:.1f} RR (+{active_cfg.sl_pts*active_cfg.t1_rr:.1f} pts)</b></span>
                    <span>Session: <b>{active_cfg.session_filter.split('(')[0]}</b></span>
                    <span>Filter: <b>{active_cfg.market_regime.split('(')[0]}</b></span>
                    <span>Frequency: <b>{'Max ' + str(active_cfg.max_daily_trades) + '/day' if active_cfg.max_daily_trades < 10 else 'Unlimited'}</b></span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Controls Row
        col_m1, col_m2, col_m3 = st.columns([2.5, 1.2, 1.3])
        with col_m1:
            live_lots = st.number_input("Trade Lots", min_value=1, max_value=20, value=1, step=1, disabled=(active_trade is not None))
        with col_m2:
            st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
            enable_audio = st.checkbox("🔊 Audio Alerts", value=True)
        with col_m3:
            st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
            with st.popover("📲 Telegram Alerts", use_container_width=True):
                cur_tg_tok, cur_tg_chat, cur_tg_on = get_telegram_creds()
                is_active = bool(cur_tg_tok and cur_tg_chat)
                
                if is_active:
                    masked_chat = f"••••{str(cur_tg_chat)[-4:]}" if len(str(cur_tg_chat)) >= 4 else "••••"
                    st.markdown(f"""
                    <div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:6px; padding:8px 10px; margin-bottom:8px;">
                        <div style="color:#065F46; font-size:0.75rem; font-weight:800; display:flex; align-items:center; gap:4px;">
                            <span>🔒 SECURED IN CLOUD SECRETS</span>
                        </div>
                        <div style="color:#047857; font-size:0.72rem; font-family:'JetBrains Mono',monospace; margin-top:2px;">
                            Status: <b>Connected & Active</b><br>
                            Chat ID: <b>{masked_chat}</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("📲 Send Test Ping to Phone", use_container_width=True, type="primary"):
                        ok, msg = send_telegram_test_message()
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)

                    st.divider()
                    st.markdown(f"**🔔 Alert Filter for {spec.name}**")
                    comm_tg_enabled = st.toggle(
                        f"Send {spec.name} Signals to Telegram",
                        value=active_cfg.enabled,
                        key=f"comm_tg_toggle_{comm_key}"
                    )
                    if comm_tg_enabled != active_cfg.enabled:
                        active_cfg.enabled = comm_tg_enabled
                        save_active_strategy_config(active_cfg)
                        st.rerun()

                    with st.expander("⚙️ Change Credentials"):
                        new_tok = st.text_input("New Bot Token", type="password", key="new_tok_inp", placeholder="Paste new token...")
                        new_chat = st.text_input("New Chat ID", type="password", key="new_chat_inp", placeholder="Paste new chat ID...")
                        if st.button("Save New Credentials", use_container_width=True):
                            if new_tok and new_chat:
                                save_telegram_env_credentials(new_tok, new_chat)
                                st.success("Updated successfully!")
                                st.rerun()
                            else:
                                st.warning("Please fill both fields.")
                else:
                    st.markdown("**Connect Telegram Mobile Alerts**")
                    st.caption("Receive instant BUY/SELL signals on your phone.")
                    inp_tg_token = st.text_input("Bot Token (from @BotFather)", type="password", placeholder="Paste token...")
                    inp_tg_chat = st.text_input("Chat ID (from @userinfobot)", placeholder="Paste chat ID...")

                    col_tg1, col_tg2 = st.columns(2)
                    with col_tg1:
                        if st.button("💾 Save", use_container_width=True, type="primary"):
                            if inp_tg_token and inp_tg_chat:
                                save_telegram_env_credentials(inp_tg_token, inp_tg_chat)
                                st.success("Credentials saved!")
                                st.rerun()
                            else:
                                st.warning("Enter both Bot Token & Chat ID.")
                    with col_tg2:
                        if st.button("📲 Test Ping", use_container_width=True):
                            if inp_tg_token and inp_tg_chat:
                                save_telegram_env_credentials(inp_tg_token, inp_tg_chat)
                            ok, msg = send_telegram_test_message()
                            if ok:
                                st.success(msg)
                            else:
                                st.error(msg)

        # Pulse Strip
        c_p_color = "#059669" if price_change >= 0 else "#DC2626"
        c_p_arrow = "▲" if price_change >= 0 else "▼"
        n_p_color = "#059669" if news_flag == "BULLISH" else ("#DC2626" if news_flag == "BEARISH" else "#64748B")
        fvg_badge = f"<b style='color:#0284C7;'>{indicators.fvg_type.replace('_', ' ')}</b>" if indicators.fvg_type != "NONE" else "<span style='color:#94A3B8;'>NONE</span>"

        st.markdown(f"""
        <div class="pulse-strip">
            <div><span style="color:#64748B;">SPOT LTP:</span> <b style="color:#0F172A;">₹{ltp:,.2f}</b> <span style="color:{c_p_color}; font-weight:700;">{c_p_arrow} ₹{abs(price_change):.2f} ({price_change_pct:+.2f}%)</span></div>
            <div><span style="color:#64748B;">PIVOT (PP):</span> <b style="color:#475569;">₹{pivot.pp:.0f}</b></div>
            <div><span style="color:#64748B;">ADX:</span> <b style="color:#0284C7;">{indicators.adx:.1f}</b></div>
            <div><span style="color:#64748B;">RSI:</span> <b style="color:#D97706;">{indicators.rsi:.1f}</b></div>
            <div><span style="color:#64748B;">ICT FVG:</span> {fvg_badge}</div>
            <div><span style="color:#64748B;">NEWS:</span> <b style="color:{n_p_color};">{news_flag}</b></div>
        </div>
        """, unsafe_allow_html=True)

        # ── SCENARIO A: AN ACTIVE POSITION IS LOCKED ──────────────────────────
        if active_trade is not None:
            direction = active_trade["direction"]
            entry_spot = active_trade["entry_spot"]
            entry_prem = active_trade["entry_premium"]
            entry_time_str = active_trade["entry_time"]
            signal_time_str = active_trade["signal_time"]
            lots = active_trade["lots"]
            contract_name = active_trade["contract"]

            pts_move = (ltp - entry_spot) if direction == "BUY" else (entry_spot - ltp)
            est_option_prem = max(5.0, round(entry_prem + (pts_move * 0.50), 2))
            gross_pnl = round((est_option_prem - entry_prem) * 100 * lots, 2)
            pnl_pct = round((gross_pnl / (entry_prem * 100 * lots)) * 100, 2) if entry_prem > 0 else 0.0

            trailing_status = f"🎯 Holding Position towards Target 1 (+{active_trade['t1_pts']:.0f} pts)"
            trailing_color = "#64748B"
            
            if pts_move >= active_trade["t1_pts"]:
                trailing_status = f"🎯 TARGET 1 HIT (+{active_trade['t1_pts']:.0f} pts): Book Full Profit!"
                trailing_color = "#059669"

            if pts_move >= active_trade["t2_pts"]:
                trailing_status = "🚀 TARGET 2 (RUNNER) HIT: Full Target Met!"
                trailing_color = "#10B981"

            pnl_card_border = "#059669" if gross_pnl >= 0 else "#DC2626"
            pnl_txt_color = "#059669" if gross_pnl >= 0 else "#DC2626"
            pnl_bg_tint = "#ECFDF5" if gross_pnl >= 0 else "#FEF2F2"
            sl_sub_txt = f"-{active_trade.get('sl_pts', 25.0):.0f} pts"
            strategy_name_short = cur_setup["model"].split("(")[0].strip()

            pos_html = f"""<div class="hero-light-active" style="border-color: {pnl_card_border};">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
<div style="display:flex; align-items:center; gap:6px;">
<span class="mini-badge" style="background:#FEF3C7; color:#92400E; border-color:#FCD34D;">🔒 CAPITAL ENGAGED</span>
<span style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; font-weight:800; color:#0F172A;">{contract_name} ({lots} Lot)</span>
</div>
<div style="font-family:'JetBrains Mono',monospace; font-size:0.70rem; color:#64748B;">
STRATEGY: <b>{strategy_name_short}</b> | ENTRY: <b>{entry_time_str}</b>
</div>
</div>
<div style="display:grid; grid-template-columns: 1.4fr repeat(4, 1fr); gap: 6px; margin-bottom: 8px;">
<div class="mini-tile" style="border-top: 2.5px solid {pnl_card_border}; background: {pnl_bg_tint};">
<div class="mini-tile-lbl">LIVE RUNNING P&L</div>
<div class="mini-tile-val" style="color:{pnl_txt_color}; font-size:1.20rem;">₹{gross_pnl:+,.0f}</div>
<div class="mini-tile-sub" style="color:{pnl_txt_color}; font-weight:700;">{pnl_pct:+.2f}% Return</div>
</div>
<div class="mini-tile" style="border-top: 2.5px solid #0284C7;">
<div class="mini-tile-lbl">OPTION VALUE</div>
<div class="mini-tile-val" style="color:#0284C7;">₹{est_option_prem:.2f}</div>
<div class="mini-tile-sub">Bought @ ₹{entry_prem:.2f}</div>
</div>
<div class="mini-tile" style="border-top: 2.5px solid #64748B;">
<div class="mini-tile-lbl">SPOT MOVE</div>
<div class="mini-tile-val" style="color:{pnl_txt_color};">{pts_move:+.1f} pts</div>
<div class="mini-tile-sub">Entry: ₹{entry_spot:.0f}</div>
</div>
<div class="mini-tile" style="border-top: 2.5px solid #DC2626;">
<div class="mini-tile-lbl">STOP LOSS</div>
<div class="mini-tile-val" style="color:#DC2626;">₹{active_trade['current_sl_prem']:.2f}</div>
<div class="mini-tile-sub">{sl_sub_txt}</div>
</div>
<div class="mini-tile" style="border-top: 2.5px solid #059669;">
<div class="mini-tile-lbl">TARGET 1 (1:{cur_setup['t1_rr']:.1f} RR)</div>
<div class="mini-tile-val" style="color:#059669;">₹{active_trade['t1_premium']:.2f}</div>
<div class="mini-tile-sub">+{active_trade['t1_pts']:.0f} pts move</div>
</div>
</div>
<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:4px; padding:4px 8px; font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:{trailing_color}; font-weight:700;">
{trailing_status}
</div>
</div>"""
            st.markdown(pos_html, unsafe_allow_html=True)

            col_act1, col_act2, col_act3 = st.columns([1.0, 1.0, 1.2])
            
            with col_act1:
                if st.button("🛡️ Lock Breakeven", use_container_width=True):
                    active_trade["be_active"] = True
                    active_trade["current_sl_prem"] = entry_prem
                    st.success("Stop Loss moved to Cost-to-Cost!")
                    st.rerun()

            with col_act2:
                if st.button("🎯 Book Target 1", use_container_width=True):
                    chg = calculate_mcx_option_charges(entry_prem, active_trade['t1_premium'], lots=lots)
                    net_pnl = round(((active_trade['t1_premium'] - entry_prem) * 100 * lots) - chg["total_charges"], 2)
                    st.session_state["live_trade_history"].append({
                        "Trade #": f"#{len(st.session_state['live_trade_history'])+1:02d}",
                        "Signal Time": signal_time_str,
                        "Entry Time": entry_time_str,
                        "Exit Time": datetime.now(IST).strftime("%H:%M:%S"),
                        "Contract": contract_name,
                        "Entry (₹)": f"₹{entry_prem:.2f}",
                        "Exit (₹)": f"₹{active_trade['t1_premium']:.2f}",
                        "Gross P&L (₹)": f"+₹{(active_trade['t1_premium'] - entry_prem) * 100 * lots:,.0f}",
                        "Charges (₹)": f"₹{chg['total_charges']:.0f}",
                        "Net In-Pocket (₹)": f"+₹{net_pnl:,.0f}",
                        "Exit Trigger": f"🎯 TARGET 1 (1:{cur_setup['t1_rr']:.1f}) HIT",
                        "Outcome": "WIN"
                    })
                    st.session_state["active_live_trade"] = None
                    st.success("Target 1 booked! Trade recorded in history.")
                    st.rerun()

            with col_act3:
                if st.button("⏹️ Exit / Square Off Position", use_container_width=True):
                    chg = calculate_commodity_option_charges(entry_prem, est_option_prem, commodity_key=comm_key, lots=lots)
                    net_pnl = round(gross_pnl - chg["total_charges"], 2)
                    outcome = "WIN" if net_pnl > 0 else ("LOSS" if net_pnl < 0 else "BREAKEVEN")
                    gross_str = f"+₹{gross_pnl:,.0f}" if gross_pnl >= 0 else f"-₹{abs(gross_pnl):,.0f}"
                    net_str = f"+₹{net_pnl:,.0f}" if net_pnl >= 0 else f"-₹{abs(net_pnl):,.0f}"

                    st.session_state["live_trade_history"].append({
                        "Trade #": f"#{len(st.session_state['live_trade_history'])+1:02d}",
                        "Signal Time": signal_time_str,
                        "Entry Time": entry_time_str,
                        "Exit Time": datetime.now(IST).strftime("%H:%M:%S"),
                        "Contract": contract_name,
                        "Entry (₹)": f"₹{entry_prem:.2f}",
                        "Exit (₹)": f"₹{est_option_prem:.2f}",
                        "Gross P&L (₹)": gross_str,
                        "Charges (₹)": f"₹{chg['total_charges']:.0f}",
                        "Net In-Pocket (₹)": net_str,
                        "Exit Trigger": "⏹️ MANUAL SQUARE-OFF",
                        "Outcome": outcome
                    })
                    st.session_state["active_live_trade"] = None
                    st.info("Position squared off and capital released.")
                    st.rerun()

        # ── SCENARIO B: SCANNING FOR NEW SIGNAL (CAPITAL AVAILABLE) ───────────
        else:
            signal = engine.generate_signal(
                indicators=indicators,
                strategy_model=active_cfg.strategy_model,
                news_flag=news_flag,
                current_price=ltp,
                sl_pts=active_cfg.sl_pts,
                t1_rr=active_cfg.t1_rr,
                t2_rr=active_cfg.t2_rr,
                market_regime=active_cfg.market_regime,
                trailing_mode=active_cfg.trailing_mode,
                commodity_key=comm_key
            )

            if signal.signal == SignalType.BUY:
                hero_cls = "hero-light-buy"
                pill_bg = "#D1FAE5"
                pill_txt = "#065F46"
                pill_border = "#6EE7B7"
                action_title = f"🟢 BUY CALL (CE) — {signal.option_contract}"
                action_desc = f"Bullish setup on <b>{active_cfg.strategy_model}</b>. Execute ATM Call Option."
            elif signal.signal == SignalType.SELL:
                hero_cls = "hero-light-sell"
                pill_bg = "#FFE4E6"
                pill_txt = "#9F1239"
                pill_border = "#FDA4AF"
                action_title = f"🔴 BUY PUT (PE) — {signal.option_contract}"
                action_desc = f"Bearish breakdown on <b>{active_cfg.strategy_model}</b>. Execute ATM Put Option."
            else:
                hero_cls = "hero-light-wait"
                pill_bg = "#F1F5F9"
                pill_txt = "#475569"
                pill_border = "#CBD5E1"
                action_title = "⚪ AWAITING CONVICTION SETUP"
                action_desc = f"Scanning market via <b>{active_cfg.strategy_model}</b> (Filter: {active_cfg.market_regime.split('(')[0]}). Capital ready."

            grid_html = ""
            if signal.signal != SignalType.NEUTRAL:
                tot_risk_rs = signal.option_lot_risk_rs * live_lots
                tot_t1_rs = signal.option_lot_target1_rs * live_lots
                tot_t2_rs = (signal.option_target2 - signal.option_buy_price) * spec.active_lot_size * live_lots

                # Note: Automated Telegram signal dispatching is strictly managed 24/7 by background_scanner daemon
                # to enforce per-asset cooldowns, candle bar deduplication, and daily frequency limits.

                grid_html = f"""<div style="display:grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin-bottom: 8px;">
<div class="mini-tile" style="border-top: 2.5px solid #0284C7;">
<div class="mini-tile-lbl">ENTRY PREMIUM</div>
<div class="mini-tile-val" style="color:#0284C7;">₹{signal.option_buy_price:.2f}</div>
<div class="mini-tile-sub">Spot: ₹{signal.entry_price:.0f}</div>
</div>
<div class="mini-tile" style="border-top: 2.5px solid #DC2626;">
<div class="mini-tile-lbl">STOP LOSS ({cur_setup['sl_pts']:.0f} PTS)</div>
<div class="mini-tile-val" style="color:#DC2626;">₹{signal.option_stop_loss:.2f}</div>
<div class="mini-tile-sub" style="color:#DC2626; font-weight:700;">-₹{tot_risk_rs:,.0f} Max Risk</div>
</div>
<div class="mini-tile" style="border-top: 2.5px solid #059669;">
<div class="mini-tile-lbl">TARGET 1 (1:{cur_setup['t1_rr']:.1f} RR)</div>
<div class="mini-tile-val" style="color:#059669;">₹{signal.option_target1:.2f}</div>
<div class="mini-tile-sub" style="color:#059669; font-weight:700;">+₹{tot_t1_rs:,.0f} Profit</div>
</div>
<div class="mini-tile" style="border-top: 2.5px solid #10B981;">
<div class="mini-tile-lbl">TARGET 2 (1:3.5 RR)</div>
<div class="mini-tile-val" style="color:#10B981;">₹{signal.option_target2:.2f}</div>
<div class="mini-tile-sub" style="color:#10B981; font-weight:700;">+₹{tot_t2_rs:,.0f} Runner</div>
</div>
<div class="mini-tile" style="border-top: 2.5px solid #D97706;">
<div class="mini-tile-lbl">SETUP PRESET</div>
<div class="mini-tile-val" style="color:#D97706; font-size:0.82rem;">{cur_setup['badge']}</div>
<div class="mini-tile-sub">{cur_setup['regime'].split('(')[0].strip()}</div>
</div>
</div>"""

            scan_html = f"""<div class="{hero_cls}">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
<div style="display:flex; align-items:center; gap:6px;">
<span style="background:{pill_bg}; color:{pill_txt}; border:1px solid {pill_border}; font-family:'JetBrains Mono',monospace; font-size:0.75rem; font-weight:800; padding:2px 8px; border-radius:4px;">{action_title}</span>
<span style="font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:#64748B;">
CONFIDENCE: <b style="color:{signal.confidence_color};">{signal.confidence.value} ({signal.conditions_met}/{signal.total_conditions} Met)</b>
</span>
</div>
<div style="font-family:'JetBrains Mono',monospace; font-size:0.68rem; color:#64748B;">
SIGNAL AT: <b>{signal.timestamp}</b>
</div>
</div>
<div style="font-size:0.78rem; color:#334155; margin-bottom:6px;">
{action_desc}
</div>
{grid_html}
</div>"""
            st.markdown(scan_html, unsafe_allow_html=True)

            if signal.signal != SignalType.NEUTRAL:
                btn_txt = f"📊 Lock in Dashboard Deck ({signal.option_contract} - {live_lots} Lot)"
                if st.button(btn_txt, use_container_width=True, type="secondary"):
                    st.session_state["active_live_trade"] = {
                        "direction": signal.signal.value,
                        "contract": signal.option_contract,
                        "entry_spot": signal.entry_price,
                        "entry_premium": signal.option_buy_price,
                        "current_sl_prem": signal.option_stop_loss,
                        "t1_premium": signal.option_target1,
                        "t2_premium": signal.option_target2,
                        "t1_pts": cur_setup["sl_pts"] * cur_setup["t1_rr"],
                        "t2_pts": cur_setup["sl_pts"] * 3.5,
                        "sl_pts": cur_setup["sl_pts"],
                        "lots": live_lots,
                        "signal_time": signal.timestamp,
                        "entry_time": datetime.now(IST).strftime("%H:%M:%S"),
                        "be_active": False
                    }
                    st.rerun()

        # ── TODAY'S LIVE EXECUTED TRADE HISTORY LEDGER ─────────────────────────
        st.markdown('<div class="mini-card" style="margin-top:6px;"><div class="mini-card-header">📜 TODAY\'S LIVE EXECUTED TRADES & REALIZED P&L LEDGER</div>', unsafe_allow_html=True)

        history_list = st.session_state.get("live_trade_history", [])
        if history_list:
            df_hist = pd.DataFrame(history_list)
            st.dataframe(style_pnl_matrix(df_hist), use_container_width=True, hide_index=True)
        else:
            st.markdown("""
            <div style="text-align:center; padding:8px; color:#94A3B8; font-family:'JetBrains Mono',monospace; font-size:0.75rem;">
                No trades closed yet today. Completed live trades and their color-coded P&L will appear here.
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2: LIVE SYSTEM SIGNAL AUDIT & TRADE JOURNAL
    # ════════════════════════════════════════════════════════════════════════
    with tab_audit:
        from trade_database import get_live_trades_df, get_live_performance_summary
        
        st.markdown("""
        <div class="mini-card" style="padding:10px 14px; margin-bottom:10px;">
            <div style="font-size:0.95rem; font-weight:800; color:#0F172A; display:flex; align-items:center; gap:6px;">
                <span>📜</span> <span>LIVE SYSTEM TRADE JOURNAL & AUDIT LEDGER</span>
            </div>
            <div style="font-size:0.75rem; color:#64748B; margin-top:2px;">
                Permanent database of every live signal fired by the 24/7 backend daemon. Tracks exact execution levels, target hits, stop losses, duration, and net in-pocket P/L.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Performance Summary KPIs
        live_perf = get_live_performance_summary()
        
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        with k1:
            st.markdown(f"""
            <div class="mini-tile" style="border-top: 2.5px solid #0284C7;">
                <div class="mini-tile-lbl">TOTAL SIGNALS</div>
                <div class="mini-tile-val">{live_perf['total_signals']}</div>
                <div class="mini-tile-sub">{live_perf['completed_trades']} Closed | {live_perf['open_trades']} Open</div>
            </div>
            """, unsafe_allow_html=True)
            
        with k2:
            wr = live_perf['win_rate']
            wr_col = "#059669" if wr >= 50 else ("#D97706" if wr > 0 else "#64748B")
            st.markdown(f"""
            <div class="mini-tile" style="border-top: 2.5px solid {wr_col};">
                <div class="mini-tile-lbl">LIVE WIN RATE</div>
                <div class="mini-tile-val" style="color:{wr_col};">{wr:.1f}%</div>
                <div class="mini-tile-sub">{live_perf['winning_trades']}W / {live_perf['losing_trades']}L</div>
            </div>
            """, unsafe_allow_html=True)
            
        with k3:
            net_pnl = live_perf['total_net_pnl']
            pnl_col = "#059669" if net_pnl > 0 else ("#DC2626" if net_pnl < 0 else "#64748B")
            pnl_sign = "+" if net_pnl > 0 else ""
            st.markdown(f"""
            <div class="mini-tile" style="border-top: 2.5px solid {pnl_col};">
                <div class="mini-tile-lbl">NET REALIZED P/L</div>
                <div class="mini-tile-val" style="color:{pnl_col};">{pnl_sign}₹{net_pnl:,.2f}</div>
                <div class="mini-tile-sub">Gross: ₹{live_perf['total_gross_pnl']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with k4:
            st.markdown(f"""
            <div class="mini-tile" style="border-top: 2.5px solid #D97706;">
                <div class="mini-tile-lbl">BROKERAGE & TAXES</div>
                <div class="mini-tile-val" style="color:#D97706;">₹{live_perf['total_charges']:,.2f}</div>
                <div class="mini-tile-sub">CTT, GST, Stamp</div>
            </div>
            """, unsafe_allow_html=True)
            
        with k5:
            pf = live_perf['profit_factor']
            pf_col = "#059669" if pf >= 1.5 else ("#D97706" if pf >= 1.0 else "#64748B")
            st.markdown(f"""
            <div class="mini-tile" style="border-top: 2.5px solid {pf_col};">
                <div class="mini-tile-lbl">PROFIT FACTOR</div>
                <div class="mini-tile-val" style="color:{pf_col};">{pf:.2f}</div>
                <div class="mini-tile-sub">Max DD: ₹{live_perf['max_drawdown']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with k6:
            st.markdown(f"""
            <div class="mini-tile" style="border-top: 2.5px solid #6366F1;">
                <div class="mini-tile-lbl">ACTIVE OPEN TRADES</div>
                <div class="mini-tile-val" style="color:#6366F1;">{live_perf['open_trades']}</div>
                <div class="mini-tile-sub">Isolated 1/Asset</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
        
        # Filter Bar
        f_col1, f_col2, f_col3, f_col4 = st.columns([1.5, 1.5, 1.5, 1.5])
        with f_col1:
            asset_options = ["ALL"] + list(COMMODITY_REGISTRY.keys())
            sel_asset = st.selectbox("Filter Asset", asset_options, format_func=lambda x: "🌐 All Assets (9)" if x == "ALL" else f"{COMMODITY_REGISTRY[x].icon} {COMMODITY_REGISTRY[x].name}", key="live_log_asset_filter")
        with f_col2:
            status_options = ["ALL", "OPEN", "TARGET2", "TARGET1", "TRAIL_COST_EXIT", "STOP_LOSS"]
            sel_status = st.selectbox("Filter Outcome", status_options, format_func=lambda x: "All Outcomes" if x == "ALL" else x, key="live_log_status_filter")
        with f_col3:
            log_date_from = st.date_input("From Date", value=datetime.now(IST).date() - timedelta(days=30), key="live_log_date_from")
        with f_col4:
            log_date_to = st.date_input("To Date", value=datetime.now(IST).date(), key="live_log_date_to")

        df_live_log = get_live_trades_df(
            commodity_key=sel_asset if sel_asset != "ALL" else None,
            date_from=str(log_date_from),
            date_to=str(log_date_to),
            limit=500
        )
        
        if sel_status != "ALL" and not df_live_log.empty:
            df_live_log = df_live_log[df_live_log["status"] == sel_status]

        if df_live_log.empty:
            st.info("ℹ️ No live trades recorded yet in the database for the selected filter. Newly generated signals will automatically appear here in real-time.")
        else:
            display_df = df_live_log[[
                "trade_id", "commodity_key", "contract_name", "direction",
                "entry_time", "exit_time", "duration_str", "entry_premium",
                "exit_premium", "points_captured", "charges_rs", "net_pnl_rs", "outcome"
            ]].copy()
            
            display_df.rename(columns={
                "trade_id": "Trade ID",
                "commodity_key": "Asset",
                "contract_name": "Contract",
                "direction": "Direction",
                "entry_time": "Entry Time",
                "exit_time": "Exit Time",
                "duration_str": "Duration",
                "entry_premium": "Entry (₹)",
                "exit_premium": "Exit (₹)",
                "points_captured": "Pts",
                "charges_rs": "Taxes (₹)",
                "net_pnl_rs": "Net P/L (₹)",
                "outcome": "Status"
            }, inplace=True)

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=380
            )

            # CSV Download Button
            csv_data = df_live_log.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Live Trade Log to CSV",
                data=csv_data,
                file_name=f"live_trade_audit_log_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="btn_download_live_csv"
            )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3: INSTANT REACTIVE STRATEGY LAB & BACKTESTER
    # ════════════════════════════════════════════════════════════════════════
    with tab_backtest:
        st.markdown('<div class="mini-card"><div class="mini-card-header">🎛️ STRATEGY AUDIT LAB — MULTI-COMMODITY CONTROLS</div>', unsafe_allow_html=True)

        comm_options_map = {
            "🛢️ MCX Crude Oil (100 bbl)": "CRUDEOIL",
            "🪙 MCX Gold Mini (100g)": "GOLD",
            "🥈 MCX Silver Mini (5kg)": "SILVER",
            "🔥 MCX Natural Gas (1250 mmBtu)": "NATURALGAS",
            "📈 NSE Nifty 50 (75 Qty)": "NIFTY",
            "🏦 NSE Bank Nifty (15 Qty)": "BANKNIFTY",
            "💳 NSE Fin Nifty (25 Qty)": "FINNIFTY",
            "🏛️ BSE Sensex (10 Qty)": "SENSEX",
            "⚡ NSE Midcap Nifty (50 Qty)": "MIDCPNIFTY",
        }
        key_to_bt_lbl = {v: k for k, v in comm_options_map.items()}

        def _handle_bt_asset_change():
            chosen_lbl = st.session_state.get("bt_commodity_select")
            if chosen_lbl in comm_options_map:
                new_k = comm_options_map[chosen_lbl]
                st.session_state["selected_comm_key"] = new_k
                if new_k in all_asset_pills:
                    st.session_state["commodity_header_selector"] = all_asset_pills[new_k]

        expected_bt_lbl = key_to_bt_lbl.get(comm_key, list(comm_options_map.keys())[0])
        if "bt_commodity_select" not in st.session_state or st.session_state.get("_last_synced_bt_k") != comm_key:
            st.session_state["bt_commodity_select"] = expected_bt_lbl
            st.session_state["_last_synced_bt_k"] = comm_key
        elif st.session_state["bt_commodity_select"] != expected_bt_lbl and st.session_state.get("_last_synced_bt_k") != comm_key:
            st.session_state["bt_commodity_select"] = expected_bt_lbl
            st.session_state["_last_synced_bt_k"] = comm_key

        row0_c1, row0_c2 = st.columns([1.6, 2.4])
        with row0_c1:
            bt_comm_label = st.selectbox(
                "Asset to Backtest (MCX / NSE / BSE)",
                list(comm_options_map.keys()),
                key="bt_commodity_select",
                on_change=_handle_bt_asset_change
            )
            bt_comm_key = comm_options_map.get(bt_comm_label, comm_key)
            bt_spec = get_commodity_spec(bt_comm_key)
        with row0_c2:
            st.markdown(f"""
            <div style="font-family:'JetBrains Mono',monospace; font-size:0.74rem; color:#475569; padding-top:24px;">
                <b>Segment:</b> {bt_spec.segment} | <b>Lot:</b> {bt_spec.active_lot_size} {bt_spec.lot_unit} | <b>Strike Step:</b> {bt_spec.strike_step:.0f} pts | <b>Base Spot:</b> ₹{bt_spec.base_spot_estimate:,.0f} | <b>Benchmark SL:</b> {bt_spec.default_sl_pts:.0f} pts
            </div>
            """, unsafe_allow_html=True)

        default_start = (datetime.now(IST) - timedelta(days=90)).date()
        default_end = datetime.now(IST).date()

        # Row 1: Model, Date Range, Session, Capital, Lots
        row1_c1, row1_c2, row1_c3, row1_c4, row1_c5 = st.columns([1.6, 1.2, 1.1, 0.8, 0.5])

        with row1_c1:
            strategy_choice = st.selectbox(
                "Strategy Model",
                strategy_options,
                index=0,
                key="bt_strategy_model"
            )

        with row1_c2:
            date_range = st.date_input(
                "Audit Date Range",
                value=(default_start, default_end),
                max_value=default_end,
                key="bt_date_range"
            )

        with row1_c3:
            if bt_spec.category == "INDEX":
                avail_sessions = [
                    "⚡ Full Equity Session (09:15 - 15:30 IST)",
                    "🌅 Morning Opening Drive (09:15 - 11:30 IST)"
                ]
            else:
                avail_sessions = [
                    "🔥 US High-Peak / Prime Session (16:30 - 22:30 IST)",
                    "🌅 Full MCX Session (09:00 - 23:30 IST)"
                ]
            session_choice = st.selectbox(
                "Session Window",
                avail_sessions,
                index=0,
                key=f"bt_session_{bt_comm_key}"
            )

        with row1_c4:
            initial_cap = st.number_input("Initial Cap (₹)", min_value=10000, max_value=5000000, value=100000, step=5000, key="bt_init_cap")

        with row1_c5:
            trade_lot_size = st.number_input("Lots", min_value=1, max_value=50, value=1, step=1, key="bt_lots")

        # Row 2: SL, Target 1 RR, Chop Filter, Trailing SL, Frequency
        row2_c1, row2_c2, row2_c3, row2_c4, row2_c5 = st.columns([0.9, 0.7, 1.2, 1.1, 0.9])

        with row2_c1:
            min_sl = max(1.0, float(round(bt_spec.default_sl_pts * 0.4)))
            max_sl = float(round(bt_spec.default_sl_pts * 2.2))
            def_sl = float(bt_spec.default_sl_pts)
            sl_step = float(max(0.1, bt_spec.tick_size * (10 if bt_spec.key != "NATURALGAS" else 2)))
            sl_input = st.slider(f"SL ({bt_spec.name})", min_value=min_sl, max_value=max_sl, value=def_sl, step=sl_step, key=f"bt_sl_{bt_comm_key}")

        with row2_c2:
            t1_rr_input = st.selectbox("Target 1 RR", [1.5, 1.8, 2.0, 2.2, 2.5, 3.0], index=3, key="bt_rr")

        with row2_c3:
            regime_choice = st.selectbox(
                "Market Chop Filter",
                ["🎯 Balanced Quality (ADX >= 18)", "🛡️ Strict Trend (ADX >= 23)", "🔥 High Frequency (ADX >= 14)"],
                index=0,
                key="bt_regime"
            )

        with row2_c4:
            trail_choice = st.selectbox(
                "Trailing SL Protection",
                ["❌ Pure Fixed SL", "🛡️ Lock Cost @ 1:1 RR", "🛡️ Lock Cost @ Benchmark Move"],
                index=0,
                key="bt_trail"
            )

        with row2_c5:
            max_trades_input = st.selectbox(
                "Daily Frequency",
                [1, 2, 3, 10],
                format_func=lambda x: f"Max {x} Trade/Day" if x < 10 else "Unlimited Trades",
                index=2,
                key="bt_max_trades"
            )

        st.markdown('</div>', unsafe_allow_html=True)

        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            sel_start, sel_end = date_range
        elif isinstance(date_range, (list, tuple)) and len(date_range) == 1:
            sel_start = sel_end = date_range[0]
        else:
            sel_start = default_start
            sel_end = default_end

        from_str = sel_start.strftime("%Y-%m-%d")
        to_str = sel_end.strftime("%Y-%m-%d")

        use_be_flag = ("Lock Cost" in trail_choice)
        be_trigger_val = bt_spec.default_sl_pts if "Benchmark Move" in trail_choice else float(sl_input)

        # ⚡ Instant Reactive Calculation via @st.cache_data
        report = execute_reactive_backtest(
            strategy_model=strategy_choice,
            from_date_str=from_str,
            to_date_str=to_str,
            sl_pts=float(sl_input),
            t1_rr=float(t1_rr_input),
            session_filter=session_choice,
            max_daily_trades=int(max_trades_input),
            lots=int(trade_lot_size),
            initial_capital=float(initial_cap),
            market_regime=regime_choice,
            use_breakeven=use_be_flag,
            be_trigger_pts=be_trigger_val,
            token_str=token_str,
            commodity_key=bt_comm_key
        )

        if report.total_trades == 0:
            st.info(f"No trades triggered between {sel_start} and {sel_end}. Try switching session to Full MCX or adjusting Market Chop Filter.")
        else:
            calls_count = sum(1 for t in report.trades if t.direction == "BUY")
            puts_count = sum(1 for t in report.trades if t.direction == "SELL")

            net_pnl_color = "#059669" if report.total_net_pnl_rs >= 0 else "#DC2626"
            roi_color = "#059669" if report.roi_percent >= 0 else "#DC2626"

            # Performance Summary Strip
            st.markdown(f"""
            <div class="pulse-strip" style="margin-top:2px;">
                <div><span style="color:#64748B;">STRATEGY:</span> <b style="color:#0284C7;">{strategy_choice}</b></div>
                <div><span style="color:#64748B;">TRADES:</span> <b style="color:#0F172A;">{report.total_trades}</b> (<span style="color:#059669;">{calls_count} Calls</span> / <span style="color:#DC2626;">{puts_count} Puts</span>)</div>
                <div><span style="color:#64748B;">WIN RATE:</span> <b style="color:#059669;">{report.win_rate:.1f}%</b> ({report.winning_trades}W / {report.losing_trades}L)</div>
                <div><span style="color:#64748B;">NET P&L:</span> <b style="color:{net_pnl_color};">₹{report.total_net_pnl_rs:+,.0f}</b></div>
                <div><span style="color:#64748B;">ROI:</span> <b style="color:{roi_color};">{report.roi_percent:+.1f}%</b></div>
                <div><span style="color:#64748B;">TAXES:</span> <b style="color:#D97706;">₹{report.total_charges_rs:,.0f}</b></div>
            </div>
            """, unsafe_allow_html=True)

            # 6 KPI Tiles
            kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

            with kpi1:
                st.markdown(f"""
                <div class="mini-tile" style="border-top: 2.5px solid {net_pnl_color}; background: {'#ECFDF5' if report.total_net_pnl_rs >= 0 else '#FEF2F2'};">
                    <div class="mini-tile-lbl">NET IN-POCKET P&L</div>
                    <div class="mini-tile-val" style="color:{net_pnl_color};">₹{report.total_net_pnl_rs:+,.0f}</div>
                    <div class="mini-tile-sub">After Brokerage & Taxes</div>
                </div>
                """, unsafe_allow_html=True)

            with kpi2:
                st.markdown(f"""
                <div class="mini-tile" style="border-top: 2.5px solid {roi_color};">
                    <div class="mini-tile-lbl">NET ROI %</div>
                    <div class="mini-tile-val" style="color:{roi_color};">{report.roi_percent:+.1f}%</div>
                    <div class="mini-tile-sub">Bal: ₹{report.ending_capital_rs:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)

            with kpi3:
                st.markdown(f"""
                <div class="mini-tile" style="border-top: 2.5px solid #0284C7;">
                    <div class="mini-tile-lbl">GROSS P&L</div>
                    <div class="mini-tile-val" style="color:#0284C7;">₹{report.total_gross_pnl_rs:+,.0f}</div>
                    <div class="mini-tile-sub">{report.total_pts_pnl:+,.1f} pts captured</div>
                </div>
                """, unsafe_allow_html=True)

            with kpi4:
                st.markdown(f"""
                <div class="mini-tile" style="border-top: 2.5px solid #D97706;">
                    <div class="mini-tile-lbl">BROKERAGE & TAXES</div>
                    <div class="mini-tile-val" style="color:#D97706;">₹{report.total_charges_rs:,.0f}</div>
                    <div class="mini-tile-sub">CTT, GST, Stamp</div>
                </div>
                """, unsafe_allow_html=True)

            with kpi5:
                wr_color = "#059669" if report.win_rate >= 50 else "#D97706"
                st.markdown(f"""
                <div class="mini-tile" style="border-top: 2.5px solid {wr_color};">
                    <div class="mini-tile-lbl">WIN RATE</div>
                    <div class="mini-tile-val" style="color:{wr_color};">{report.win_rate:.1f}%</div>
                    <div class="mini-tile-sub">{report.winning_trades}W / {report.losing_trades}L</div>
                </div>
                """, unsafe_allow_html=True)

            with kpi6:
                pf_color = "#059669" if report.profit_factor >= 1.5 else ("#D97706" if report.profit_factor >= 1.0 else "#DC2626")
                st.markdown(f"""
                <div class="mini-tile" style="border-top: 2.5px solid {pf_color};">
                    <div class="mini-tile-lbl">PROFIT FACTOR</div>
                    <div class="mini-tile-val" style="color:{pf_color};">{report.profit_factor:.2f}</div>
                    <div class="mini-tile-sub">Max DD: ₹{report.max_drawdown_rs:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)

            # ── 🚀 SAVE & DEPLOY BACKTEST STRATEGY TO ASSET LIBRARY ────────
            st.markdown(f"""
            <div class="mini-card" style="background:#F0FDF4; border:1.5px solid #86EFAC; padding:10px 14px; margin-top:8px; margin-bottom:8px;">
                <div style="font-size:0.82rem; font-weight:800; color:#15803D; letter-spacing:0.02em; display:flex; align-items:center; gap:6px;">
                    <span>💾</span> <span>SAVE & DEPLOY BACKTEST SETUP TO {bt_spec.name.upper()} STRATEGY LIBRARY</span>
                </div>
            """, unsafe_allow_html=True)
            
            save_c1, save_c2, save_c3 = st.columns([2.2, 1.4, 1.4])
            with save_c1:
                suggested_name = f"{strategy_choice.split('(')[0].strip()} ({'1:' + str(t1_rr_input) + ' RR'})"
                strat_custom_name = st.text_input("Custom Strategy Name", value=suggested_name, key=f"inp_strat_name_{bt_comm_key}")
            with save_c2:
                st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
                if st.button(f"🚀 Save & Deploy Live", type="primary", use_container_width=True, key=f"btn_save_deploy_{bt_comm_key}"):
                    new_s = save_custom_strategy(
                        commodity_key=bt_comm_key,
                        name=strat_custom_name,
                        model=strategy_choice,
                        session_filter=session_choice,
                        sl_pts=float(sl_input),
                        t1_rr=float(t1_rr_input),
                        t2_rr=float(t1_rr_input * 1.5),
                        market_regime=regime_choice,
                        trailing_mode=trail_choice,
                        max_daily_trades=int(max_trades_input),
                        badge=f"+{report.win_rate:.0f}% WR | 1:{t1_rr_input:.1f} RR",
                        set_active=True
                    )
                    st.success(f"✅ Strategy '{strat_custom_name}' saved to {bt_spec.name} and deployed for 24/7 Live Scanning!")
                    st.rerun()
            with save_c3:
                st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
                if st.button(f"📁 Save to Library Only", type="secondary", use_container_width=True, key=f"btn_save_lib_only_{bt_comm_key}"):
                    new_s = save_custom_strategy(
                        commodity_key=bt_comm_key,
                        name=strat_custom_name,
                        model=strategy_choice,
                        session_filter=session_choice,
                        sl_pts=float(sl_input),
                        t1_rr=float(t1_rr_input),
                        t2_rr=float(t1_rr_input * 1.5),
                        market_regime=regime_choice,
                        trailing_mode=trail_choice,
                        max_daily_trades=int(max_trades_input),
                        badge=f"+{report.win_rate:.0f}% WR | 1:{t1_rr_input:.1f} RR",
                        set_active=False
                    )
                    st.success(f"📁 Strategy '{strat_custom_name}' saved to {bt_spec.name} library!")
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

            # ── 📚 MANAGE SAVED STRATEGIES FOR THIS ASSET (EDIT / DELETE / DEPLOY) ──
            asset_saved_strats = get_saved_strategies_for_asset(bt_comm_key)
            with st.expander(f"📚 Manage Saved Strategies for {bt_spec.name} ({len(asset_saved_strats)} Saved)", expanded=False):
                curr_active_cfg = get_active_strategy_config(bt_comm_key)

                for s_item in asset_saved_strats:
                    s_id = s_item["id"]
                    is_currently_active = (curr_active_cfg.title == s_item["name"])
                    border_c = "#10B981" if is_currently_active else "#E2E8F0"
                    bg_c = "#F0FDF4" if is_currently_active else "#F8FAFC"
                    active_badge = '<span style="color:#059669; font-weight:800; font-size:0.70rem; margin-left:6px;">(⚡ ACTIVE LIVE)</span>' if is_currently_active else ''
                    
                    row_html = (
                        f'<div style="background:{bg_c}; border:1px solid {border_c}; border-radius:6px; padding:6px 10px; margin-bottom:4px;">'
                        f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                        f'<div>'
                        f'<b style="font-size:0.82rem; color:#0F172A;">{s_item["name"]}</b>{active_badge}'
                        f'<div style="font-size:0.70rem; color:#64748B; font-family:\'JetBrains Mono\',monospace; margin-top:2px;">'
                        f'Model: <b>{s_item["model"]}</b> | SL: <b>{s_item["sl_pts"]:.0f} pts</b> | RR: <b>1:{s_item["t1_rr"]:.1f}</b> | Session: <b>{s_item["session"].split("(")[0].strip()}</b>'
                        f'</div>'
                        f'</div>'
                        f'</div>'
                        f'</div>'
                    )
                    
                    col_info, col_b1, col_b2, col_b3 = st.columns([5.2, 1.6, 1.4, 0.8])
                    with col_info:
                        st.markdown(row_html, unsafe_allow_html=True)
                    with col_b1:
                        st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)
                        if not is_currently_active:
                            if st.button("⚡ Deploy", key=f"btn_dep_{bt_comm_key}_{s_id}", use_container_width=True):
                                deploy_strategy_to_asset(bt_comm_key, s_id)
                                st.rerun()
                        else:
                            st.button("✅ Active", disabled=True, key=f"btn_act_dis_{bt_comm_key}_{s_id}", use_container_width=True)
                    with col_b2:
                        st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)
                        with st.popover("✏️ Rename", use_container_width=True):
                            new_name_val = st.text_input("New Name", value=s_item["name"], key=f"ren_inp_{bt_comm_key}_{s_id}")
                            if st.button("Save", key=f"btn_save_ren_{bt_comm_key}_{s_id}", type="primary"):
                                rename_custom_strategy(bt_comm_key, s_id, new_name_val)
                                st.success("Renamed!")
                                st.rerun()
                    with col_b3:
                        st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)
                        if st.button("🗑️", key=f"btn_del_{bt_comm_key}_{s_id}", use_container_width=True, help="Delete strategy"):
                            delete_custom_strategy(bt_comm_key, s_id)
                            st.rerun()

            st.markdown("<div style='margin-top:4px;'></div>", unsafe_allow_html=True)
            
            view_mode = st.radio(
                "Select Analysis View",
                ["📋 Trade Journal (Trade-by-Trade)", "📅 Day-by-Day Summary Ledger", "📈 Strategy Equity & Capital Curve"],
                horizontal=True,
                label_visibility="collapsed"
            )

            st.markdown('<div class="mini-card">', unsafe_allow_html=True)

            if view_mode == "📋 Trade Journal (Trade-by-Trade)":
                st.markdown(f'<div class="mini-card-header">AUDITED OPTION BUYING JOURNAL ({len(report.trades)} TRADES) — DYNAMIC OPTION ENTRY & COLOR-CODED P&L</div>', unsafe_allow_html=True)
                
                journal_rows = []
                running_cap = float(initial_cap)

                for t in report.trades:
                    entry_t_str = t.entry_time.strftime("%d-%b %H:%M") if isinstance(t.entry_time, datetime) else str(t.entry_time)
                    
                    # Exit Time Formatting
                    if isinstance(t.exit_time, datetime):
                        exit_t_str = t.exit_time.strftime("%d-%b %H:%M")
                    elif t.exit_time is not None:
                        try:
                            exit_t_str = pd.to_datetime(t.exit_time).strftime("%d-%b %H:%M")
                        except Exception:
                            exit_t_str = str(t.exit_time)
                    else:
                        exit_t_str = "--"

                    # Duration Calculation
                    try:
                        e_dt = pd.to_datetime(t.entry_time)
                        x_dt = pd.to_datetime(t.exit_time)
                        dur_mins = int((x_dt - e_dt).total_seconds() // 60)
                        if dur_mins < 60:
                            dur_str = f"{dur_mins}m"
                        else:
                            h = dur_mins // 60
                            m = dur_mins % 60
                            dur_str = f"{h}h {m}m" if m > 0 else f"{h}h"
                    except Exception:
                        dur_str = f"{t.holding_candles * 30}m" if hasattr(t, "holding_candles") and t.holding_candles > 0 else "--"

                    running_cap += t.net_option_pnl_rs

                    gross_str = f"+₹{t.gross_option_pnl_rs:,.0f}" if t.gross_option_pnl_rs >= 0 else f"-₹{abs(t.gross_option_pnl_rs):,.0f}"
                    net_str = f"+₹{t.net_option_pnl_rs:,.0f}" if t.net_option_pnl_rs >= 0 else f"-₹{abs(t.net_option_pnl_rs):,.0f}"

                    journal_rows.append({
                        "Trade #": f"#{t.trade_id:02d}",
                        "Entry Time": entry_t_str,
                        "Exit Time": exit_t_str,
                        "Duration": dur_str,
                        "Action": t.option_action,
                        "Contract": f"{t.strike} {t.option_type}",
                        "Buy (₹)": f"₹{t.option_buy_price:.2f}",
                        "Exit (₹)": f"₹{t.option_exit_price:.2f}",
                        "Trigger": t.exit_reason,
                        "Result": f"{'WIN' if t.status == 'WIN' else ('LOSS' if t.status == 'LOSS' else 'SCRATCH')}",
                        "Gross P&L": gross_str,
                        "Taxes (₹)": f"₹{t.total_charges_rs:,.0f}",
                        "Net In-Pocket": net_str,
                        "Account Balance (₹)": f"₹{running_cap:,.0f}",
                    })

                df_journal = pd.DataFrame(journal_rows)
                st.dataframe(style_pnl_matrix(df_journal), use_container_width=True, hide_index=True, height=340)

            elif view_mode == "📅 Day-by-Day Summary Ledger":
                st.markdown(f'<div class="mini-card-header">DAILY LEDGER BREAKDOWN ({report.total_days} TRADING DAYS) — DAILY CAPITAL BALANCE & P&L</div>', unsafe_allow_html=True)
                
                if not report.daily_summary.empty:
                    df_daily_view = report.daily_summary.copy()
                    
                    daily_running_cap = float(initial_cap)
                    running_caps = []
                    for net_val in df_daily_view["Net Option P&L (₹)"]:
                        daily_running_cap += float(net_val)
                        running_caps.append(f"₹{daily_running_cap:,.0f}")
                    
                    df_daily_view["Day End Balance (₹)"] = running_caps
                    df_daily_view["Gross P&L (₹)"] = df_daily_view["Gross P&L (₹)"].apply(lambda x: f"+₹{x:,.0f}" if x >= 0 else f"-₹{abs(x):,.0f}")
                    df_daily_view["Taxes & Brokerage (₹)"] = df_daily_view["Taxes & Brokerage (₹)"].apply(lambda x: f"₹{x:,.0f}")
                    df_daily_view["Net Option P&L (₹)"] = df_daily_view["Net Option P&L (₹)"].apply(lambda x: f"+₹{x:,.0f}" if x >= 0 else f"-₹{abs(x):,.0f}")
                    df_daily_view["Win Rate (%)"] = df_daily_view["Win Rate (%)"].apply(lambda x: f"{x:.1f}%")
                    df_daily_view["Day Outcome"] = df_daily_view["Day Outcome"].apply(
                        lambda x: "PROFITABLE" if x == "PROFITABLE" else ("LOSS" if x == "LOSS" else "BREAKEVEN")
                    )

                    st.dataframe(style_pnl_matrix(df_daily_view), use_container_width=True, hide_index=True, height=340)

            else:
                st.markdown('<div class="mini-card-header">CAPITAL GROWTH & EQUITY CURVE (AFTER BROKERAGE & TAXES)</div>', unsafe_allow_html=True)
                
                if not report.equity_curve.empty:
                    df_eq = report.equity_curve.copy()
                    fig_eq = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.7, 0.3])

                    fig_eq.add_trace(go.Scatter(
                        x=df_eq["Time"],
                        y=df_eq["Capital_Balance"],
                        mode="lines+markers",
                        name="Capital (₹)",
                        line=dict(color="#059669" if report.total_net_pnl_rs >= 0 else "#DC2626", width=2.0),
                        fill="tozeroy",
                        fillcolor="rgba(16, 185, 129, 0.08)" if report.total_net_pnl_rs >= 0 else "rgba(220, 38, 38, 0.08)",
                    ), row=1, col=1)

                    fig_eq.add_hline(y=float(initial_cap), line_color="#94A3B8", line_dash="dash", line_width=1, row=1, col=1)

                    fig_eq.add_trace(go.Scatter(
                        x=df_eq["Time"],
                        y=-df_eq["Drawdown_Rs"],
                        mode="lines",
                        name="Drawdown (₹)",
                        line=dict(color="#F43F5E", width=1.5),
                        fill="tozeroy",
                        fillcolor="rgba(244, 63, 94, 0.15)",
                    ), row=2, col=1)

                    fig_eq.update_layout(
                        height=320,
                        paper_bgcolor="#FFFFFF",
                        plot_bgcolor="#FFFFFF",
                        font=dict(color="#475569", family="JetBrains Mono", size=9),
                        margin=dict(l=8, r=15, t=8, b=8),
                        xaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
                        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Capital (₹)"),
                        yaxis2=dict(showgrid=True, gridcolor="#F1F5F9", title="Drawdown (₹)"),
                    )
                    st.plotly_chart(fig_eq, use_container_width=True)

            st.markdown('</div>', unsafe_allow_html=True)



    # ════════════════════════════════════════════════════════════════════════
    # TAB 4: NSE INTRADAY STOCKS SCANNER (ACTIONABLE TRADE LIST ONLY)
    # ════════════════════════════════════════════════════════════════════════
    with tab_scanner:
        col_hdr, col_btn = st.columns([3.5, 1.5])
        with col_hdr:
            st.markdown("### 🚀 NSE Intraday Stock Scanner")
            st.caption("Institutional Volume & Breakout Algorithm • Real-Time Intraday Trade Candidates")
        with col_btn:
            st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
            scan_now = st.button("🔍 Scan All NSE Stocks Now", type="primary", use_container_width=True, key="btn_simple_scan_now")

        # Scan NSE stocks on button click or load
        if scan_now or "simple_scanner_signals" not in st.session_state:
            with st.spinner("Scanning NSE stocks as per algorithm criteria..."):
                signals = run_stock_momentum_scanner(
                    universe=NSE_STOCK_UNIVERSE,
                    min_impulse=0.008,
                    min_value_cr=4.0,
                    rvv_threshold=10.0,
                    filter_52w_high=False
                )
                st.session_state["simple_scanner_signals"] = signals

        signals = st.session_state.get("simple_scanner_signals", [])

        if not signals:
            st.info("ℹ️ No stocks currently qualify for intraday trade open right now. The scanner is actively filtering for ₹4+ Cr institutional volume and breakout confirmation.")
        else:
            st.success(f"🎯 **{len(signals)} Actionable Stocks Ready for Intraday Trade Open Right Now:**")

            # ── Clean Table of Open Trades ──
            table_rows = []
            for s in signals:
                risk_pts = max(1.0, s.entry_price - s.stop_loss)
                tag_52w = "⭐ 52W Breakout" if s.fifty_two_week_break else "Standard Breakout"
                table_rows.append({
                    "Stock": s.stock,
                    "Action": "🟢 BUY",
                    "Entry (₹)": f"₹{s.entry_price:,.2f}",
                    "Stop Loss (₹)": f"₹{s.stop_loss:,.2f}",
                    "Target 1 (1:3 RR)": f"₹{s.target1:,.2f}",
                    "Target 2 (1:4 RR)": f"₹{s.target2:,.2f}",
                    "Risk (Pts)": f"{risk_pts:.1f} pts",
                    "Setup Type": tag_52w,
                    "Sector": s.sector
                })

            st.dataframe(
                pd.DataFrame(table_rows),
                use_container_width=True,
                hide_index=True,
                height=min(320, (len(table_rows) + 1) * 45)
            )




if __name__ == "__main__":
    main()
