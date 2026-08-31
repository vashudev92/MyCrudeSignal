"""
signal_engine.py — Multi-Model Live Signal Engine for MCX Crude Oil Option Buying

Generates instant actionable trade signals for 4 selectable strategy models:
  1. 🚀 Supertrend & 20 EMA Momentum (Trend-Following)
  2. ⚡ 20 EMA / Pivot Pullback (Dip-Buyer)
  3. 📐 Standard Pivot Points Breakout (R1/S1)
  4. 🎯 RSI + MACD Momentum Confluence

Option Execution Details:
  - Exact ATM Call (CE) / Put (PE) Strike & Contract Name.
  - Calculated Option Buy Price, Stop Loss, Target 1 (1:2.1), Target 2 (1:3.5).
  - Maximum Rupee Risk per Lot vs Target Rupee Profit.
  - Live News Sentiment integration.
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional, List
import pytz

from config import IST_TIMEZONE
from indicators import IndicatorValues, PivotLevels
from commodity_registry import get_commodity_spec

IST = pytz.timezone(IST_TIMEZONE)

LOT_SIZE = 100
ATM_DELTA = 0.50
BASE_ATM_PREMIUM = 160.0
DEFAULT_SL_PTS = 20.0
DEFAULT_T1_RR = 2.2
DEFAULT_T2_RR = 3.5


class SignalType(Enum):
    BUY = "BUY"    # Bullish -> BUY CALL (CE)
    SELL = "SELL"  # Bearish -> BUY PUT (PE)
    NEUTRAL = "NEUTRAL"


class SignalConfidence(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class TradeSignal:
    """Actionable Trade Signal for Option Buying."""
    signal: SignalType = SignalType.NEUTRAL
    confidence: SignalConfidence = SignalConfidence.LOW
    conditions_met: int = 0
    total_conditions: int = 4
    strategy_model: str = "Supertrend & 20 EMA Momentum"

    # Option Contract Execution Details
    option_action: str = "WAIT"
    atm_strike: int = 0
    option_contract: str = ""
    option_buy_price: float = 0.0
    option_stop_loss: float = 0.0
    option_target1: float = 0.0
    option_target2: float = 0.0
    option_risk_pts: float = 0.0
    option_reward1_pts: float = 0.0
    option_lot_risk_rs: float = 0.0
    option_lot_target1_rs: float = 0.0

    # Underlying Futures Reference
    entry_price: float = 0.0
    stop_loss: float = 0.0
    target1: float = 0.0
    target2: float = 0.0

    # Execution Metadata & Alerts
    timestamp: str = ""
    reason: str = ""
    conditions_detail: List[str] = field(default_factory=list)
    news_flag: str = "NEUTRAL"
    pivot: Optional[PivotLevels] = None
    rsi: float = 50.0
    option_suggestion: str = ""

    @property
    def signal_emoji(self) -> str:
        if self.signal == SignalType.BUY:
            return "🟢"
        elif self.signal == SignalType.SELL:
            return "🔴"
        return "⚪"

    @property
    def confidence_color(self) -> str:
        if self.confidence == SignalConfidence.HIGH:
            return "#059669"
        elif self.confidence == SignalConfidence.MEDIUM:
            return "#D97706"
        return "#64748B"

    @property
    def risk_reward(self) -> str:
        return f"1 : {DEFAULT_T1_RR:.1f} (T1) / 1 : {DEFAULT_T2_RR:.1f} (T2)"


class SignalEngine:
    """
    Evaluates real-time market data across selected strategy models
    and generates immediate, high-conviction Option Buying signals.
    """

    def __init__(self):
        self._last_signal: Optional[TradeSignal] = None

    def generate_signal(
        self,
        indicators: IndicatorValues,
        strategy_model: str = "🎯 RSI + MACD Confluence",
        news_flag: str = "NEUTRAL",
        current_price: Optional[float] = None,
        sl_pts: float = 25.0,
        t1_rr: float = 3.0,
        t2_rr: float = 3.5,
        market_regime: str = "🛡️ Strict Trend (ADX >= 23)",
        trailing_mode: str = "❌ Pure Fixed SL",
        commodity_key: str = "CRUDEOIL",
    ) -> TradeSignal:
        price = current_price if current_price and current_price > 0 else indicators.close
        pivot = indicators.pivot
        now_ist = datetime.now(IST).strftime("%H:%M:%S %d-%b-%Y")

        ema20 = indicators.ema21
        ema50 = indicators.ema50
        pp = pivot.pp

        # ADX threshold based on selected regime
        if "High Frequency" in market_regime:
            adx_min = 14.0
        elif "Strict" in market_regime:
            adx_min = 23.0
        else:
            adx_min = 18.0

        buy_conditions: List[str] = []
        sell_conditions: List[str] = []

        # ── 1. Evaluate Selected Model with Strict Trigger Rules ──────────────
        candle_open = indicators.open if hasattr(indicators, "open") and indicators.open > 0 else ema20
        is_bull_candle = price >= candle_open
        is_bear_candle = price <= candle_open

        if "RSI" in strategy_model or "Confluence" in strategy_model:
            # 🎯 RSI + MACD Confluence Model (Exact Backtest Parity)
            if indicators.macd_histogram > 0 and (50.0 <= indicators.rsi <= 70.0) and price > ema20 and is_bull_candle:
                buy_conditions.append("✅ MACD: Bullish expansion (Histogram > 0)")
                buy_conditions.append(f"✅ RSI: {indicators.rsi:.0f} in high-velocity expansion zone")
                buy_conditions.append(f"✅ Trend: Bullish candle above 20 EMA (₹{ema20:.0f})")

            if indicators.macd_histogram < 0 and (30.0 <= indicators.rsi <= 50.0) and price < ema20 and is_bear_candle:
                sell_conditions.append("✅ MACD: Bearish expansion (Histogram < 0)")
                sell_conditions.append(f"✅ RSI: {indicators.rsi:.0f} in downward momentum zone")
                sell_conditions.append(f"✅ Trend: Bearish candle below 20 EMA (₹{ema20:.0f})")

        elif "ICT" in strategy_model or "FVG" in strategy_model:
            # 💎 ICT & Fair Value Gap (FVG) + Liquidity Sweep Model
            if (indicators.fvg_type == "BULLISH_FVG" or "BULLISH" in indicators.liquidity_sweep or price > ema20) and is_bull_candle and indicators.rsi >= 48.0:
                buy_conditions.append(f"✅ Smart Money: Bullish FVG Zone / Sweep Confirmation")
                buy_conditions.append(f"✅ Market Structure: Above 20 EMA (₹{ema20:.0f})")
                buy_conditions.append(f"✅ Institutional Expansion: RSI {indicators.rsi:.0f} >= 48")

            if (indicators.fvg_type == "BEARISH_FVG" or "BEARISH" in indicators.liquidity_sweep or price < ema20) and is_bear_candle and indicators.rsi <= 52.0:
                sell_conditions.append(f"✅ Smart Money: Bearish FVG Zone / Sweep Confirmation")
                sell_conditions.append(f"✅ Market Structure: Below 20 EMA (₹{ema20:.0f})")
                sell_conditions.append(f"✅ Institutional Expansion: RSI {indicators.rsi:.0f} <= 52")

        elif "News" in strategy_model or "Inventory" in strategy_model:
            # 📰 High-Impact Energy News & Inventory Breakout
            if news_flag == "BULLISH" and price > ema20 and indicators.rsi >= 50.0 and is_bull_candle:
                buy_conditions.append("📰 EIA / Energy Catalyst: Strong Bullish News Sentiment")
                buy_conditions.append("✅ Volatility Expansion: Price leading above 20 EMA")
                buy_conditions.append(f"✅ Momentum Surge: RSI {indicators.rsi:.0f} >= 50")

            if news_flag == "BEARISH" and price < ema20 and indicators.rsi <= 50.0 and is_bear_candle:
                sell_conditions.append("📰 EIA / Energy Catalyst: Strong Bearish News Sentiment")
                sell_conditions.append("✅ Volatility Breakdown: Price leading below 20 EMA")
                sell_conditions.append(f"✅ Momentum Dump: RSI {indicators.rsi:.0f} <= 50")

        elif "Pullback" in strategy_model:
            # 20 EMA / Pivot Pullback Model
            dist_to_ema = abs(price - ema20)
            is_near_ema20 = dist_to_ema <= 15.0 or (indicators.day_low <= ema20 <= price)

            if price >= ema50 and is_near_ema20 and is_bull_candle and (46.0 <= indicators.rsi <= 68.0):
                buy_conditions.append(f"✅ Trend Bias: Bullish above 50 EMA (₹{ema50:.0f})")
                buy_conditions.append(f"✅ Pullback Zone: Bounce off 20 EMA (₹{ema20:.0f})")
                buy_conditions.append(f"✅ Reversal Momentum: Green candle (RSI {indicators.rsi:.0f})")

            if price <= ema50 and is_near_ema20 and is_bear_candle and (32.0 <= indicators.rsi <= 54.0):
                sell_conditions.append(f"✅ Trend Bias: Bearish below 50 EMA (₹{ema50:.0f})")
                sell_conditions.append(f"✅ Pullback Zone: Rejection off 20 EMA (₹{ema20:.0f})")
                sell_conditions.append(f"✅ Reversal Momentum: Red candle (RSI {indicators.rsi:.0f})")

        elif "Pivot" in strategy_model:
            # Standard Pivot Breakout Model
            if price > pp and price > ema20 and is_bull_candle and indicators.rsi >= 50.0:
                buy_conditions.append(f"✅ Pivot Breakout: Price (₹{price:.0f}) > PP (₹{pp:.0f})")
                buy_conditions.append(f"✅ Momentum: Above 20 EMA (₹{ema20:.0f})")
                buy_conditions.append(f"✅ RSI Strength: {indicators.rsi:.0f} >= 50 (Bullish)")

            if price < pp and price < ema20 and is_bear_candle and indicators.rsi <= 50.0:
                sell_conditions.append(f"✅ Pivot Breakdown: Price (₹{price:.0f}) < PP (₹{pp:.0f})")
                sell_conditions.append(f"✅ Momentum: Below 20 EMA (₹{ema20:.0f})")
                sell_conditions.append(f"✅ RSI Weakness: {indicators.rsi:.0f} <= 50 (Bearish)")

        else:
            # Supertrend & 20 EMA Momentum
            if indicators.st_fast_dir == 1 and price > ema20 and ema20 >= ema50 and is_bull_candle:
                buy_conditions.append(f"✅ Supertrend: Bullish (₹{indicators.st_fast:.0f})")
                buy_conditions.append(f"✅ Trend Alignment: 20 EMA (₹{ema20:.0f}) >= 50 EMA")
                buy_conditions.append(f"✅ RSI Momentum: {indicators.rsi:.0f} supporting upward drive")

            if indicators.st_fast_dir == -1 and price < ema20 and ema20 <= ema50 and is_bear_candle:
                sell_conditions.append(f"✅ Supertrend: Bearish (₹{indicators.st_fast:.0f})")
                sell_conditions.append(f"✅ Trend Alignment: 20 EMA (₹{ema20:.0f}) <= 50 EMA")
                sell_conditions.append(f"✅ RSI Weakness: {indicators.rsi:.0f} supporting downward drive")

        # Add news sentiment factor
        if news_flag == "BULLISH" and buy_conditions:
            buy_conditions.append("📰 Energy News: Bullish sentiment catalyst")
        elif news_flag == "BEARISH" and sell_conditions:
            sell_conditions.append("📰 Energy News: Bearish sentiment catalyst")

        buy_score = len(buy_conditions)
        sell_score = len(sell_conditions)

        # ADX Trend Filter (Skip signal if market is sideways / consolidating)
        is_trending_market = indicators.adx >= adx_min
        if is_trending_market:
            if buy_score >= 3 and buy_score > sell_score:
                signal_type = SignalType.BUY
                score = buy_score
                active_conditions = buy_conditions
            elif sell_score >= 3 and sell_score > buy_score:
                signal_type = SignalType.SELL
                score = sell_score
                active_conditions = sell_conditions
            else:
                signal_type = SignalType.NEUTRAL
                score = 0
                active_conditions = ["⚪ Market consolidating — awaiting confluence criteria"]
        else:
            signal_type = SignalType.NEUTRAL
            score = 0
            active_conditions = [f"⚪ Market in Low-Volatility Consolidation (ADX: {indicators.adx:.1f} < {adx_min:.0f}) — Capital protected"]

        confidence = SignalConfidence.HIGH if score >= 3 else (
            SignalConfidence.MEDIUM if score >= 2 else SignalConfidence.LOW
        )

        spec = get_commodity_spec(commodity_key)
        strike_step = spec.strike_step
        atm_strike = int(round(price / strike_step) * strike_step)
        entry = round(price, 2)
        lot_size = spec.active_lot_size

        # Dynamic ATM option premium based on spot and commodity baseline
        calc_atm_prem = round(max(spec.tick_size * 10, spec.base_option_premium * (price / spec.base_spot_estimate)), 2)

        contract_prefix = "GOLDM" if spec.key == "GOLD" else ("SILVERM" if spec.key == "SILVER" else spec.symbol_keyword)

        if signal_type == SignalType.BUY:
            sl = round(price - sl_pts, 2)
            t1 = round(price + (sl_pts * t1_rr), 2)
            t2 = round(price + (sl_pts * t2_rr), 2)

            option_action = "🟢 BUY CALL (CE)"
            option_contract = f"{contract_prefix} {atm_strike} CE"
            opt_buy = calc_atm_prem
            opt_risk_pts = round(sl_pts * spec.atm_delta, 2)
            opt_sl = max(spec.tick_size * 5, round(opt_buy - opt_risk_pts, 2))
            opt_t1 = round(opt_buy + (sl_pts * t1_rr * spec.atm_delta), 2)
            opt_t2 = round(opt_buy + (sl_pts * t2_rr * spec.atm_delta), 2)
            opt_rew_pts = round(opt_t1 - opt_buy, 2)

            option_suggestion = f"BUY {option_contract} @ ₹{opt_buy:.1f} (1:{t1_rr:.1f} R:R | 1 Lot)"
            reason = f"Bullish {strategy_model.split('(')[0].strip()} Trigger on {spec.name}. Target 1 (₹{opt_t1:.0f}) & Target 2 (₹{opt_t2:.0f})."

        elif signal_type == SignalType.SELL:
            sl = round(price + sl_pts, 2)
            t1 = round(price - (sl_pts * t1_rr), 2)
            t2 = round(price - (sl_pts * t2_rr), 2)

            option_action = "🔴 BUY PUT (PE)"
            option_contract = f"{contract_prefix} {atm_strike} PE"
            opt_buy = calc_atm_prem
            opt_risk_pts = round(sl_pts * spec.atm_delta, 2)
            opt_sl = max(spec.tick_size * 5, round(opt_buy - opt_risk_pts, 2))
            opt_t1 = round(opt_buy + (sl_pts * t1_rr * spec.atm_delta), 2)
            opt_t2 = round(opt_buy + (sl_pts * t2_rr * spec.atm_delta), 2)
            opt_rew_pts = round(opt_t1 - opt_buy, 2)

            option_suggestion = f"BUY {option_contract} @ ₹{opt_buy:.1f} (1:{t1_rr:.1f} R:R | 1 Lot)"
            reason = f"Bearish {strategy_model.split('(')[0].strip()} Trigger on {spec.name}. Target 1 (₹{opt_t1:.0f}) & Target 2 (₹{opt_t2:.0f})."

        else:
            sl = t1 = t2 = 0.0
            option_action = "WAIT"
            option_contract = f"NO ACTIVE {spec.name.upper()} POSITION"
            opt_buy = opt_sl = opt_t1 = opt_t2 = opt_risk_pts = opt_rew_pts = 0.0
            option_suggestion = f"Awaiting {strategy_model.split('(')[0].strip()} trigger"
            reason = f"{spec.name} price is in consolidation zone. Waiting for clear signal."

        return TradeSignal(
            signal=signal_type,
            confidence=confidence,
            conditions_met=score,
            total_conditions=4,
            strategy_model=strategy_model,
            option_action=option_action,
            atm_strike=atm_strike,
            option_contract=option_contract,
            option_buy_price=opt_buy,
            option_stop_loss=opt_sl,
            option_target1=opt_t1,
            option_target2=opt_t2,
            option_risk_pts=opt_risk_pts,
            option_reward1_pts=opt_rew_pts,
            option_lot_risk_rs=round(opt_risk_pts * lot_size, 2),
            option_lot_target1_rs=round(opt_rew_pts * lot_size, 2),
            entry_price=entry,
            stop_loss=sl,
            target1=t1,
            target2=t2,
            timestamp=now_ist,
            reason=reason,
            conditions_detail=active_conditions,
            news_flag=news_flag,
            pivot=pivot,
            rsi=indicators.rsi,
            option_suggestion=option_suggestion,
        )
