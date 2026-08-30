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

        # ── 1. Evaluate Selected Model ─────────────────────────────────────────
        if "RSI" in strategy_model or "Confluence" in strategy_model:
            # 🎯 RSI + MACD Confluence Model
            if indicators.macd_line > indicators.macd_signal:
                buy_conditions.append("✅ MACD: Bullish crossover (Line > Signal)")
            if 50.0 <= indicators.rsi <= 70.0:
                buy_conditions.append(f"✅ RSI: {indicators.rsi:.0f} in high-velocity expansion zone")
            if price > ema20:
                buy_conditions.append(f"✅ Trend: Price above 20 EMA (₹{ema20:.0f})")

            if indicators.macd_line < indicators.macd_signal:
                sell_conditions.append("✅ MACD: Bearish crossover (Line < Signal)")
            if 30.0 <= indicators.rsi <= 50.0:
                sell_conditions.append(f"✅ RSI: {indicators.rsi:.0f} in downward momentum zone")
            if price < ema20:
                sell_conditions.append(f"✅ Trend: Price below 20 EMA (₹{ema20:.0f})")

        elif "ICT" in strategy_model or "FVG" in strategy_model:
            # 💎 ICT & Fair Value Gap (FVG) + Liquidity Sweep Model
            if indicators.fvg_type == "BULLISH_FVG" or "BULLISH" in indicators.liquidity_sweep:
                buy_conditions.append(f"✅ Smart Money: Bullish FVG Zone (₹{indicators.fvg_bottom:.0f} - ₹{indicators.fvg_top:.0f})")
            if price >= ema20:
                buy_conditions.append(f"✅ Market Structure Shift (MSS): Above 20 EMA (₹{ema20:.0f})")
            if indicators.rsi >= 46.0:
                buy_conditions.append(f"✅ Institutional Expansion: RSI {indicators.rsi:.0f} >= 46")

            if indicators.fvg_type == "BEARISH_FVG" or "BEARISH" in indicators.liquidity_sweep:
                sell_conditions.append(f"✅ Smart Money: Bearish FVG Zone (₹{indicators.fvg_bottom:.0f} - ₹{indicators.fvg_top:.0f})")
            if price <= ema20:
                sell_conditions.append(f"✅ Market Structure Shift (MSS): Below 20 EMA (₹{ema20:.0f})")
            if indicators.rsi <= 54.0:
                sell_conditions.append(f"✅ Institutional Expansion: RSI {indicators.rsi:.0f} <= 54")

        elif "News" in strategy_model or "Inventory" in strategy_model:
            # 📰 High-Impact Energy News & Inventory Breakout
            if news_flag == "BULLISH":
                buy_conditions.append("📰 EIA / Energy Catalyst: Strong Bullish News Sentiment")
            if price > indicators.ema9 and price > ema20:
                buy_conditions.append("✅ Volatility Expansion: Price leading above 9 & 20 EMA")
            if indicators.rsi >= 50.0:
                buy_conditions.append(f"✅ Momentum Surge: RSI {indicators.rsi:.0f} > 50")

            if news_flag == "BEARISH":
                sell_conditions.append("📰 EIA / Energy Catalyst: Strong Bearish News Sentiment")
            if price < indicators.ema9 and price < ema20:
                sell_conditions.append("✅ Volatility Breakdown: Price leading below 9 & 20 EMA")
            if indicators.rsi <= 50.0:
                sell_conditions.append(f"✅ Momentum Dump: RSI {indicators.rsi:.0f} < 50")

        elif "Pullback" in strategy_model:
            # 20 EMA / Pivot Pullback Model
            dist_to_ema = abs(price - ema20)
            is_near_ema20 = dist_to_ema <= 15.0 or (indicators.day_low <= ema20 <= price)

            if price >= pp or price >= ema50:
                buy_conditions.append(f"✅ Trend Bias: Bullish (Price ₹{price:.0f} >= PP ₹{pp:.0f})")
            if is_near_ema20:
                buy_conditions.append(f"✅ Pullback Zone: Price touching 20 EMA (₹{ema20:.0f})")
            if indicators.close >= indicators.ema9:
                buy_conditions.append("✅ Momentum: Green reversal candle above 9 EMA")
            if 40.0 <= indicators.rsi <= 70.0:
                buy_conditions.append(f"✅ RSI ({indicators.rsi:.0f}) in active expansion zone")

            if price <= pp or price <= ema50:
                sell_conditions.append(f"✅ Trend Bias: Bearish (Price ₹{price:.0f} <= PP ₹{pp:.0f})")
            if is_near_ema20:
                sell_conditions.append(f"✅ Pullback Zone: Price rallying to 20 EMA (₹{ema20:.0f})")
            if indicators.close <= indicators.ema9:
                sell_conditions.append("✅ Momentum: Red reversal candle below 9 EMA")
            if 30.0 <= indicators.rsi <= 60.0:
                sell_conditions.append(f"✅ RSI ({indicators.rsi:.0f}) in active bearish expansion zone")

        elif "Pivot" in strategy_model:
            # Standard Pivot Breakout Model
            if price > pp:
                buy_conditions.append(f"✅ Pivot Breakout: Price (₹{price:.0f}) > PP (₹{pp:.0f})")
            if price > ema20:
                buy_conditions.append(f"✅ Momentum: Above 20 EMA (₹{ema20:.0f})")
            if indicators.rsi >= 48.0:
                buy_conditions.append(f"✅ RSI Strength: {indicators.rsi:.0f} >= 48 (Bullish)")

            if price < pp:
                sell_conditions.append(f"✅ Pivot Breakdown: Price (₹{price:.0f}) < PP (₹{pp:.0f})")
            if price < ema20:
                sell_conditions.append(f"✅ Momentum: Below 20 EMA (₹{ema20:.0f})")
            if indicators.rsi <= 52.0:
                sell_conditions.append(f"✅ RSI Weakness: {indicators.rsi:.0f} <= 52 (Bearish)")

        elif "RSI" in strategy_model:
            # RSI + MACD Confluence Model
            if indicators.macd_line > indicators.macd_signal:
                buy_conditions.append("✅ MACD: Bullish crossover (Line > Signal)")
            if 50.0 <= indicators.rsi <= 70.0:
                buy_conditions.append(f"✅ RSI: {indicators.rsi:.0f} in high-velocity expansion zone")
            if price > ema20:
                buy_conditions.append(f"✅ Trend: Price above 20 EMA (₹{ema20:.0f})")

            if indicators.macd_line < indicators.macd_signal:
                sell_conditions.append("✅ MACD: Bearish crossover (Line < Signal)")
            if 30.0 <= indicators.rsi <= 50.0:
                sell_conditions.append(f"✅ RSI: {indicators.rsi:.0f} in downward momentum zone")
            if price < ema20:
                sell_conditions.append(f"✅ Trend: Price below 20 EMA (₹{ema20:.0f})")

        else:
            # Supertrend & 20 EMA Momentum
            if price > ema50 and price > ema20:
                buy_conditions.append(f"✅ Trend Alignment: Price above 20 EMA (₹{ema20:.0f}) & 50 EMA (₹{ema50:.0f})")
            if indicators.close >= indicators.ema9:
                buy_conditions.append("✅ Bullish Price Action: Candle closing above 9 EMA")
            if indicators.rsi >= 45.0:
                buy_conditions.append(f"✅ RSI Momentum: {indicators.rsi:.0f} supporting upward drive")

            if price < ema50 and price < ema20:
                sell_conditions.append(f"✅ Trend Alignment: Price below 20 EMA (₹{ema20:.0f}) & 50 EMA (₹{ema50:.0f})")
            if indicators.close <= indicators.ema9:
                sell_conditions.append("✅ Bearish Price Action: Candle closing below 9 EMA")
            if indicators.rsi <= 55.0:
                sell_conditions.append(f"✅ RSI Weakness: {indicators.rsi:.0f} supporting downward drive")

        # Add news sentiment factor
        if news_flag == "BULLISH":
            buy_conditions.append("📰 Energy News: Bullish sentiment catalyst")
        elif news_flag == "BEARISH":
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
