import sys
sys.path.insert(0, r'C:\Users\admin\.gemini\antigravity\scratch\crude-signal-dashboard')
import pandas as pd
import numpy as np
from datetime import date
from dashboard import get_cached_historical_data

df_raw, df_daily = get_cached_historical_data('MCX_FO|565899', '2026-06-01', '2026-08-28', '30minute')

# Let's test the improved backtester logic directly
from backtester import CrudeBacktester

# Let's inspect indicators preparation
tester = CrudeBacktester(df_candles=df_raw, df_daily=df_daily)
df_ind = tester._prepare_indicators(df_raw)
print(f"Computed indicators shape: {df_ind.shape}")
