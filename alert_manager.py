"""
alert_manager.py — Sound and Telegram Alerts for Trade Signals
Plays a beep when a new BUY or SELL signal fires.
Optionally sends a Telegram message.
"""

import time
import threading
import requests
from datetime import datetime
from typing import Optional

from config import (
    ENABLE_SOUND_ALERTS, ALERT_COOLDOWN_SECONDS,
    ENABLE_TELEGRAM, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
)


# ─── Sound Alert ──────────────────────────────────────────────────────────────

def _play_alert_sound(signal_type: str):
    """Play a Windows system beep. Works without any extra library."""
    try:
        import winsound
        if signal_type == "BUY":
            # Two rising beeps for BUY
            winsound.Beep(800, 200)
            time.sleep(0.05)
            winsound.Beep(1200, 300)
        elif signal_type == "SELL":
            # Two falling beeps for SELL
            winsound.Beep(1200, 200)
            time.sleep(0.05)
            winsound.Beep(600, 300)
        else:
            winsound.Beep(880, 150)
    except Exception:
        # Fallback: terminal bell
        print("\a")


# ─── Market Hours Guard ───────────────────────────────────────────────────────

def is_market_open() -> bool:
    from config import IST_TIMEZONE, MARKET_OPEN_HOUR, MARKET_OPEN_MIN, MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN
    import pytz
    IST = pytz.timezone(IST_TIMEZONE)
    now = datetime.now(IST)
    if now.weekday() in (5, 6):  # Saturday (5) / Sunday (6)
        return False
    open_time = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MIN, second=0)
    close_time = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MIN, second=0)
    return open_time <= now <= close_time


# ─── Telegram Alert ───────────────────────────────────────────────────────────

def get_telegram_creds() -> tuple[str, str, bool]:
    """Retrieve Telegram credentials from environment or Streamlit secrets."""
    token = TELEGRAM_BOT_TOKEN
    chat_id = TELEGRAM_CHAT_ID
    enabled = ENABLE_TELEGRAM

    # Check Streamlit secrets if available (for Cloud Deployment)
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            token = st.secrets.get("TELEGRAM_BOT_TOKEN", token)
            chat_id = st.secrets.get("TELEGRAM_CHAT_ID", chat_id)
            enabled = st.secrets.get("ENABLE_TELEGRAM", enabled)
    except Exception:
        pass

    return token, chat_id, enabled


def send_telegram_message(message: str, force: bool = False) -> bool:
    """Send a Telegram message via bot API."""
    if not force and not is_market_open():
        print("[AlertManager] [PAUSED] Market is closed (Weekend/Night). Suppressed Telegram message.")
        return False

    token, chat_id, enabled = get_telegram_creds()
    if not token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }, timeout=8)
        return resp.status_code == 200
    except Exception as e:
        print(f"[AlertManager] Telegram error: {e}")
        return False


def send_telegram_test_message() -> tuple[bool, str]:
    """Send a test message to verify Telegram bot setup."""
    token, chat_id, enabled = get_telegram_creds()
    if not token or not chat_id:
        return False, "Telegram Bot Token or Chat ID is missing. Please configure them in .env or Cloud Secrets."

    test_msg = (
        "🤖 <b>CRUDE MCX PRO TERMINAL — TELEGRAM CONNECTED!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ <b>Status:</b> Live Alert Stream Active\n"
        "⚡ <b>Engine:</b> Institutional MCX Crude Options\n"
        f"⏰ <b>Test Time:</b> {datetime.now().strftime('%H:%M:%S %d-%b-%Y')}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 You will now receive instant trade alerts with exact entry, stop loss, and targets on your phone!"
    )
    success = send_telegram_message(test_msg, force=True)
    if success:
        return True, "Telegram test message sent successfully! Check your Telegram app."
    else:
        return False, "Failed to send message. Please verify your Bot Token and Chat ID."


def _format_telegram_message(
    signal_type: str,
    confidence: str,
    entry: float,
    stop_loss: float,
    target1: float,
    target2: float,
    strategy_name: str = "🎯 RSI + MACD Confluence",
    contract_name: str = "CRUDEOIL ATM OPTION",
    entry_premium: float = 160.0,
    sl_premium: float = 135.0,
    t1_premium: float = 215.0,
    t2_premium: float = 247.5,
    risk_rs: float = 1250.0,
    t1_profit_rs: float = 2750.0,
    lots: int = 1,
    timestamp: str = "",
) -> str:
    is_buy = (signal_type == "BUY")
    emoji = "🟢" if is_buy else "🔴"
    action_header = "BUY CALL (CE)" if is_buy else "BUY PUT (PE)"

    # Dynamic commodity branding
    c_upper = contract_name.upper()
    if "GOLD" in c_upper:
        comm_icon = "🪙"
        comm_title = "GOLD MCX"
    elif "SILVER" in c_upper:
        comm_icon = "🥈"
        comm_title = "SILVER MCX"
    elif "NAT" in c_upper or "GAS" in c_upper:
        comm_icon = "🔥"
        comm_title = "NATGAS MCX"
    else:
        comm_icon = "🛢️"
        comm_title = "CRUDE MCX"

    return (
        f"{emoji} <b>{comm_title} ALERT: {action_header}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Strategy:</b> {strategy_name}\n"
        f"{comm_icon} <b>Contract:</b> {contract_name} ({lots} Lot)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Option Entry:</b> ₹{entry_premium:.2f} (Spot: ₹{entry:.0f})\n"
        f"🛑 <b>Stop Loss:</b>     ₹{sl_premium:.2f} (Risk: -₹{risk_rs:,.0f})\n"
        f"🎯 <b>Target 1:</b>       ₹{t1_premium:.2f} (+₹{t1_profit_rs:,.0f} Profit)\n"
        f"🚀 <b>Target 2:</b>       ₹{t2_premium:.2f} (Runner Target)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ <b>Time:</b> {timestamp} | <b>Confidence:</b> {confidence}\n"
        f"⚡ <i>Direct from Multi-Commodity Pro Terminal</i>"
    )


def send_tp_sl_alert(
    event_type: str,
    contract_name: str,
    pts_move: float,
    pnl_rs: float,
    exit_premium: float,
    lots: int = 1,
    timestamp: str = ""
) -> bool:
    """Sends Target 1, Target 2, and Stop Loss hit alerts to Telegram."""
    token, chat_id, enabled = get_telegram_creds()
    if not token or not chat_id:
        return False

    if not timestamp:
        timestamp = datetime.now().strftime("%H:%M:%S %d-%b-%Y")

    c_upper = contract_name.upper()
    if "GOLD" in c_upper:
        comm_icon = "🪙"
        comm_title = "GOLD MCX"
    elif "SILVER" in c_upper:
        comm_icon = "🥈"
        comm_title = "SILVER MCX"
    elif "NAT" in c_upper or "GAS" in c_upper:
        comm_icon = "🔥"
        comm_title = "NATGAS MCX"
    else:
        comm_icon = "🛢️"
        comm_title = "CRUDE MCX"

    if event_type == "TARGET1":
        msg = (
            f"🎯 <b>{comm_title} TARGET 1 HIT! (+{pts_move:.0f} PTS)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{comm_icon} <b>Contract:</b> {contract_name} ({lots} Lot)\n"
            f"💰 <b>Profit Booked:</b> +₹{pnl_rs:,.0f}\n"
            f"📍 <b>Option Value:</b> ₹{exit_premium:.2f}\n"
            f"🛡️ <b>Action:</b> Book Partial / Trail SL to Cost!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ <b>Time:</b> {timestamp}\n"
            f"⚡ <i>Multi-Commodity Pro Terminal</i>"
        )
    elif event_type == "TARGET2":
        msg = (
            f"🚀 <b>{comm_title} TARGET 2 (RUNNER) HIT! (+{pts_move:.0f} PTS)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{comm_icon} <b>Contract:</b> {contract_name} ({lots} Lot)\n"
            f"💰 <b>Total Profit:</b> +₹{pnl_rs:,.0f}\n"
            f"📍 <b>Final Option Value:</b> ₹{exit_premium:.2f}\n"
            f"🏁 <b>Action:</b> Full Target Met. Trade Closed!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ <b>Time:</b> {timestamp}\n"
            f"⚡ <i>Multi-Commodity Pro Terminal</i>"
        )
    else:  # STOP_LOSS
        msg = (
            f"🛑 <b>{comm_title} STOP LOSS HIT (-{abs(pts_move):.0f} PTS)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{comm_icon} <b>Contract:</b> {contract_name} ({lots} Lot)\n"
            f"🛡️ <b>Max Risk Limited:</b> -₹{abs(pnl_rs):,.0f}\n"
            f"📍 <b>Exit Value:</b> ₹{exit_premium:.2f}\n"
            f"⏹️ <b>Action:</b> Position Closed. Capital Protected.\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ <b>Time:</b> {timestamp}\n"
            f"⚡ <i>Multi-Commodity Pro Terminal</i>"
        )

    return send_telegram_message(msg)


# ─── Alert Manager ────────────────────────────────────────────────────────────

class AlertManager:
    """
    Manages signal alerts with per-asset cooldown to prevent duplicate/spam alerts.
    Thread-safe.
    """

    def __init__(self):
        self._last_alert_times: dict[str, float] = {}
        self._last_signal_signatures: dict[str, str] = {}
        self._last_candle_times: dict[str, str] = {}
        self._lock = threading.Lock()

    def _is_cooldown_active(self, comm_key: str, sig: str, candle_time: str = "") -> bool:
        clean_k = comm_key.upper().strip()
        last_t = self._last_alert_times.get(clean_k, 0.0)
        last_sig = self._last_signal_signatures.get(clean_k, "")
        last_candle = self._last_candle_times.get(clean_k, "")

        # 1. Never fire more than 1 entry alert on the exact same candle bar
        if candle_time and last_candle == candle_time:
            return True

        # 2. Strict 15-minute cooldown for the same asset to prevent rapid-fire duplicates
        elapsed = time.time() - last_t
        if elapsed < 900:  # 15 minutes
            return True

        # 3. If exact same signature, respect 30-minute cooldown
        if sig == last_sig and elapsed < 1800:
            return True

        return False

    def trigger(
        self,
        signal_type: str,
        confidence: str,
        entry: float,
        stop_loss: float,
        target1: float,
        target2: float,
        strategy_name: str = "🎯 RSI + MACD Confluence",
        contract_name: str = "CRUDEOIL ATM OPTION",
        entry_premium: float = 160.0,
        sl_premium: float = 135.0,
        t1_premium: float = 215.0,
        t2_premium: float = 247.5,
        risk_rs: float = 1250.0,
        t1_profit_rs: float = 2750.0,
        lots: int = 1,
        timestamp: str = "",
        commodity_key: str = "CRUDEOIL",
        candle_time: str = "",
        force: bool = False,
    ) -> bool:
        """
        Fire an alert for a new signal automatically. Returns True if alert was sent, False if throttled.
        """
        if signal_type == "NEUTRAL":
            return False

        # ⛔ STRICT MARKET HOURS GUARD: Never alert on weekends or outside market hours
        if not force and not is_market_open():
            print(f"[AlertManager] [PAUSED] Market Closed (Weekend/Night). Suppressed {signal_type} alert.")
            return False

        clean_k = commodity_key.upper().strip()
        sig_key = f"{clean_k}_{strategy_name}_{signal_type}_{contract_name}"

        with self._lock:
            if not force and self._is_cooldown_active(clean_k, sig_key, candle_time):
                return False
            self._last_alert_times[clean_k] = time.time()
            self._last_signal_signatures[clean_k] = sig_key
            if candle_time:
                self._last_candle_times[clean_k] = candle_time

        if not timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S %d-%b-%Y")

        # Sound alert (non-blocking)
        if ENABLE_SOUND_ALERTS:
            threading.Thread(target=_play_alert_sound, args=(signal_type,), daemon=True).start()

        # Telegram alert (non-blocking)
        token, chat_id, enabled = get_telegram_creds()
        if enabled or (token and chat_id):
            msg = _format_telegram_message(
                signal_type=signal_type,
                confidence=confidence,
                entry=entry,
                stop_loss=stop_loss,
                target1=target1,
                target2=target2,
                strategy_name=strategy_name,
                contract_name=contract_name,
                entry_premium=entry_premium,
                sl_premium=sl_premium,
                t1_premium=t1_premium,
                t2_premium=t2_premium,
                risk_rs=risk_rs,
                t1_profit_rs=t1_profit_rs,
                lots=lots,
                timestamp=timestamp
            )
            threading.Thread(target=send_telegram_message, args=(msg,), daemon=True).start()

        print(f"[AlertManager] [AUTO-FIRED] {signal_type} alert to Telegram at {timestamp} for {clean_k} ({contract_name})")
        return True

    def test_alert(self):
        """Play a test sound to verify audio is working."""
        threading.Thread(target=_play_alert_sound, args=("BUY",), daemon=True).start()


# ─── Singleton ────────────────────────────────────────────────────────────────
_alert_manager: Optional[AlertManager] = None

def get_alert_manager() -> AlertManager:
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
