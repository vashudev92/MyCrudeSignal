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
from alert_manager import get_alert_manager, send_tp_sl_alert

from commodity_registry import COMMODITY_REGISTRY, get_commodity_spec
from strategy_presets import get_active_strategy_config

IST = pytz.timezone(IST_TIMEZONE)

_scanner_thread: threading.Thread | None = None
_scanner_running = False
_active_trade_trackers: dict[str, dict] = {}
_post_loss_cooldowns: dict[str, float] = {}
_daily_trade_counts: dict[str, int] = {}
_daily_count_date: str = ""
_lock = threading.Lock()


def is_any_market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() in (5, 6):  # Saturday / Sunday
        return False
    # Overall trading window from 09:00 to 23:30 IST
    open_time = now.replace(hour=9, minute=0, second=0)
    close_time = now.replace(hour=23, minute=30, second=0)
    return open_time <= now <= close_time


def is_asset_market_open(spec) -> bool:
    now = datetime.now(IST)
    if now.weekday() in (5, 6):  # Saturday / Sunday
        return False
    if spec.category == "INDEX":
        # Equity market hours: 09:15 to 15:30 IST
        open_time = now.replace(hour=9, minute=15, second=0)
        close_time = now.replace(hour=15, minute=30, second=0)
    else:
        # MCX market hours: 09:00 to 23:30 IST
        open_time = now.replace(hour=9, minute=0, second=0)
        close_time = now.replace(hour=23, minute=30, second=0)
    return open_time <= now <= close_time


def _scanner_loop():
    global _scanner_running, _active_trade_trackers, _post_loss_cooldowns, _daily_trade_counts, _daily_count_date
    print("[BackgroundScanner] 🚀 Multi-Asset 24/7 Autonomous Background Scanner Daemon Started.")
    client = get_client()
    engine = SignalEngine()
    alert_mgr = get_alert_manager()

    commodities = list(COMMODITY_REGISTRY.keys())

    while _scanner_running:
        try:
            # ⛔ STRICT MARKET HOURS GUARD: Do NOT scan on weekends or outside trading hours
            if not is_any_market_open():
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
                now_dt = datetime.now(IST)
                today_str = now_dt.strftime("%Y-%m-%d")
                if _daily_count_date != today_str:
                    _daily_trade_counts.clear()
                    _daily_count_date = today_str

                is_us_prime = (16 <= now_dt.hour <= 22 or (now_dt.hour == 23 and now_dt.minute <= 30))
                is_morning_drive = ((now_dt.hour == 9 and now_dt.minute >= 15) or (now_dt.hour == 10) or (now_dt.hour == 11 and now_dt.minute <= 30))

                for comm_key in commodities:
                    spec = get_commodity_spec(comm_key)
                    cfg = get_active_strategy_config(comm_key)

                    # 1. Check if Telegram alerts are enabled for this specific asset
                    if not cfg.enabled:
                        continue

                    # 2. Check segment market hours (09:15-15:30 for NSE/BSE, 09:00-23:30 for MCX)
                    if not is_asset_market_open(spec):
                        continue

                    # 3. Check session window filter for this asset
                    if ("US Prime" in cfg.session_filter or "US High-Peak" in cfg.session_filter) and not is_us_prime:
                        continue
                    if "Morning Opening Drive" in cfg.session_filter and not is_morning_drive:
                        continue

                    # 4. Check daily trade count limit (prevent exceeding configured frequency)
                    if _daily_trade_counts.get(comm_key, 0) >= cfg.max_daily_trades:
                        continue

                    # 5. Check post-loss cooling period (15 minutes after Stop Loss)
                    if time.time() < _post_loss_cooldowns.get(comm_key, 0.0):
                        continue

                    try:
                        instrument_key = get_active_crude_instrument_key(token, commodity_key=comm_key)
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

                            # ── A. Monitor Active Trade for Target 1, Target 2, and Stop Loss Hits ──
                            if comm_key in _active_trade_trackers and _active_trade_trackers[comm_key] is not None:
                                tr = _active_trade_trackers[comm_key]
                                dir_mul = 1.0 if tr["direction"] == "BUY" else -1.0
                                pts_move = (ltp - tr["entry_spot"]) * dir_mul
                                cur_prem = max(spec.tick_size * 5, round(tr["entry_premium"] + (pts_move * spec.atm_delta), 2))
                                gross_rs = round((cur_prem - tr["entry_premium"]) * spec.active_lot_size * tr["lots"], 2)

                                # 1. Target 2 Hit (Runner Target Met)
                                if pts_move >= tr["t2_pts"]:
                                    send_tp_sl_alert(
                                        event_type="TARGET2",
                                        contract_name=tr["contract"],
                                        pts_move=pts_move,
                                        pnl_rs=gross_rs,
                                        exit_premium=cur_prem,
                                        lots=tr["lots"]
                                    )
                                    _active_trade_trackers[comm_key] = None

                                # 2. Target 1 Hit (Book Profit / Lock Breakeven)
                                elif pts_move >= tr["t1_pts"] and not tr.get("t1_alerted", False):
                                    send_tp_sl_alert(
                                        event_type="TARGET1",
                                        contract_name=tr["contract"],
                                        pts_move=pts_move,
                                        pnl_rs=gross_rs,
                                        exit_premium=cur_prem,
                                        lots=tr["lots"]
                                    )
                                    tr["t1_alerted"] = True

                                # 3. Stop Loss Hit
                                elif pts_move <= -tr["sl_pts"]:
                                    send_tp_sl_alert(
                                        event_type="STOP_LOSS",
                                        contract_name=tr["contract"],
                                        pts_move=pts_move,
                                        pnl_rs=gross_rs,
                                        exit_premium=cur_prem,
                                        lots=tr["lots"]
                                    )
                                    _active_trade_trackers[comm_key] = None
                                    _post_loss_cooldowns[comm_key] = time.time() + 900  # 15 min cooling period after SL

                            # ── B. Scan for New Trade Entry Signal (If No Active Trade) ──
                            else:
                                signal = engine.generate_signal(
                                    indicators=indicators,
                                    strategy_model=cfg.strategy_model,
                                    news_flag="NEUTRAL",
                                    current_price=ltp,
                                    sl_pts=cfg.sl_pts,
                                    t1_rr=cfg.t1_rr,
                                    t2_rr=cfg.t2_rr,
                                    market_regime=cfg.market_regime,
                                    trailing_mode=cfg.trailing_mode,
                                    commodity_key=comm_key,
                                )

                                if signal.signal != SignalType.NEUTRAL:
                                    candle_ts = str(df_candles["date"].iloc[-1]) if ("date" in df_candles and not df_candles.empty) else ""
                                    fired = alert_mgr.trigger(
                                        signal_type=signal.signal.value,
                                        confidence=signal.confidence.value,
                                        entry=signal.entry_price,
                                        stop_loss=signal.option_stop_loss,
                                        target1=signal.option_target1,
                                        target2=signal.option_target2,
                                        strategy_name=f"{spec.icon} {cfg.title}",
                                        contract_name=signal.option_contract,
                                        entry_premium=signal.option_buy_price,
                                        sl_premium=signal.option_stop_loss,
                                        t1_premium=signal.option_target1,
                                        t2_premium=signal.option_target2,
                                        risk_rs=signal.option_lot_risk_rs,
                                        t1_profit_rs=signal.option_lot_target1_rs,
                                        lots=cfg.lots,
                                        timestamp=signal.timestamp,
                                        commodity_key=comm_key,
                                        candle_time=candle_ts,
                                    )
                                    if fired:
                                        _daily_trade_counts[comm_key] = _daily_trade_counts.get(comm_key, 0) + 1
                                        _active_trade_trackers[comm_key] = {
                                            "direction": signal.signal.value,
                                            "contract": signal.option_contract,
                                            "entry_spot": signal.entry_price,
                                            "entry_premium": signal.option_buy_price,
                                            "sl_pts": cfg.sl_pts,
                                            "t1_pts": cfg.sl_pts * cfg.t1_rr,
                                            "t2_pts": cfg.sl_pts * cfg.t2_rr,
                                            "lots": cfg.lots,
                                            "t1_alerted": False
                                        }
                    except Exception as e:
                        print(f"[BackgroundScanner] Scan error for {comm_key}: {e}")

        except Exception as outer_e:
            print(f"[BackgroundScanner] Daemon error: {outer_e}")

        time.sleep(20)  # Scan every 20 seconds


def start_background_scanner():
    """Start the 24/7 background scanner daemon thread if not already running."""
    global _scanner_thread, _scanner_running
    with _lock:
        if _scanner_running and _scanner_thread is not None and _scanner_thread.is_alive():
            return
        _scanner_running = True
        _scanner_thread = threading.Thread(target=_scanner_loop, daemon=True, name="MultiCommodityScannerDaemon")
        _scanner_thread.start()
        print("[BackgroundScanner] Multi-Commodity thread launched successfully.")

