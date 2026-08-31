"""
indicators.py — Technical Indicators for Crude MCX Signal Dashboard

Calculates:
  - Standard Pivot Points (PP, R1, R2, R3, S1, S2, S3)
  - EMA 9, 21, 50, 200
  - MACD (12, 26, 9)
  - RSI (14)
  - ADX (14) Trend Strength & Chop Filter
  - Volume spike detection
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

from config import (
    EMA_FAST, EMA_MID, EMA_SLOW,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    RSI_PERIOD, PIVOT_PROXIMITY_RS
)

ADX_PERIOD = 14
ADX_CHOP_THRESHOLD = 20.0  # Below 20 = Choppy sideways market


# ─── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class PivotLevels:
    """Standard Pivot Points calculated from previous day's H/L/C."""
    pp: float = 0.0
    r1: float = 0.0
    r2: float = 0.0
    r3: float = 0.0
    s1: float = 0.0
    s2: float = 0.0
    s3: float = 0.0
    prev_high: float = 0.0
    prev_low: float = 0.0
    prev_close: float = 0.0
    date: str = ""

    def as_dict(self) -> dict:
        return {
            "S3": self.s3, "S2": self.s2, "S1": self.s1,
            "PP": self.pp,
            "R1": self.r1, "R2": self.r2, "R3": self.r3,
        }

    def nearest_support(self, price: float) -> Optional[tuple[str, float]]:
        supports = [("S1", self.s1), ("S2", self.s2), ("S3", self.s3), ("PP", self.pp)]
        below = [(n, v) for n, v in supports if v < price]
        return max(below, key=lambda x: x[1]) if below else None

    def nearest_resistance(self, price: float) -> Optional[tuple[str, float]]:
        resistances = [("R1", self.r1), ("R2", self.r2), ("R3", self.r3), ("PP", self.pp)]
        above = [(n, v) for n, v in resistances if v > price]
        return min(above, key=lambda x: x[1]) if above else None

    def at_level(self, price: float) -> Optional[str]:
        all_levels = self.as_dict()
        for name, level in all_levels.items():
            if abs(price - level) <= PIVOT_PROXIMITY_RS:
                return name
        return None


@dataclass
class IndicatorValues:
    """Snapshot of all indicator values at the latest candle."""
    close: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    atr: float = 20.0
    # EMAs
    ema9: float = 0.0
    ema21: float = 0.0
    ema50: float = 0.0
    # MACD
    macd_line: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    macd_prev_histogram: float = 0.0
    # RSI
    rsi: float = 50.0
    # ADX Trend Filter
    adx: float = 25.0
    plus_di: float = 20.0
    minus_di: float = 20.0
    is_trending: bool = True  # True if ADX >= 20
    # Volume
    volume: float = 0.0
    avg_volume_20: float = 0.0
    volume_spike: bool = False
    # Day levels
    day_high: float = 0.0
    day_low: float = 0.0
    # Derived
    above_pp: bool = False
    above_ema21: bool = False
    ema9_above_ema21: bool = False
    macd_bullish_cross: bool = False
    macd_bearish_cross: bool = False
    pivot: PivotLevels = field(default_factory=PivotLevels)
    # Smart Money Concepts / ICT
    fvg_type: str = "NONE"
    fvg_top: float = 0.0
    fvg_bottom: float = 0.0
    fvg_mid: float = 0.0
    liquidity_sweep: str = "NONE"
    # 4-Condition Dual Supertrend (11,2 & 7,3)
    st_fast: float = 0.0
    st_fast_dir: int = 1  # 1 for Bullish, -1 for Bearish
    st_slow: float = 0.0
    st_slow_dir: int = 1  # 1 for Bullish, -1 for Bearish
    st_cross_bullish: bool = False
    st_cross_bearish: bool = False
    vol_above_sma20: bool = False
    vol_consecutive_high: int = 0


# ─── Calculators ──────────────────────────────────────────────────────────────

def calculate_pivot_points(prev_high: float, prev_low: float, prev_close: float, date: str = "") -> PivotLevels:
    pp = (prev_high + prev_low + prev_close) / 3.0
    r1 = (2 * pp) - prev_low
    r2 = pp + (prev_high - prev_low)
    r3 = prev_high + 2 * (pp - prev_low)
    s1 = (2 * pp) - prev_high
    s2 = pp - (prev_high - prev_low)
    s3 = prev_low - 2 * (prev_high - pp)

    return PivotLevels(
        pp=round(pp, 2), r1=round(r1, 2), r2=round(r2, 2), r3=round(r3, 2),
        s1=round(s1, 2), s2=round(s2, 2), s3=round(s3, 2),
        prev_high=prev_high, prev_low=prev_low, prev_close=prev_close,
        date=date
    )


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _adx(df: pd.DataFrame, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculates Average Directional Index (ADX), +DI, and -DI.
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    plus_dm = high - prev_high
    minus_dm = prev_low - low

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr_smooth = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    plus_dm_smooth = plus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    plus_di = 100 * (plus_dm_smooth / tr_smooth.replace(0, np.nan))
    minus_di = 100 * (minus_dm_smooth / tr_smooth.replace(0, np.nan))

    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx = dx.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    return adx.fillna(20.0), plus_di.fillna(20.0), minus_di.fillna(20.0)


def _supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> tuple[pd.Series, pd.Series]:
    """
    Calculates Supertrend line and Direction (+1 for Bullish, -1 for Bearish).
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    hl2 = (high + low) / 2.0
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)

    n = len(df)
    final_upper = np.zeros(n)
    final_lower = np.zeros(n)
    supertrend = np.zeros(n)
    direction = np.zeros(n)

    close_arr = close.values
    bu_arr = basic_upper.values
    bl_arr = basic_lower.values

    for i in range(1, n):
        if bu_arr[i] < final_upper[i - 1] or close_arr[i - 1] > final_upper[i - 1]:
            final_upper[i] = bu_arr[i]
        else:
            final_upper[i] = final_upper[i - 1]

        if bl_arr[i] > final_lower[i - 1] or close_arr[i - 1] < final_lower[i - 1]:
            final_lower[i] = bl_arr[i]
        else:
            final_lower[i] = final_lower[i - 1]

        if supertrend[i - 1] == final_upper[i - 1]:
            if close_arr[i] > final_upper[i]:
                supertrend[i] = final_lower[i]
                direction[i] = 1
            else:
                supertrend[i] = final_upper[i]
                direction[i] = -1
        else:
            if close_arr[i] < final_lower[i]:
                supertrend[i] = final_upper[i]
                direction[i] = -1
            else:
                supertrend[i] = final_lower[i]
                direction[i] = 1

    st_series = pd.Series(supertrend, index=df.index)
    dir_series = pd.Series(direction, index=df.index)
    return st_series, dir_series


# ─── Main Indicator Calculator ────────────────────────────────────────────────

def compute_indicators(df: pd.DataFrame, pivot: PivotLevels) -> IndicatorValues:
    if df.empty or len(df) < 20:
        return IndicatorValues(pivot=pivot)

    close = df["close"]
    volume = df["volume"]

    # EMAs
    ema9 = _ema(close, EMA_FAST)
    ema21 = _ema(close, EMA_MID)
    ema50 = _ema(close, EMA_SLOW)

    # MACD
    macd_line, macd_signal_line, macd_hist = _macd(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)

    # RSI
    rsi = _rsi(close, RSI_PERIOD)

    # ADX
    adx_s, p_di_s, m_di_s = _adx(df, ADX_PERIOD)

    # Volume Spike & SMA 20
    avg_vol = volume.rolling(20).mean()
    curr_vol = float(volume.iloc[-1])
    vol_sma20 = float(avg_vol.iloc[-1]) if not avg_vol.isna().iloc[-1] else 0.0
    vol_above_sma20 = curr_vol >= vol_sma20 if vol_sma20 > 0 else True
    is_volume_spike = bool(curr_vol > vol_sma20 * 1.5) if vol_sma20 > 0 else False

    # Check consecutive volume candles above 20-SMA
    vol_consecutive = 0
    for v_idx in range(len(volume) - 1, max(0, len(volume) - 5), -1):
        if not avg_vol.isna().iloc[v_idx] and volume.iloc[v_idx] >= avg_vol.iloc[v_idx]:
            vol_consecutive += 1
        else:
            break

    # Dual Supertrend: Fast (11, 2) & Slow (7, 3)
    st_fast_s, dir_fast_s = _supertrend(df, period=11, multiplier=2.0)
    st_slow_s, dir_slow_s = _supertrend(df, period=7, multiplier=3.0)

    latest_st_fast = float(st_fast_s.iloc[-1])
    latest_st_fast_dir = int(dir_fast_s.iloc[-1])
    latest_st_slow = float(st_slow_s.iloc[-1])
    latest_st_slow_dir = int(dir_slow_s.iloc[-1])

    prev_st_fast_dir = int(dir_fast_s.iloc[-2]) if len(dir_fast_s) >= 2 else latest_st_fast_dir
    prev_st_slow_dir = int(dir_slow_s.iloc[-2]) if len(dir_slow_s) >= 2 else latest_st_slow_dir

    st_cross_bullish = (latest_st_fast_dir == 1 and (prev_st_fast_dir == -1 or latest_st_slow_dir == 1))
    st_cross_bearish = (latest_st_fast_dir == -1 and (prev_st_fast_dir == 1 or latest_st_slow_dir == -1))

    # Day High / Low
    import pytz
    from config import IST_TIMEZONE
    IST = pytz.timezone(IST_TIMEZONE)
    from datetime import datetime
    today = datetime.now(IST).date()

    today_mask = df["datetime"].dt.date == today
    if today_mask.any():
        today_df = df[today_mask]
        day_high = float(today_df["high"].max())
        day_low = float(today_df["low"].min())
    else:
        day_high = float(df["high"].iloc[-1])
        day_low = float(df["low"].iloc[-1])

    latest_close = float(close.iloc[-1])
    latest_ema9 = float(ema9.iloc[-1])
    latest_ema21 = float(ema21.iloc[-1])
    latest_ema50 = float(ema50.iloc[-1])
    latest_macd = float(macd_line.iloc[-1])
    latest_signal = float(macd_signal_line.iloc[-1])
    latest_hist = float(macd_hist.iloc[-1])
    prev_hist = float(macd_hist.iloc[-2]) if len(macd_hist) >= 2 else latest_hist
    latest_rsi = float(rsi.iloc[-1]) if not rsi.isna().iloc[-1] else 50.0
    latest_adx = float(adx_s.iloc[-1]) if not adx_s.isna().iloc[-1] else 20.0
    latest_pdi = float(p_di_s.iloc[-1]) if not p_di_s.isna().iloc[-1] else 20.0
    latest_mdi = float(m_di_s.iloc[-1]) if not m_di_s.isna().iloc[-1] else 20.0

    # Smart Money Concepts / ICT Fair Value Gap (FVG) Analysis
    fvg_type = "NONE"
    fvg_top = 0.0
    fvg_bottom = 0.0
    fvg_mid = 0.0
    liquidity_sweep = "NONE"

    if len(df) >= 4:
        c1_high = float(df["high"].iloc[-3])
        c1_low = float(df["low"].iloc[-3])
        c3_high = float(df["high"].iloc[-1])
        c3_low = float(df["low"].iloc[-1])
        
        # Bullish FVG: Gap between candle 1 high and candle 3 low
        if c3_low > c1_high + 3.0:
            fvg_type = "BULLISH_FVG"
            fvg_top = c3_low
            fvg_bottom = c1_high
            fvg_mid = (fvg_top + fvg_bottom) / 2.0
        # Bearish FVG: Gap between candle 1 low and candle 3 high
        elif c3_high < c1_low - 3.0:
            fvg_type = "BEARISH_FVG"
            fvg_top = c1_low
            fvg_bottom = c3_high
            fvg_mid = (fvg_top + fvg_bottom) / 2.0

        # Liquidity Sweep check over last 12 candles
        prev_swing_high = float(df["high"].iloc[-12:-2].max())
        prev_swing_low = float(df["low"].iloc[-12:-2].min())
        curr_high = float(df["high"].iloc[-1])
        curr_low = float(df["low"].iloc[-1])

        if curr_high > prev_swing_high and latest_close < prev_swing_high:
            liquidity_sweep = "BUY_SIDE_LIQUIDITY_PURGED (BEARISH REVERSAL)"
        elif curr_low < prev_swing_low and latest_close > prev_swing_low:
            liquidity_sweep = "SELL_SIDE_LIQUIDITY_PURGED (BULLISH REVERSAL)"

    above_pp = latest_close > pivot.pp
    above_ema21 = latest_close > latest_ema21
    ema9_above_ema21 = latest_ema9 > latest_ema21
    macd_bullish_cross = (prev_hist < 0) and (latest_hist >= 0)
    macd_bearish_cross = (prev_hist > 0) and (latest_hist <= 0)
    is_trending = latest_adx >= ADX_CHOP_THRESHOLD

    latest_open = float(df["open"].iloc[-1]) if "open" in df.columns else latest_close
    latest_high = float(df["high"].iloc[-1]) if "high" in df.columns else latest_close
    latest_low = float(df["low"].iloc[-1]) if "low" in df.columns else latest_close
    latest_atr = float(atr_series.iloc[-1]) if ("atr_series" in locals() and not atr_series.empty) else 20.0

    return IndicatorValues(
        close=latest_close,
        open=latest_open,
        high=latest_high,
        low=latest_low,
        atr=latest_atr,
        ema9=round(latest_ema9, 2),
        ema21=round(latest_ema21, 2),
        ema50=round(latest_ema50, 2),
        macd_line=round(latest_macd, 4),
        macd_signal=round(latest_signal, 4),
        macd_histogram=round(latest_hist, 4),
        macd_prev_histogram=round(prev_hist, 4),
        rsi=round(latest_rsi, 2),
        adx=round(latest_adx, 2),
        plus_di=round(latest_pdi, 2),
        minus_di=round(latest_mdi, 2),
        is_trending=is_trending,
        volume=curr_vol,
        avg_volume_20=round(vol_sma20, 2),
        volume_spike=is_volume_spike,
        day_high=round(day_high, 2),
        day_low=round(day_low, 2),
        above_pp=above_pp,
        above_ema21=above_ema21,
        ema9_above_ema21=ema9_above_ema21,
        macd_bullish_cross=macd_bullish_cross,
        macd_bearish_cross=macd_bearish_cross,
        pivot=pivot,
        fvg_type=fvg_type,
        fvg_top=round(fvg_top, 2),
        fvg_bottom=round(fvg_bottom, 2),
        fvg_mid=round(fvg_mid, 2),
        liquidity_sweep=liquidity_sweep,
        st_fast=round(latest_st_fast, 2),
        st_fast_dir=latest_st_fast_dir,
        st_slow=round(latest_st_slow, 2),
        st_slow_dir=latest_st_slow_dir,
        st_cross_bullish=st_cross_bullish,
        st_cross_bearish=st_cross_bearish,
        vol_above_sma20=vol_above_sma20,
        vol_consecutive_high=vol_consecutive
    )


def add_indicators_to_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    close = df["close"]

    df[f"ema{EMA_FAST}"] = _ema(close, EMA_FAST).round(2)
    df[f"ema{EMA_MID}"] = _ema(close, EMA_MID).round(2)
    df[f"ema{EMA_SLOW}"] = _ema(close, EMA_SLOW).round(2)

    macd_line, macd_signal_line, macd_hist = _macd(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    df["macd_line"] = macd_line.round(4)
    df["macd_signal"] = macd_signal_line.round(4)
    df["macd_histogram"] = macd_hist.round(4)

    df["rsi"] = _rsi(close, RSI_PERIOD).round(2)
    adx_s, _, _ = _adx(df, ADX_PERIOD)
    df["adx"] = adx_s.round(2)

    return df
