"""
background_scanner.py — 24/7 Autonomous Background Market Scanner & Telegram Alert Dispatcher

Runs continuously in a separate daemon thread.
Monitors MCX Crude Oil live feed, computes RSI + MACD / Supertrend indicators,
and automatically sends instant trade alerts to Telegram WITHOUT requiring any user button clicks!
"""

import time
import threading
from datetime import datetime, date
import pytz
import pandas as pd

from config import (
    IST_TIMEZONE, MARKET_OPEN_HOUR, MARKET_OPEN_MIN, MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN,
    UPSTOX_ACCESS_TOKEN
)
from upstox_client import get_client
from instrument_finder import get_active_crude_instrument_key
from indicators import calculate_pivot_points, compute_indicators
from signal_engine import SignalEngine, SignalType
from alert_manager import get_alert_manager

IST = pytz.timezone(IST_TIMEZONE)

_scanner_thread: threading.Thread | None = None
_scanner_running = False
_lock = threading.Lock()


def is_market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() in (5, 6):  # Saturday / Sunday
        return False
    open_time = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MIN, second=0)
    close_time = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MIN, second=0)
    return open_time <= now <= close_time


def _scanner_loop():
    global _scanner_running
    print("[BackgroundScanner] 🚀 24/7 Autonomous Background Scanner Daemon Started.")
    client = get_client()
    engine = SignalEngine()
    alert_mgr = get_alert_manager()

    while _scanner_running:
        try:
            # ⛔ STRICT MARKET HOURS GUARD: Do NOT scan on weekends or outside MCX trading hours
            if not is_market_open():
                time.sleep(60)
                continue

            token = UPSTOX_ACCESS_TOKEN
            try:
                import streamlit as st
                if hasattr(st, "secrets") and "UPSTOX_ACCESS_TOKEN" in st.secrets:
                    token = st.secrets["UPSTOX_ACCESS_TOKEN"]
            except Exception:
                pass

            if token:
                try:
                    instrument_key = get_active_crude_instrument_key(token)
                    df_candles = client.get_intraday_candles(instrument_key, interval="30minute")
                    if df_candles.empty or len(df_candles) < 20:
                        df_candles = client.get_historical_candles(instrument_key, interval="30minute", days_back=4)
                    
                    live_quote = client.get_live_quote(instrument_key)
                    prev_day_ohlc = client.get_previous_day_ohlc(instrument_key)

                    if not df_candles.empty and len(df_candles) >= 20:
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

                        # Evaluate Setup 1: RSI + MACD Confluence
                        signal = engine.generate_signal(
                            indicators=indicators,
                            strategy_model="🎯 RSI + MACD Confluence",
                            news_flag="NEUTRAL",
                            current_price=ltp,
                            sl_pts=25.0,
                            t1_rr=2.2,
                            t2_rr=3.5,
                            market_regime="🎯 Balanced Quality (ADX >= 18)",
                            trailing_mode="❌ Pure Fixed SL"
                        )

                        if signal.signal != SignalType.NEUTRAL:
                            alert_mgr.trigger(
                                signal_type=signal.signal.value,
                                confidence=signal.confidence.value,
                                entry=signal.entry_price,
                                stop_loss=signal.option_stop_loss,
                                target1=signal.option_target1,
                                target2=signal.option_target2,
                                strategy_name="🎯 Setup 1: RSI + MACD Confluence",
                                contract_name=signal.option_contract,
                                entry_premium=signal.option_buy_price,
                                sl_premium=signal.option_stop_loss,
                                t1_premium=signal.option_target1,
                                t2_premium=signal.option_target2,
                                risk_rs=signal.option_lot_risk_rs,
                                t1_profit_rs=signal.option_lot_target1_rs,
                                lots=1,
                                timestamp=signal.timestamp,
                            )
                except Exception as e:
                    print(f"[BackgroundScanner] Scan error: {e}")

        except Exception as outer_e:
            print(f"[BackgroundScanner] Daemon error: {outer_e}")

        time.sleep(15)  # Scan every 15 seconds


def start_background_scanner():
    """Start the 24/7 background scanner daemon thread if not already running."""
    global _scanner_thread, _scanner_running
    with _lock:
        if _scanner_running and _scanner_thread is not None and _scanner_thread.is_alive():
            return
        _scanner_running = True
        _scanner_thread = threading.Thread(target=_scanner_loop, daemon=True, name="CrudeScannerDaemon")
        _scanner_thread.start()
        print("[BackgroundScanner] Thread launched successfully.")
