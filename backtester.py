"""
backtester.py — Multi-Strategy Quantitative Option Buying Backtester & Customizer

Supports 4 Switchable Strategy Models:
  1. Supertrend & 20 EMA Momentum Trend-Following
  2. 20 EMA / Pivot Pullback (Dip-Buyer)
  3. Standard Pivot Points (CPR / PP Breakout & Retest)
  4. RSI + MACD Momentum Confluence

With Full User Customization:
  - Custom Stop Loss (15 to 40 pts)
  - Custom Target 1 & Target 2 Risk-to-Reward (1:1.5 to 1:4.0)
  - Trailing Breakeven Stop Loss (Locks cost at +18 pts)
  - Session Timing Filter (US Session 16:30-22:30 vs Full Day 09:00-23:30)
  - Max Trades Per Day Intraday Circuit Breaker (1, 2, 3, or Unlimited)
  - Real MCX Option Brokerage, CTT, Exchange Fees & GST Deductions.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
import pandas as pd
import numpy as np
from typing import Optional, List, Dict

from config import (
    EMA_FAST, EMA_MID, EMA_SLOW,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    RSI_PERIOD, IST_TIMEZONE
)
from indicators import calculate_pivot_points, PivotLevels, _supertrend
from commodity_registry import get_commodity_spec, calculate_commodity_option_charges

LOT_SIZE = 100
ATM_DELTA = 0.50
BASE_ATM_PREMIUM = 160.0


def calculate_mcx_option_charges(buy_premium: float, exit_premium: float, commodity_key: str = "CRUDEOIL", lots: int = 1) -> Dict[str, float]:
    return calculate_commodity_option_charges(buy_premium, exit_premium, commodity_key=commodity_key, lots=lots)


@dataclass
class BacktestTrade:
    """Single Option Buying Trade Record."""
    trade_id: int
    entry_time: datetime
    exit_time: Optional[datetime]
    trade_date: str
    direction: str  # "BUY" (Call) or "SELL" (Put)
    option_action: str
    strike: int
    option_type: str
    option_contract: str
    
    # Option Premium Levels (₹)
    option_buy_price: float = BASE_ATM_PREMIUM
    option_exit_price: float = BASE_ATM_PREMIUM
    option_sl_premium: float = 151.0
    option_t1_premium: float = 179.0
    option_t2_premium: float = 191.5
    option_pnl_pts: float = 0.0

    # P&L and Charges
    gross_option_pnl_rs: float = 0.0
    total_charges_rs: float = 0.0
    net_option_pnl_rs: float = 0.0

    # Underlying Futures Reference
    entry_price: float = 0.0
    exit_price: float = 0.0
    stop_loss: float = 0.0
    target1: float = 0.0
    target2: float = 0.0
    pts_pnl: float = 0.0
    futures_pnl_rs: float = 0.0

    # Trade Execution Details
    exit_reason: str = "OPEN"
    status: str = "OPEN"
    holding_candles: int = 0
    sl_moved_to_cost: bool = False
    hit_target1: bool = False
    signal_confidence: str = "HIGH"
    strategy_used: str = "SUPERTREND"


@dataclass
class BacktestReport:
    """Complete Strategy Audit Report."""
    trades: List[BacktestTrade] = field(default_factory=list)
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    scratch_trades: int = 0
    win_rate: float = 0.0

    initial_capital_rs: float = 100000.0
    ending_capital_rs: float = 100000.0
    roi_percent: float = 0.0

    total_gross_pnl_rs: float = 0.0
    total_charges_rs: float = 0.0
    total_net_pnl_rs: float = 0.0
    total_futures_pnl_rs: float = 0.0
    total_pts_pnl: float = 0.0
    avg_trade_net_pnl_rs: float = 0.0

    max_win_rs: float = 0.0
    max_loss_rs: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_rs: float = 0.0

    total_days: int = 0
    profitable_days: int = 0
    losing_days: int = 0
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
    daily_summary: pd.DataFrame = field(default_factory=pd.DataFrame)


class CrudeBacktester:
    """
    Modular Option Buying Backtester with User-Selected Strategies
    and Custom Risk-Reward Parameters for Multi-Commodity Assets.
    """

    def __init__(
        self,
        df_candles: pd.DataFrame,
        df_daily: Optional[pd.DataFrame] = None,
        commodity_key: str = "CRUDEOIL"
    ):
        self.commodity_key = commodity_key
        self.spec = get_commodity_spec(commodity_key)
        self.df_candles = df_candles.copy().sort_values("datetime").reset_index(drop=True)
        self.df_daily = df_daily.copy().sort_values("datetime").reset_index(drop=True) if df_daily is not None else None

    def _prepare_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        close = df["close"]
        high = df["high"]
        low = df["low"]

        df["ema9"] = close.ewm(span=EMA_FAST, adjust=False).mean()
        df["ema20"] = close.ewm(span=EMA_MID, adjust=False).mean()
        df["ema50"] = close.ewm(span=EMA_SLOW, adjust=False).mean()

        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / RSI_PERIOD, min_periods=RSI_PERIOD, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / RSI_PERIOD, min_periods=RSI_PERIOD, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["rsi"] = (100 - (100 / (1 + rs))).fillna(50)

        # MACD (12, 26, 9)
        ema12 = close.ewm(span=MACD_FAST, adjust=False).mean()
        ema26 = close.ewm(span=MACD_SLOW, adjust=False).mean()
        df["macd_line"] = ema12 - ema26
        df["macd_signal"] = df["macd_line"].ewm(span=MACD_SIGNAL, adjust=False).mean()
        df["macd_hist"] = df["macd_line"] - df["macd_signal"]

        # ATR & ADX (14) Trend Strength Filter
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df["atr"] = tr.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean().fillna(20.0)

        up_move = high - high.shift()
        down_move = low.shift() - low
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        plus_di = 100 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1 / 14, min_periods=14, adjust=False).mean() / df["atr"])
        minus_di = 100 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1 / 14, min_periods=14, adjust=False).mean() / df["atr"])
        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
        df["adx"] = dx.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean().fillna(20.0)

        # Supertrend (period=10, multiplier=3)
        hl2 = (high + low) / 2
        upper_band = hl2 + (3.0 * df["atr"])
        lower_band = hl2 - (3.0 * df["atr"])
        supertrend = pd.Series(index=df.index, dtype=float)
        in_uptrend = True

        for idx in range(len(df)):
            if idx == 0:
                supertrend.iloc[idx] = lower_band.iloc[idx]
                continue
            c = close.iloc[idx]
            prev_st = supertrend.iloc[idx - 1]
            if in_uptrend:
                if c < lower_band.iloc[idx]:
                    in_uptrend = False
                    supertrend.iloc[idx] = upper_band.iloc[idx]
                else:
                    supertrend.iloc[idx] = max(lower_band.iloc[idx], prev_st)
            else:
                if c > upper_band.iloc[idx]:
                    in_uptrend = True
                    supertrend.iloc[idx] = lower_band.iloc[idx]
                else:
                    supertrend.iloc[idx] = min(upper_band.iloc[idx], prev_st)
        df["supertrend"] = supertrend
        df["st_direction"] = np.where(close >= df["supertrend"], "BULLISH", "BEARISH")

        # 🚀 4-Condition Strategy Indicators: Dual Supertrend (11,2 & 7,3) and Volume 20-SMA
        st_fast_s, dir_fast_s = _supertrend(df, period=11, multiplier=2.0)
        st_slow_s, dir_slow_s = _supertrend(df, period=7, multiplier=3.0)
        df["st_fast"] = st_fast_s
        df["dir_fast"] = dir_fast_s
        df["st_slow"] = st_slow_s
        df["dir_slow"] = dir_slow_s
        df["vol_sma20"] = df["volume"].rolling(20).mean().fillna(df["volume"])

        return df

    def _get_daily_trend_and_pivots(self, trade_date: date) -> tuple[str, PivotLevels]:
        if self.df_daily is not None and not self.df_daily.empty:
            prev_days = self.df_daily[self.df_daily["datetime"].dt.date < trade_date]
            if not prev_days.empty:
                last_day = prev_days.iloc[-1]
                daily_close = float(last_day["close"])
                daily_ema20 = float(prev_days["close"].tail(20).mean()) if len(prev_days) >= 20 else daily_close
                daily_trend = "BULLISH" if daily_close >= daily_ema20 else "BEARISH"
                
                pivots = calculate_pivot_points(
                    prev_high=float(last_day["high"]),
                    prev_low=float(last_day["low"]),
                    prev_close=daily_close,
                    date=str(trade_date)
                )
                return daily_trend, pivots

        prev_intraday = self.df_candles[self.df_candles["datetime"].dt.date < trade_date]
        if not prev_intraday.empty:
            last_date = prev_intraday["datetime"].dt.date.max()
            day_group = prev_intraday[prev_intraday["datetime"].dt.date == last_date]
            pivots = calculate_pivot_points(
                prev_high=float(day_group["high"].max()),
                prev_low=float(day_group["low"].min()),
                prev_close=float(day_group["close"].iloc[-1]),
                date=str(trade_date)
            )
            return "BULLISH", pivots

        return "BULLISH", calculate_pivot_points(6500, 6300, 6400, date=str(trade_date))

    def run(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        strategy_model: str = "Supertrend & 20 EMA Momentum",
        sl_pts: float = 20.0,
        t1_rr: float = 1.8,
        t2_rr: float = 3.5,
        use_breakeven: bool = True,
        be_trigger_pts: float = 20.0,
        session_filter: str = "US Prime Session (16:30 - 22:30 IST)",
        market_regime: str = "🎯 Balanced Quality (ADX >= 18)",
        max_daily_trades: int = 1,
        lots: int = 1,
        initial_capital: float = 100000.0,
    ) -> BacktestReport:
        if self.df_candles.empty or len(self.df_candles) < 10:
            return BacktestReport(initial_capital_rs=initial_capital, ending_capital_rs=initial_capital)

        df_all = self._prepare_indicators(self.df_candles)
        df_all["date"] = df_all["datetime"].dt.date

        if start_date is not None:
            df = df_all[df_all["date"] >= start_date].copy()
        else:
            df = df_all.copy()

        if end_date is not None:
            df = df[df["date"] <= end_date].copy()

        if df.empty:
            return BacktestReport(initial_capital_rs=initial_capital, ending_capital_rs=initial_capital)

        trades: List[BacktestTrade] = []
        active_trade: Optional[BacktestTrade] = None
        trade_counter = 0

        # ADX threshold based on trader regime selection
        if "High Frequency" in market_regime:
            adx_min = 14.0
        elif "Strict" in market_regime:
            adx_min = 23.0
        else:
            adx_min = 18.0

        unique_dates = sorted(df["date"].unique())

        for curr_date in unique_dates:
            day_df = df[df["date"] == curr_date].reset_index(drop=True)
            daily_trend, pivot = self._get_daily_trend_and_pivots(curr_date)
            day_trades_count = 0

            for i in range(1, len(day_df)):
                row = day_df.iloc[i]
                prev_row = day_df.iloc[i - 1]

                current_time = row["datetime"]
                price = float(row["close"])
                high = float(row["high"])
                low = float(row["low"])
                open_p = float(row["open"])
                ema20 = float(row["ema20"])
                ema50 = float(row["ema50"])
                adx = float(row["adx"])
                atr = float(row["atr"])

                is_eod = (i == len(day_df) - 1) or (current_time.hour == 23 and current_time.minute >= 15)

                # ── 1. Manage Active Trade Exits & Trailing Breakeven ──────────
                if active_trade is not None:
                    active_trade.holding_candles += 1
                    closed = False

                    if active_trade.direction == "BUY":
                        # Trailing Breakeven Logic (Protect capital at 1:1 RR)
                        if use_breakeven and not active_trade.sl_moved_to_cost:
                            if high >= active_trade.entry_price + be_trigger_pts:
                                active_trade.sl_moved_to_cost = True
                                active_trade.stop_loss = active_trade.entry_price

                        if high >= active_trade.target2:
                            active_trade.exit_price = active_trade.target2
                            active_trade.exit_time = current_time
                            active_trade.exit_reason = "🎯 TARGET 2 (1:3.5) HIT"
                            active_trade.status = "WIN"
                            closed = True
                        elif high >= active_trade.target1 and not active_trade.hit_target1:
                            active_trade.hit_target1 = True
                            active_trade.exit_price = active_trade.target1
                            active_trade.exit_time = current_time
                            active_trade.exit_reason = f"🎯 TARGET 1 (1:{t1_rr:.1f}) HIT"
                            active_trade.status = "WIN"
                            closed = True
                        elif low <= active_trade.stop_loss:
                            active_trade.exit_price = active_trade.stop_loss
                            active_trade.exit_time = current_time
                            active_trade.exit_reason = "🛡️ BREAKEVEN EXIT" if active_trade.sl_moved_to_cost else "🛑 STOP LOSS HIT"
                            active_trade.status = "SCRATCH" if active_trade.sl_moved_to_cost else "LOSS"
                            closed = True
                        elif is_eod:
                            active_trade.exit_price = price
                            active_trade.exit_time = current_time
                            active_trade.exit_reason = "⏰ EOD SQUARE-OFF"
                            active_trade.status = "WIN" if price > active_trade.entry_price else ("LOSS" if price < active_trade.entry_price else "SCRATCH")
                            closed = True

                    elif active_trade.direction == "SELL":
                        if use_breakeven and not active_trade.sl_moved_to_cost:
                            if low <= active_trade.entry_price - be_trigger_pts:
                                active_trade.sl_moved_to_cost = True
                                active_trade.stop_loss = active_trade.entry_price

                        if low <= active_trade.target2:
                            active_trade.exit_price = active_trade.target2
                            active_trade.exit_time = current_time
                            active_trade.exit_reason = "🎯 TARGET 2 (1:3.5) HIT"
                            active_trade.status = "WIN"
                            closed = True
                        elif low <= active_trade.target1 and not active_trade.hit_target1:
                            active_trade.hit_target1 = True
                            active_trade.exit_price = active_trade.target1
                            active_trade.exit_time = current_time
                            active_trade.exit_reason = f"🎯 TARGET 1 (1:{t1_rr:.1f}) HIT"
                            active_trade.status = "WIN"
                            closed = True
                        elif high >= active_trade.stop_loss:
                            active_trade.exit_price = active_trade.stop_loss
                            active_trade.exit_time = current_time
                            active_trade.exit_reason = "🛡️ BREAKEVEN EXIT" if active_trade.sl_moved_to_cost else "🛑 STOP LOSS HIT"
                            active_trade.status = "SCRATCH" if active_trade.sl_moved_to_cost else "LOSS"
                            closed = True
                        elif is_eod:
                            active_trade.exit_price = price
                            active_trade.exit_time = current_time
                            active_trade.exit_reason = "⏰ EOD SQUARE-OFF"
                            active_trade.status = "WIN" if price < active_trade.entry_price else ("LOSS" if price > active_trade.entry_price else "SCRATCH")
                            closed = True

                    if closed:
                        pts = (active_trade.exit_price - active_trade.entry_price) if active_trade.direction == "BUY" else (active_trade.entry_price - active_trade.exit_price)
                        active_trade.pts_pnl = round(pts, 2)
                        active_trade.option_pnl_pts = round(pts * self.spec.atm_delta, 2)
                        lot_size = self.spec.active_lot_size
                        active_trade.gross_option_pnl_rs = round(active_trade.option_pnl_pts * lot_size * lots, 2)
                        active_trade.futures_pnl_rs = round(pts * lot_size * lots, 2)
                        active_trade.option_exit_price = max(self.spec.tick_size * 5, round(active_trade.option_buy_price + active_trade.option_pnl_pts, 2))

                        chg = calculate_commodity_option_charges(active_trade.option_buy_price, active_trade.option_exit_price, commodity_key=self.commodity_key, lots=lots)
                        active_trade.total_charges_rs = chg["total_charges"]
                        active_trade.net_option_pnl_rs = round(active_trade.gross_option_pnl_rs - active_trade.total_charges_rs, 2)

                        trades.append(active_trade)
                        day_trades_count += 1
                        active_trade = None

                # ── 2. Evaluate Strategy Models ───────────────────────────────
                if active_trade is not None or day_trades_count >= max_daily_trades or i >= len(day_df) - 1:
                    continue

                is_us_prime = (16 <= current_time.hour <= 22 or (current_time.hour == 23 and current_time.minute <= 30))
                is_morning_drive = ((current_time.hour == 9 and current_time.minute >= 15) or current_time.hour == 10 or (current_time.hour == 11 and current_time.minute <= 30))

                if ("US Prime" in session_filter or "US High-Peak" in session_filter) and not is_us_prime:
                    continue
                if "Morning Opening Drive" in session_filter and not is_morning_drive:
                    continue

                # 🛑 CHOP / CONSOLIDATION FILTER: Skip entering if market is flat/sideways
                if adx < adx_min:
                    continue

                trigger_buy = False
                trigger_sell = False

                # ── MODEL 1: Supertrend & 20 EMA Momentum ─────────────────────
                if "Supertrend" in strategy_model:
                    if row["st_direction"] == "BULLISH" and price > ema20 and ema20 >= ema50:
                        if prev_row["st_direction"] == "BEARISH" or prev_row["close"] <= prev_row["ema20"] + 3.0 or (price - open_p) >= (0.35 * atr):
                            trigger_buy = True
                    elif row["st_direction"] == "BEARISH" and price < ema20 and ema20 <= ema50:
                        if prev_row["st_direction"] == "BULLISH" or prev_row["close"] >= prev_row["ema20"] - 3.0 or (open_p - price) >= (0.35 * atr):
                            trigger_sell = True

                # ── MODEL 2: 20 EMA / Pivot Pullback (Dip-Buyer) ──────────────
                elif "Pullback" in strategy_model:
                    if price >= ema50 and (prev_row["low"] <= prev_row["ema20"] + 8.0 or low <= ema20 + 4.0) and price > open_p and (46.0 <= float(row["rsi"]) <= 68.0):
                        trigger_buy = True
                    elif price <= ema50 and (prev_row["high"] >= prev_row["ema20"] - 8.0 or high >= ema20 - 4.0) and price < open_p and (32.0 <= float(row["rsi"]) <= 54.0):
                        trigger_sell = True

                # ── MODEL 3: 💎 ICT & Fair Value Gap (FVG) + Liquidity Sweep ──
                elif "ICT" in strategy_model or "FVG" in strategy_model:
                    # Check swing sweep & displacement
                    low_sweep = (low <= prev_row["low"] - 3.0 and price > prev_row["low"])
                    high_sweep = (high >= prev_row["high"] + 3.0 and price < prev_row["high"])
                    
                    if (low_sweep or (price > ema20 and prev_row["close"] <= ema20)) and price > open_p and (price - open_p) >= 0.30 * atr:
                        trigger_buy = True
                    elif (high_sweep or (price < ema20 and prev_row["close"] >= ema20)) and price < open_p and (open_p - price) >= 0.30 * atr:
                        trigger_sell = True

                # ── MODEL 4: 📰 High-Impact Energy News & Inventory Breakout ──
                elif "News" in strategy_model or "Inventory" in strategy_model:
                    if (price - open_p) >= 0.45 * atr and price > ema20 and float(row["rsi"]) >= 50.0:
                        trigger_buy = True
                    elif (open_p - price) >= 0.45 * atr and price < ema20 and float(row["rsi"]) <= 50.0:
                        trigger_sell = True

                # ── MODEL 5: Standard Pivot Breakout (PP Action) ──────────────
                elif "Pivot" in strategy_model:
                    if price > pivot.pp and price > ema20 and price > open_p and (float(row["rsi"]) >= 48.0):
                        trigger_buy = True
                    elif price < pivot.pp and price < ema20 and price < open_p and (float(row["rsi"]) <= 52.0):
                        trigger_sell = True

                # ── MODEL 7: RSI + MACD Momentum Confluence ───────────────────
                else:
                    if float(row["macd_hist"]) > 0 and (50.0 <= float(row["rsi"]) <= 70.0) and price > ema20 and price > open_p:
                        trigger_buy = True
                    elif float(row["macd_hist"]) < 0 and (30.0 <= float(row["rsi"]) <= 50.0) and price < ema20 and price < open_p:
                        trigger_sell = True

                strike_step = self.spec.strike_step
                contract_prefix = "GOLDM" if self.spec.key == "GOLD" else ("SILVERM" if self.spec.key == "SILVER" else self.spec.symbol_keyword)
                calc_opt_prem = round(max(self.spec.tick_size * 10, self.spec.base_option_premium * (price / self.spec.base_spot_estimate)), 2)

                if trigger_buy:
                    trade_counter += 1
                    atm_strike = int(round(price / strike_step) * strike_step)
                    sl = round(price - sl_pts, 2)
                    t1 = round(price + (sl_pts * t1_rr), 2)
                    t2 = round(price + (sl_pts * t2_rr), 2)

                    opt_buy = calc_opt_prem
                    opt_sl = max(self.spec.tick_size * 5, round(opt_buy - (sl_pts * self.spec.atm_delta), 2))
                    opt_t1 = round(opt_buy + (sl_pts * t1_rr * self.spec.atm_delta), 2)
                    opt_t2 = round(opt_buy + (sl_pts * t2_rr * self.spec.atm_delta), 2)

                    active_trade = BacktestTrade(
                        trade_id=trade_counter,
                        entry_time=current_time,
                        exit_time=None,
                        trade_date=str(curr_date),
                        direction="BUY",
                        option_action="🟢 BUY CALL (CE)",
                        strike=atm_strike,
                        option_type="CE",
                        option_contract=f"{contract_prefix} {atm_strike} CE",
                        option_buy_price=opt_buy,
                        option_exit_price=opt_buy,
                        option_sl_premium=opt_sl,
                        option_t1_premium=opt_t1,
                        option_t2_premium=opt_t2,
                        option_pnl_pts=0.0,
                        gross_option_pnl_rs=0.0,
                        total_charges_rs=0.0,
                        net_option_pnl_rs=0.0,
                        entry_price=round(price, 2),
                        exit_price=0.0,
                        stop_loss=sl,
                        target1=t1,
                        target2=t2,
                        pts_pnl=0.0,
                        futures_pnl_rs=0.0,
                        exit_reason="OPEN",
                        status="OPEN",
                        signal_confidence="HIGH",
                        strategy_used=strategy_model
                    )

                elif trigger_sell:
                    trade_counter += 1
                    atm_strike = int(round(price / strike_step) * strike_step)
                    sl = round(price + sl_pts, 2)
                    t1 = round(price - (sl_pts * t1_rr), 2)
                    t2 = round(price - (sl_pts * t2_rr), 2)

                    opt_buy = calc_opt_prem
                    opt_sl = max(self.spec.tick_size * 5, round(opt_buy - (sl_pts * self.spec.atm_delta), 2))
                    opt_t1 = round(opt_buy + (sl_pts * t1_rr * self.spec.atm_delta), 2)
                    opt_t2 = round(opt_buy + (sl_pts * t2_rr * self.spec.atm_delta), 2)

                    active_trade = BacktestTrade(
                        trade_id=trade_counter,
                        entry_time=current_time,
                        exit_time=None,
                        trade_date=str(curr_date),
                        direction="SELL",
                        option_action="🔴 BUY PUT (PE)",
                        strike=atm_strike,
                        option_type="PE",
                        option_contract=f"{contract_prefix} {atm_strike} PE",
                        option_buy_price=opt_buy,
                        option_exit_price=opt_buy,
                        option_sl_premium=opt_sl,
                        option_t1_premium=opt_t1,
                        option_t2_premium=opt_t2,
                        option_pnl_pts=0.0,
                        gross_option_pnl_rs=0.0,
                        total_charges_rs=0.0,
                        net_option_pnl_rs=0.0,
                        entry_price=round(price, 2),
                        exit_price=0.0,
                        stop_loss=sl,
                        target1=t1,
                        target2=t2,
                        pts_pnl=0.0,
                        futures_pnl_rs=0.0,
                        exit_reason="OPEN",
                        status="OPEN",
                        signal_confidence="HIGH",
                        strategy_used=strategy_model
                    )

        if active_trade is not None:
            last_p = float(df["close"].iloc[-1])
            pts = (last_p - active_trade.entry_price) if active_trade.direction == "BUY" else (active_trade.entry_price - last_p)
            active_trade.exit_price = last_p
            active_trade.exit_time = df["datetime"].iloc[-1]
            active_trade.exit_reason = "⏰ SESSION CLOSE"
            active_trade.status = "WIN" if pts > 0 else ("LOSS" if pts < 0 else "SCRATCH")
            active_trade.pts_pnl = round(pts, 2)
            active_trade.option_pnl_pts = round(pts * self.spec.atm_delta, 2)
            lot_size = self.spec.active_lot_size
            active_trade.gross_option_pnl_rs = round(active_trade.option_pnl_pts * lot_size * lots, 2)
            active_trade.futures_pnl_rs = round(pts * lot_size * lots, 2)
            active_trade.option_exit_price = max(self.spec.tick_size * 5, round(active_trade.option_buy_price + active_trade.option_pnl_pts, 2))

            chg = calculate_commodity_option_charges(active_trade.option_buy_price, active_trade.option_exit_price, commodity_key=self.commodity_key, lots=lots)
            active_trade.total_charges_rs = chg["total_charges"]
            active_trade.net_option_pnl_rs = round(active_trade.gross_option_pnl_rs - active_trade.total_charges_rs, 2)
            trades.append(active_trade)

        total_trades = len(trades)
        if total_trades == 0:
            return BacktestReport(initial_capital_rs=initial_capital, ending_capital_rs=initial_capital)

        wins = sum(1 for t in trades if t.status == "WIN")
        losses = sum(1 for t in trades if t.status == "LOSS")
        scratches = sum(1 for t in trades if t.status == "SCRATCH")
        win_rate = round((wins / total_trades) * 100.0, 1)

        total_gross_pnl = sum(t.gross_option_pnl_rs for t in trades)
        total_charges = sum(t.total_charges_rs for t in trades)
        total_net_pnl = sum(t.net_option_pnl_rs for t in trades)
        total_fut_pnl = sum(t.futures_pnl_rs for t in trades)
        total_pts = sum(t.pts_pnl for t in trades)

        ending_capital = round(initial_capital + total_net_pnl, 2)
        roi_percent = round((total_net_pnl / initial_capital) * 100.0, 2) if initial_capital > 0 else 0.0
        avg_net_pnl = round(total_net_pnl / total_trades, 2)

        win_pnls = [t.net_option_pnl_rs for t in trades if t.status == "WIN"]
        loss_pnls = [t.net_option_pnl_rs for t in trades if t.status == "LOSS"]

        max_win = max(win_pnls) if win_pnls else 0.0
        max_loss = min(loss_pnls) if loss_pnls else 0.0

        gross_profit = sum(win_pnls)
        gross_loss = abs(sum(loss_pnls))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.9 if gross_profit > 0 else 0.0)

        cum_net_pnl = 0.0
        peak = 0.0
        max_dd = 0.0
        equity_records = []

        for t in trades:
            cum_net_pnl += t.net_option_pnl_rs
            if cum_net_pnl > peak:
                peak = cum_net_pnl
            dd = peak - cum_net_pnl
            if dd > max_dd:
                max_dd = dd

            equity_records.append({
                "Trade": f"#{t.trade_id:02d}",
                "Time": t.exit_time or t.entry_time,
                "Trade_Net_PnL": t.net_option_pnl_rs,
                "Cumulative_Net_PnL": round(cum_net_pnl, 2),
                "Capital_Balance": round(initial_capital + cum_net_pnl, 2),
                "Drawdown_Rs": round(dd, 2)
            })

        df_equity = pd.DataFrame(equity_records)

        day_records = []
        for d in unique_dates:
            d_str = str(d)
            d_trades = [t for t in trades if t.trade_date == d_str]
            if not d_trades:
                continue
            
            d_wins = sum(1 for t in d_trades if t.status == "WIN")
            d_losses = sum(1 for t in d_trades if t.status == "LOSS")
            d_gross_pnl = sum(t.gross_option_pnl_rs for t in d_trades)
            d_charges = sum(t.total_charges_rs for t in d_trades)
            d_net_pnl = sum(t.net_option_pnl_rs for t in d_trades)
            d_fut_pnl = sum(t.futures_pnl_rs for t in d_trades)
            d_pts = sum(t.pts_pnl for t in d_trades)
            d_wr = round((d_wins / len(d_trades)) * 100, 1) if d_trades else 0.0

            calls_bought = sum(1 for t in d_trades if t.direction == "BUY")
            puts_bought = sum(1 for t in d_trades if t.direction == "SELL")

            day_records.append({
                "Date": d_str,
                "Weekday": d.strftime("%A"),
                "Trades": len(d_trades),
                "Calls (CE)": calls_bought,
                "Puts (PE)": puts_bought,
                "Wins": d_wins,
                "Losses": d_losses,
                "Win Rate (%)": d_wr,
                "Gross P&L (₹)": round(d_gross_pnl, 2),
                "Taxes & Brokerage (₹)": round(d_charges, 2),
                "Net Option P&L (₹)": round(d_net_pnl, 2),
                "Day Outcome": "PROFITABLE" if d_net_pnl > 0 else ("LOSS" if d_net_pnl < 0 else "BREAKEVEN")
            })

        df_daily_summary = pd.DataFrame(day_records)
        total_days = len(day_records)
        profitable_days = sum(1 for d in day_records if d["Net Option P&L (₹)"] > 0)
        losing_days = sum(1 for d in day_records if d["Net Option P&L (₹)"] < 0)

        return BacktestReport(
            trades=trades,
            total_trades=total_trades,
            winning_trades=wins,
            losing_trades=losses,
            scratch_trades=scratches,
            win_rate=win_rate,
            initial_capital_rs=initial_capital,
            ending_capital_rs=ending_capital,
            roi_percent=roi_percent,
            total_gross_pnl_rs=round(total_gross_pnl, 2),
            total_charges_rs=round(total_charges, 2),
            total_net_pnl_rs=round(total_net_pnl, 2),
            total_futures_pnl_rs=round(total_fut_pnl, 2),
            total_pts_pnl=round(total_pts, 2),
            avg_trade_net_pnl_rs=avg_net_pnl,
            max_win_rs=round(max_win, 2),
            max_loss_rs=round(max_loss, 2),
            profit_factor=profit_factor,
            max_drawdown_rs=round(max_dd, 2),
            total_days=total_days,
            profitable_days=profitable_days,
            losing_days=losing_days,
            equity_curve=df_equity,
            daily_summary=df_daily_summary,
        )
