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
    commodity_key: str = "CRUDEOIL",
    trade_id: str = "",
) -> str:
    is_buy = (signal_type == "BUY")
    emoji = "🟢" if is_buy else "🔴"
    action_header = "BUY CALL (CE)" if is_buy else "BUY PUT (PE)"

    from commodity_registry import get_commodity_spec
    spec = get_commodity_spec(commodity_key)

    if not trade_id:
        trade_id = f"#{spec.symbol_keyword}_{datetime.now().strftime('%y%m%d_%H%M')}"

    total_qty = spec.active_lot_size * lots
    t2_profit_rs = max(0.0, round((t2_premium - entry_premium) * total_qty, 2))
    sl_pts = abs(entry_premium - sl_premium) / max(0.01, spec.atm_delta)
    t1_pts = abs(t1_premium - entry_premium) / max(0.01, spec.atm_delta)
    t2_pts = abs(t2_premium - entry_premium) / max(0.01, spec.atm_delta)

    return (
        f"{emoji} <b>TRADE ALERT: {action_header}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{spec.icon} <b>ASSET:</b> <b>{spec.name.upper()}</b> (<code>{spec.segment}</code>)\n"
        f"📑 <b>CONTRACT:</b> <code>{contract_name}</code>\n"
        f"📦 <b>SIZE:</b> {lots} Lot ({total_qty} {spec.lot_unit})\n"
        f"🆔 <b>TRADE ID:</b> <code>{trade_id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<blockquote>"
        f"📍 <b>ENTRY PREMIUM:</b> <b>₹{entry_premium:.2f}</b> (Spot: ₹{entry:,.0f})\n"
        f"🛑 <b>STOP LOSS:</b>     <b>₹{sl_premium:.2f}</b> (-{sl_pts:.1f}p | Risk: -₹{risk_rs:,.0f})\n"
        f"🎯 <b>TARGET 1:</b>       <b>₹{t1_premium:.2f}</b> (+{t1_pts:.1f}p | +₹{t1_profit_rs:,.0f})\n"
        f"🚀 <b>TARGET 2:</b>       <b>₹{t2_premium:.2f}</b> (+{t2_pts:.1f}p | +₹{t2_profit_rs:,.0f})\n"
        f"</blockquote>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Setup:</b> {strategy_name}\n"
        f"⏰ <b>Time:</b> {timestamp} | <b>Conviction:</b> {confidence}\n"
        f"⚡ <i>Institutional Multi-Asset Pro Terminal</i>"
    )


def send_tp_sl_alert(
    event_type: str,
    contract_name: str,
    pts_move: float,
    pnl_rs: float,
    exit_premium: float,
    lots: int = 1,
    timestamp: str = "",
    commodity_key: str = "CRUDEOIL",
    trade_id: str = "",
    entry_premium: float = 0.0,
) -> bool:
    """Sends Target 1, Target 2, Stop Loss, and Trailing Breakeven hit alerts to Telegram."""
    token, chat_id, enabled = get_telegram_creds()
    if not token or not chat_id:
        return False

    clean_k = commodity_key.upper().strip()
    try:
        from strategy_presets import get_active_strategy_config
        active_cfg = get_active_strategy_config(clean_k)
        if not active_cfg.enabled:
            print(f"[AlertManager] [MUTED] Suppressed TP/SL alert for {clean_k} because asset is disabled.")
            return False
    except Exception:
        pass

    if not timestamp:
        timestamp = datetime.now().strftime("%H:%M:%S %d-%b-%Y")

    from commodity_registry import get_commodity_spec
    spec = get_commodity_spec(clean_k)
    trade_id_tag = f"🆔 <b>LINKED TRADE:</b> <code>{trade_id}</code>\n" if trade_id else ""

    if event_type == "TARGET1":
        msg = (
            f"🎯 <b>TARGET 1 ACHIEVED! (+{pts_move:.1f} PTS)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{spec.icon} <b>ASSET:</b> <b>{spec.name.upper()}</b>\n"
            f"📑 <b>CONTRACT:</b> <code>{contract_name}</code> ({lots} Lot)\n"
            f"{trade_id_tag}"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>"
            f"💰 <b>PROFIT SECURED:</b> <b>+₹{pnl_rs:,.0f}</b>\n"
            f"📍 <b>OPTION VALUE:</b> ₹{exit_premium:.2f}\n"
            f"🛡️ <b>ACTION:</b> Book 50% & Lock SL to Cost (₹{entry_premium:.2f})!\n"
            f"</blockquote>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ <b>Time:</b> {timestamp} | <b>Risk:</b> ZERO (Protected)\n"
            f"⚡ <i>Institutional Multi-Asset Pro Terminal</i>"
        )
    elif event_type == "TARGET2":
        msg = (
            f"🚀 <b>TARGET 2 (RUNNER) HIT! (+{pts_move:.1f} PTS)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{spec.icon} <b>ASSET:</b> <b>{spec.name.upper()}</b>\n"
            f"📑 <b>CONTRACT:</b> <code>{contract_name}</code> ({lots} Lot)\n"
            f"{trade_id_tag}"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>"
            f"💰 <b>TOTAL NET PROFIT:</b> <b>+₹{pnl_rs:,.0f}</b>\n"
            f"📍 <b>FINAL OPTION VALUE:</b> ₹{exit_premium:.2f}\n"
            f"🏁 <b>ACTION:</b> Full Target Met. Trade 100% Closed!\n"
            f"</blockquote>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ <b>Time:</b> {timestamp} | <b>Status:</b> COMPLETE\n"
            f"⚡ <i>Institutional Multi-Asset Pro Terminal</i>"
        )
    elif event_type == "TRAIL_COST_EXIT":
        msg = (
            f"🛡️ <b>RUNNER EXITED AT BREAKEVEN / COST</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{spec.icon} <b>ASSET:</b> <b>{spec.name.upper()}</b>\n"
            f"📑 <b>CONTRACT:</b> <code>{contract_name}</code> ({lots} Lot)\n"
            f"{trade_id_tag}"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>"
            f"💰 <b>T1 PROFIT PROTECTED!</b>\n"
            f"📍 <b>EXIT VALUE:</b> ₹{exit_premium:.2f} (Entry Cost)\n"
            f"🏁 <b>ACTION:</b> Position Closed at Breakeven. Capital 100% Safe.\n"
            f"</blockquote>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ <b>Time:</b> {timestamp} | <b>Status:</b> PROFIT PROTECTED\n"
            f"⚡ <i>Institutional Multi-Asset Pro Terminal</i>"
        )
    else:  # STOP_LOSS
        msg = (
            f"🛑 <b>STOP LOSS TRIGGERED (-{abs(pts_move):.1f} PTS)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{spec.icon} <b>ASSET:</b> <b>{spec.name.upper()}</b>\n"
            f"📑 <b>CONTRACT:</b> <code>{contract_name}</code> ({lots} Lot)\n"
            f"{trade_id_tag}"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>"
            f"🛡️ <b>MAX RISK LIMITED:</b> <b>-₹{abs(pnl_rs):,.0f}</b>\n"
            f"📍 <b>EXIT VALUE:</b> ₹{exit_premium:.2f}\n"
            f"⏹️ <b>ACTION:</b> Trade Closed. 15-Min Cool-Down Active.\n"
            f"</blockquote>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ <b>Time:</b> {timestamp} | <b>Status:</b> RISK CONTROLLED\n"
            f"⚡ <i>Institutional Multi-Asset Pro Terminal</i>"
        )
    return send_telegram_message(msg)


def send_nse_stock_alert(sig) -> bool:
    """Send real-time breakout alert for NSE Intraday Stock to Telegram."""
    token, chat_id, enabled = get_telegram_creds()
    if not token or not chat_id:
        return False

    import pytz
    from config import IST_TIMEZONE
    IST = pytz.timezone(IST_TIMEZONE)
    now_ist = datetime.now(IST).strftime("%H:%M:%S IST")

    risk_pts = max(0.1, sig.entry_price - sig.stop_loss)
    tag_52w = "⭐ 52-Week High Breakout" if sig.fifty_two_week_break else "Institutional Volume Breakout"
    entry_time_str = getattr(sig, "entry_timestamp", "") or getattr(sig, "time", "") or now_ist

    msg = (
        f"🚀 <b>NSE INTRADAY STOCK BREAKOUT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏛️ <b>STOCK:</b> <b>{sig.stock}</b> ({sig.sector})\n"
        f"🟢 <b>ACTION:</b> <b>INTRADAY BUY</b>\n"
        f"🏷️ <b>SETUP:</b> {tag_52w}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<blockquote>"
        f"📍 <b>ENTRY PRICE:</b>  <b>₹{sig.entry_price:,.2f}</b>\n"
        f"🛑 <b>STOP LOSS:</b>    <b>₹{sig.stop_loss:,.2f}</b> (-{risk_pts:.1f} pts)\n"
        f"🎯 <b>TARGET 1 (1:3):</b> <b>₹{sig.target1:,.2f}</b> (+{risk_pts*3:.1f} pts)\n"
        f"🚀 <b>TARGET 2 (1:4):</b> <b>₹{sig.target2:,.2f}</b> (+{risk_pts*4:.1f} pts)\n"
        f"</blockquote>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <b>INSTITUTIONAL METRICS:</b>\n"
        f"• <b>Volume Impulse:</b> ₹{sig.impulse_value_cr:.1f} Cr ({sig.rvv_multiple:.0f}x Median)\n"
        f"• <b>1-Min Move:</b> +{sig.impulse_move_pct:.2f}%\n"
        f"• <b>Breakout Time:</b> <code>{entry_time_str}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ <b>Alert Dispatched:</b> {now_ist}\n"
        f"⚡ <i>Institutional Multi-Asset Pro Terminal</i>"
    )
    return send_telegram_message(msg, force=True)


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
        trade_id: str = "",
        force: bool = False,
    ) -> bool:
        """
        Fire an alert for a new signal automatically. Returns True if alert was sent, False if throttled.
        """
        if signal_type == "NEUTRAL":
            return False

        clean_k = commodity_key.upper().strip()

        # ⛔ STRICT ACTIVE ASSET TOGGLE GUARD: Muted assets will NEVER send Telegram alerts
        try:
            from strategy_presets import get_active_strategy_config
            active_cfg = get_active_strategy_config(clean_k)
            if not force and not active_cfg.enabled:
                print(f"[AlertManager] [MUTED] Alert suppressed for {clean_k} because asset is disabled in settings.")
                return False
        except Exception:
            pass

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
                timestamp=timestamp,
                commodity_key=clean_k,
                trade_id=trade_id,
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
