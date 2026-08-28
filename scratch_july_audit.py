import sys
sys.path.insert(0, r'C:\Users\admin\.gemini\antigravity\scratch\crude-signal-dashboard')
from backtester import CrudeBacktester
from dashboard import get_cached_historical_data
from datetime import date
import pandas as pd

from_str = '2026-07-01'
to_str = '2026-07-31'
df_candles, df_daily = get_cached_historical_data('MCX_FO|565899', from_str, to_str, '30minute')

tester = CrudeBacktester(df_candles=df_candles, df_daily=df_daily)

strategies = [
    'Supertrend & 20 EMA Momentum',
    '20 EMA / Pivot Pullback',
    'Standard Pivot Points Breakout',
    'RSI + MACD Momentum Confluence'
]

print('=== AUDIT 1: DEFAULT CONFIG (SL 25, T1 2.5, US Session) ===')
for s in strategies:
    rep = tester.run(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        strategy_model=s,
        sl_pts=25.0,
        t1_rr=2.5,
        session_filter='US Prime Session',
        max_daily_trades=1,
        lots=1,
        initial_capital=100000.0
    )
    print(s + ': Trades=' + str(rep.total_trades) + ' Wins=' + str(rep.winning_trades) + ' Losses=' + str(rep.losing_trades) + ' Scratches=' + str(rep.scratch_trades) + ' Net PnL=Rs. ' + str(rep.total_net_pnl_rs) + ' WinRate=' + str(rep.win_rate) + '%')

print('\n=== AUDIT 2: TRADE REASONS IN JULY FOR SUPERTREND ===')
rep_st = tester.run(
    start_date=date(2026, 7, 1),
    end_date=date(2026, 7, 31),
    strategy_model='Supertrend & 20 EMA Momentum',
    sl_pts=25.0,
    t1_rr=2.5,
    session_filter='US Prime Session',
    max_daily_trades=1,
    lots=1,
    initial_capital=100000.0
)

for t in rep_st.trades:
    print('Date: ' + t.trade_date + ' | Entry: ' + str(t.entry_price) + ' -> Exit: ' + str(t.exit_price) + ' | ExitReason: ' + t.exit_reason + ' | PnL: Rs. ' + str(t.net_option_pnl_rs))

print('\n=== AUDIT 3: PARAMETER SENSITIVITY GRID FOR JULY ===')
for sl in [15.0, 18.0, 20.0, 25.0]:
    for rr in [1.5, 1.8, 2.0, 2.2, 2.5]:
        r = tester.run(
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            strategy_model='Supertrend & 20 EMA Momentum',
            sl_pts=sl,
            t1_rr=rr,
            session_filter='US Prime Session',
            max_daily_trades=1,
            lots=1,
            initial_capital=100000.0
        )
        print('SL=' + str(sl) + ' pts | T1 R:R=1:' + str(rr) + ' -> Net PnL: Rs. ' + str(r.total_net_pnl_rs) + ' | Wins: ' + str(r.winning_trades) + '/' + str(r.total_trades) + ' (' + str(r.win_rate) + '%)')
