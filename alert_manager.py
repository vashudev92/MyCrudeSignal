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


def send_telegram_message(message: str) -> bool:
    """Send a Telegram message via bot API."""
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
    success = send_telegram_message(test_msg)
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

    return (
        f"{emoji} <b>CRUDE MCX ALERT: {action_header}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Strategy:</b> {strategy_name}\n"
        f"🛢️ <b>Contract:</b> {contract_name} ({lots} Lot)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Option Entry:</b> ₹{entry_premium:.2f} (Spot: ₹{entry:.0f})\n"
        f"🛑 <b>Stop Loss:</b>     ₹{sl_premium:.2f} (Risk: -₹{risk_rs:,.0f})\n"
        f"🎯 <b>Target 1:</b>       ₹{t1_premium:.2f} (+₹{t1_profit_rs:,.0f} Profit)\n"
        f"🚀 <b>Target 2:</b>       ₹{t2_premium:.2f} (Runner Target)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ <b>Time:</b> {timestamp} | <b>Confidence:</b> {confidence}\n"
        f"⚡ <i>Direct from Crude MCX Terminal</i>"
    )


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


# ─── Alert Manager ────────────────────────────────────────────────────────────

class AlertManager:
    """
    Manages signal alerts with cooldown to prevent spam.
    Thread-safe.
    """

    def __init__(self):
        self._last_alert_time: float = 0.0
        self._last_signal_signature: Optional[str] = None
        self._lock = threading.Lock()

    def _is_cooldown_active(self, sig: str) -> bool:
        # If signal signature changed (e.g. new contract or new direction), allow immediately
        if sig != self._last_signal_signature:
            return False
        # If exact same signal signature, respect 10-minute cooldown
        return (time.time() - self._last_alert_time) < 600

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
        force: bool = False,
    ) -> bool:
        """
        Fire an alert for a new signal automatically. Returns True if alert was sent, False if throttled.
        """
        if signal_type == "NEUTRAL":
            return False

        # ⛔ STRICT MARKET HOURS GUARD: Never alert on weekends or outside market hours
        if not force and not is_market_open():
            print(f"[AlertManager] ⏸️ Market Closed (Weekend/Night). Suppressed {signal_type} alert.")
            return False

        sig_key = f"{strategy_name}_{signal_type}_{contract_name}"

        with self._lock:
            if not force and self._is_cooldown_active(sig_key):
                return False
            self._last_alert_time = time.time()
            self._last_signal_signature = sig_key

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

        print(f"[AlertManager] 🚀 AUTO-FIRED {signal_type} alert to Telegram at {timestamp} for {contract_name}")
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
