import sys
sys.path.insert(0, r'C:\Users\admin\.gemini\antigravity\scratch\crude-signal-dashboard')
import pandas as pd
import numpy as np
from datetime import date
from dashboard import get_cached_historical_data

df_raw, df_daily = get_cached_historical_data('MCX_FO|565899', '2026-06-01', '2026-08-28', '30minute')

# Let's run a full backtest simulation with these refined rules
def run_simulation(df_candles, df_daily, model_name, sl_pts=20.0, t1_rr=1.8, be_trigger=20.0, use_be=True, filter_mode="Balanced"):
    from backtester import CrudeBacktester
    tester = CrudeBacktester(df_candles=df_candles, df_daily=df_daily)
    
    # We will test with our refined backtester
    rep = tester.run(
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 28),
        strategy_model=model_name,
        sl_pts=sl_pts,
        t1_rr=t1_rr,
        use_breakeven=use_be,
        be_trigger_pts=be_trigger,
        session_filter='US Prime Session (16:30 - 22:30 IST)',
        max_daily_trades=1,
        lots=1,
        initial_capital=100000.0
    )
    return rep

from backtester import CrudeBacktester
tester = CrudeBacktester(df_candles=df_raw, df_daily=df_daily)

for m in ['Supertrend & 20 EMA Momentum', '20 EMA / Pivot Pullback', 'Standard Pivot Breakout', 'RSI + MACD Confluence']:
    rep = tester.run(
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 28),
        strategy_model=m,
        sl_pts=20.0,
        t1_rr=1.8,
        use_breakeven=True,
        be_trigger_pts=20.0,
        session_filter='US Prime Session (16:30 - 22:30 IST)',
        max_daily_trades=1,
        lots=1,
        initial_capital=100000.0
    )
    print(f"[{m}] Trades: {rep.total_trades}, WinRate: {rep.win_rate:.1f}%, Net PnL: Rs {rep.total_net_pnl_rs:+,.0f}, ROI: {rep.roi_percent:+.1f}%, PF: {rep.profit_factor:.2f}")
