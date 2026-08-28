import sys
sys.path.insert(0, r'C:\Users\admin\.gemini\antigravity\scratch\crude-signal-dashboard')
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from dashboard import get_cached_historical_data
from indicators import calculate_pivot_points

def compute_indicators_full(df):
    df = df.copy()
    close = df["close"]
    high = df["high"]
    low = df["low"]
    
    df["ema9"] = close.ewm(span=9, adjust=False).mean()
    df["ema20"] = close.ewm(span=20, adjust=False).mean()
    df["ema50"] = close.ewm(span=50, adjust=False).mean()
    
    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = (100 - (100 / (1 + rs))).fillna(50)
    
    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd_line"] = ema12 - ema26
    df["macd_signal"] = df["macd_line"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd_line"] - df["macd_signal"]
    
    # ATR & ADX
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean().fillna(20.0)
    
    up_move = high - high.shift()
    down_move = low.shift() - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_di = 100 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, min_periods=14, adjust=False).mean() / df["atr"])
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, min_periods=14, adjust=False).mean() / df["atr"])
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
    df["adx"] = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean().fillna(20.0)
    
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
        prev_st = supertrend.iloc[idx-1]
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
    return df

df_raw, df_daily = get_cached_historical_data('MCX_FO|565899', '2026-06-01', '2026-08-28', '30minute')
df_full = compute_indicators_full(df_raw)
print(f"Total days: {len(df_full['datetime'].dt.date.unique())}")

# Let's count trades with genuine trend and breakout rules across all models
for model_name in ["Supertrend & 20 EMA Momentum", "20 EMA / Pivot Pullback", "Standard Pivot Breakout", "RSI + MACD Confluence"]:
    trades_count = 0
    days_with_trades = set()
    all_dates = sorted(df_full['datetime'].dt.date.unique())
    
    for curr_date in all_dates:
        day_df = df_full[df_full['datetime'].dt.date == curr_date].reset_index(drop=True)
        traded_today = False
        
        for i in range(1, len(day_df)-2):
            if traded_today:
                break
            row = day_df.iloc[i]
            prev = day_df.iloc[i-1]
            t = row['datetime']
            if not (16 <= t.hour <= 22):
                continue
            
            p = row['close']
            adx = row['adx']
            atr = row['atr']
            
            # Skip if sideways consolidation / chop
            if adx < 22:
                continue
                
            trigger_buy = False
            trigger_sell = False
            
            if "Supertrend" in model_name:
                # Fresh breakout or strong expansion above Supertrend & 20 EMA
                if row['st_direction'] == "BULLISH" and p > row['ema20'] and row['ema20'] > row['ema50']:
                    if prev['st_direction'] == "BEARISH" or prev['close'] <= prev['ema20'] or (row['close'] - row['open']) >= (0.6 * atr):
                        trigger_buy = True
                elif row['st_direction'] == "BEARISH" and p < row['ema20'] and row['ema20'] < row['ema50']:
                    if prev['st_direction'] == "BULLISH" or prev['close'] >= prev['ema20'] or (row['open'] - row['close']) >= (0.6 * atr):
                        trigger_sell = True
                        
            elif "Pullback" in model_name:
                # Genuine bounce at 20 EMA
                if p > row['ema50'] and prev['low'] <= (prev['ema20'] + 4.0) and row['close'] > row['open'] and row['close'] > prev['high'] and (48 <= row['rsi'] <= 68):
                    trigger_buy = True
                elif p < row['ema50'] and prev['high'] >= (prev['ema20'] - 4.0) and row['close'] < row['open'] and row['close'] < prev['low'] and (32 <= row['rsi'] <= 52):
                    trigger_sell = True
                    
            elif "Pivot" in model_name:
                # Breakout
                if prev['close'] <= row['ema20'] and p > row['ema20'] and (row['close'] - row['open']) >= (0.7 * atr):
                    trigger_buy = True
                elif prev['close'] >= row['ema20'] and p < row['ema20'] and (row['open'] - row['close']) >= (0.7 * atr):
                    trigger_sell = True
                    
            elif "RSI" in model_name:
                # Fresh MACD Crossover with RSI expansion
                if prev['macd_line'] <= prev['macd_signal'] and row['macd_line'] > row['macd_signal'] and (52 <= row['rsi'] <= 70) and p > row['ema20']:
                    trigger_buy = True
                elif prev['macd_line'] >= prev['macd_signal'] and row['macd_line'] < row['macd_signal'] and (30 <= row['rsi'] <= 48) and p < row['ema20']:
                    trigger_sell = True
                    
            if trigger_buy or trigger_sell:
                traded_today = True
                trades_count += 1
                days_with_trades.add(curr_date)
                
    print(f"[{model_name}] -> Total Trades: {trades_count} across {len(days_with_trades)} / {len(all_dates)} days ({len(all_dates) - len(days_with_trades)} sideways days skipped!)")
