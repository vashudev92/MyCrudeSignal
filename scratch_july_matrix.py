import sys
sys.path.insert(0, r'C:\Users\admin\.gemini\antigravity\scratch\crude-signal-dashboard')
from backtester import CrudeBacktester
from dashboard import get_cached_historical_data
from datetime import date
import re

from_str = '2026-07-01'
to_str = '2026-07-31'
df_candles, df_daily = get_cached_historical_data('MCX_FO|565899', from_str, to_str, '30minute')

tester = CrudeBacktester(df_candles=df_candles, df_daily=df_daily)

out = []
out.append("=== JULY 2026 AUDIT REPORT ===")

for sl in [15.0, 18.0, 20.0, 22.0, 25.0]:
    for rr in [1.5, 1.8, 2.0, 2.2, 2.5]:
        for model in ['Supertrend & 20 EMA Momentum', '20 EMA / Pivot Pullback', 'Standard Pivot Points Breakout', 'RSI + MACD Momentum Confluence']:
            r = tester.run(
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 31),
                strategy_model=model,
                sl_pts=sl,
                t1_rr=rr,
                session_filter='US Prime Session',
                max_daily_trades=1,
                lots=1,
                initial_capital=100000.0
            )
            out.append(f"Model: {model[:18]} | SL: {sl} | RR: 1:{rr} | Trades: {r.total_trades} | W: {r.winning_trades} | L: {r.losing_trades} | Scratch: {r.scratch_trades} | Net PnL: Rs. {r.total_net_pnl_rs:+,.0f} | WR: {r.win_rate:.1f}%")

with open(r'C:\Users\admin\.gemini\antigravity\scratch\crude-signal-dashboard\july_results.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print("Audit written to july_results.txt successfully")
