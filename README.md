# 🛢️ Crude MCX Signal Dashboard

A real-time trading signal tool for MCX Crude Oil — built for options traders on Upstox.

Combines **Standard Pivot Points + EMA Trend Following + MACD + RSI + Live News** to generate clear **BUY / SELL / NEUTRAL** signals with entry price, stop-loss, and targets.

---

## 📸 What You'll See

```
┌─────────────────────────────────────────────────────────┐
│  💰 Live Price     │ 📡 Signal  │ 🎯 Trade Levels        │
│  ₹6,423.50        │  🟢 BUY   │  Entry:  ₹6,423        │
│  ▲ ₹45 (+0.71%)   │ HIGH (5/5)│  SL:     ₹6,388        │
│  H: 6450 L: 6380  │           │  T1:     ₹6,478 (R1)   │
│  RSI: 58  MACD:+12│           │  T2:     ₹6,521 (R2)   │
├───────────────────────────────────────────────────────  │
│  📊 Candlestick Chart with EMA 9/21/50 + Pivot Levels   │
│  [Sub: MACD histogram] [Sub: RSI 14]                    │
├─────────────────────────────────────────────────────────│
│  📰 Crude Oil News (live, every 5 min)                  │
│  🟥 OPEC cuts output by 500k bpd — Oil rises...         │
│  ⬜ Crude inventories data awaited on Wednesday          │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (5 Steps)

### Step 1 — Install Python (if not already)
Download Python 3.10+ from https://python.org/downloads/

### Step 2 — Install Dependencies
Open PowerShell in this folder and run:
```powershell
pip install -r requirements.txt
```

### Step 3 — Get Upstox API Credentials
1. Go to https://upstox.com/developer/
2. Log in with your Upstox account
3. Click "Create App"
4. Set Redirect URI to: `http://127.0.0.1:8000/callback`
5. Copy your **API Key** and **API Secret**

### Step 4 — Configure .env file
```powershell
# Copy the template
copy .env.example .env

# Open and fill in your keys
notepad .env
```

Fill in:
```
UPSTOX_API_KEY=your_actual_key
UPSTOX_API_SECRET=your_actual_secret
UPSTOX_REDIRECT_URI=http://127.0.0.1:8000/callback
```

### Step 5 — Launch Dashboard
```powershell
streamlit run dashboard.py
```

Browser opens at `http://localhost:8501` 🎉

> **First run**: Click the Upstox login button → authorize → paste the code back → you're connected!

---

## 🎮 Demo Mode (No API Key Needed)

Toggle "🎮 Demo Mode" in the sidebar to see the dashboard with simulated data — great for testing before setup.

---

## 📡 Signal Logic

Signals are generated on **15-minute candles** using a scoring system:

| Condition | BUY | SELL |
|---|---|---|
| Price vs PP | Price > PP | Price < PP |
| Price vs EMA 21 | Price > EMA 21 | Price < EMA 21 |
| EMA Cross | EMA 9 > EMA 21 | EMA 9 < EMA 21 |
| MACD | Histogram > 0 | Histogram < 0 |
| RSI | 40 ≤ RSI ≤ 70 | 30 ≤ RSI ≤ 60 |
| Bonus | Bounce off S1/S2 | Rejected at R1/R2 |

- **HIGH confidence** = 5/5 conditions met
- **MEDIUM confidence** = 3–4/5 conditions met
- **NEUTRAL** = mixed signals (wait)

**News can reinforce or weaken signals** — bearish crude news weakens BUY signals.

---

## 📐 Pivot Points (Standard/Classical)

Calculated from previous day's High, Low, Close:

```
PP  = (High + Low + Close) / 3
R1  = (2 × PP) - Low       → First resistance
R2  = PP + (High - Low)    → Second resistance
R3  = High + 2(PP - Low)   → Third resistance
S1  = (2 × PP) - High      → First support
S2  = PP - (High - Low)    → Second support
S3  = Low - 2(High - PP)   → Third support
```

Pivot levels reset every day at market open (9:00 AM IST).

---

## 🎯 How to Use the Signals for Options Trading

1. **Wait for a HIGH confidence signal** (5/5 conditions)
2. **Check news sentiment** — don't buy options against the news
3. **Entry**: When price is at/near the entry level shown
4. **Buy the suggested option** (ATM CE for BUY, ATM PE for SELL)
5. **Risk management**:
   - Never risk more than 2% of capital on one trade
   - Exit if underlying crosses your stop-loss level
   - Book partial profits at T1, keep rest for T2

---

## ⚠️ Risk Disclaimer

This tool generates **technical signals only**. Options trading in MCX Crude Oil involves **significant risk** due to leverage. Always:
- Use stop-losses
- Size positions appropriately
- Never trade with money you can't afford to lose
- This is NOT financial advice

---

## 📁 File Structure

```
crude-signal-dashboard/
├── dashboard.py          ← Main entry point (run this)
├── config.py             ← All settings (timeframes, EMA lengths, etc.)
├── upstox_client.py      ← Upstox API auth + data fetching
├── instrument_finder.py  ← Auto-finds active CRUDEOIL contract
├── indicators.py         ← Pivot, EMA, MACD, RSI calculations
├── signal_engine.py      ← Signal generation logic
├── news_monitor.py       ← News fetching + sentiment
├── alert_manager.py      ← Sound + Telegram alerts
├── requirements.txt      ← Python dependencies
├── .env.example          ← Config template (copy to .env)
└── README.md             ← This file
```

---

## 🛠️ Customization

Edit `config.py` to tune:
- **EMA lengths** (`EMA_FAST`, `EMA_MID`, `EMA_SLOW`)
- **Signal timeframe** (`PRIMARY_TIMEFRAME`)
- **RSI levels** (`RSI_OVERBOUGHT`, `RSI_OVERSOLD`)
- **Pivot proximity** (`PIVOT_PROXIMITY_RS`) — how close to a level counts as "at level"
- **Telegram alerts** — set `ENABLE_TELEGRAM = True` and add bot token

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` again |
| Token expired | Dashboard shows login button — just re-authorize |
| No data / empty chart | Market may be closed, or instrument key expired |
| Wrong pivot levels | Check previous day's OHLC from Upstox matches expectations |
| News not loading | Check internet connection; RSS feeds may be temporarily down |
