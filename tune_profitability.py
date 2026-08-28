import sys
sys.path.insert(0, r'C:\Users\admin\.gemini\antigravity\scratch\crude-signal-dashboard')
import pandas as pd
import numpy as np
from datetime import date
from dashboard import get_cached_historical_data

df_raw, df_daily = get_cached_historical_data('MCX_FO|565899', '2026-06-01', '2026-08-28', '30minute')

from backtester import CrudeBacktester
tester = CrudeBacktester(df_candles=df_raw, df_daily=df_daily)

# Let's test with proper balanced quality filter
for m in [
    'Supertrend & 20 EMA Momentum',
    '20 EMA / Pivot Pullback',
    'Standard Pivot Breakout',
    'RSI + MACD Confluence'
]:
    for regime in ['🎯 Balanced Quality (ADX >= 18)', '🛡️ Strict Trend (ADX >= 23)']:
        rep = tester.run(
            start_date=date(2026, 6, 1),
            end_date=date(2026, 8, 28),
            strategy_model=m,
            sl_pts=20.0,
            t1_rr=2.0,
            use_breakeven=True,
            be_trigger_pts=20.0,
            session_filter='US Prime Session (16:30 - 22:30 IST)',
            market_regime=regime,
            max_daily_trades=1,
            lots=1,
            initial_capital=100000.0
        )
        print(f"[{m}] ({regime}) -> Trades: {rep.total_trades}, Wins: {rep.winning_trades}, Losses: {rep.losing_trades}, Net: Rs {rep.total_net_pnl_rs:+,.0f}, WinRate: {rep.win_rate:.1f}%, ROI: {rep.roi_percent:+.1f}%, PF: {rep.profit_factor:.2f}")
