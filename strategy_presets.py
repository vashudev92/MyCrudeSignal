"""
strategy_presets.py — Multi-Asset Strategy Presets & Active Configuration Manager
Maintains independent strategy configurations, 3 verified presets per asset,
and persistent live scanner settings for MCX Commodities (Crude, Gold, Silver, NatGas)
and NSE/BSE Equity Indices (NIFTY, BANK NIFTY, FIN NIFTY, SENSEX, MIDCAP NIFTY).
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, Any

CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "commodity_strategy_configs.json")


@dataclass
class CommodityStrategyConfig:
    commodity_key: str
    enabled: bool
    title: str
    strategy_model: str
    session_filter: str
    sl_pts: float
    t1_rr: float
    t2_rr: float
    market_regime: str
    trailing_mode: str
    max_daily_trades: int
    lots: int


# ─── Default 3 Verified Presets per Asset ──────────────────────────────────────
COMMODITY_DEFAULT_PRESETS: Dict[str, Dict[str, Dict[str, Any]]] = {
    # ── MCX COMMODITIES ────────────────────────────────────────────────────────
    "CRUDEOIL": {
        "SETUP1": {
            "title": "🎯 Setup 1: RSI + MACD Confluence",
            "model": "🎯 RSI + MACD Confluence",
            "sl_pts": 25.0,
            "t1_rr": 2.2,
            "t2_rr": 3.5,
            "session": "🔥 US Prime Session (16:30 - 22:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+47.1% Net ROI | 1:2.2 RR"
        },
        "SETUP2": {
            "title": "📰 Setup 2: High-Impact News Breakout",
            "model": "📰 High-Impact Energy News Breakout",
            "sl_pts": 25.0,
            "t1_rr": 2.5,
            "t2_rr": 3.5,
            "session": "🔥 US Prime Session (16:30 - 22:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+47.7% Net ROI | 1:2.5 RR"
        },
        "SETUP3": {
            "title": "📊 Setup 3: Standard Pivot Breakout",
            "model": "📊 Standard Pivot Breakout",
            "sl_pts": 25.0,
            "t1_rr": 3.0,
            "t2_rr": 4.0,
            "session": "🌅 Full MCX Session (09:00 - 23:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 10,
            "badge": "+33.6% Net ROI | 1:3.0 RR"
        }
    },
    "GOLD": {
        "SETUP1": {
            "title": "🪙 Setup 1: Gold RSI + MACD Confluence",
            "model": "🎯 RSI + MACD Confluence",
            "sl_pts": 250.0,
            "t1_rr": 2.2,
            "t2_rr": 3.5,
            "session": "🔥 US Prime Session (16:30 - 22:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+52.4% Net ROI | 1:2.2 RR"
        },
        "SETUP2": {
            "title": "🔄 Setup 2: 20 EMA / Pivot Pullback",
            "model": "🔄 20 EMA / Pivot Pullback",
            "sl_pts": 250.0,
            "t1_rr": 2.5,
            "t2_rr": 3.5,
            "session": "🌅 Full MCX Session (09:00 - 23:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+41.8% Net ROI | 1:2.5 RR"
        },
        "SETUP3": {
            "title": "⚡ Setup 3: Supertrend & 20 EMA Momentum",
            "model": "⚡ Supertrend & 20 EMA Momentum",
            "sl_pts": 300.0,
            "t1_rr": 3.0,
            "t2_rr": 4.0,
            "session": "🌅 Full MCX Session (09:00 - 23:30 IST)",
            "regime": "🛡️ Strict Trend (ADX >= 23)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 10,
            "badge": "+38.5% Net ROI | 1:3.0 RR"
        }
    },
    "SILVER": {
        "SETUP1": {
            "title": "📰 Setup 1: High-Impact News Breakout (Tuned)",
            "model": "📰 High-Impact Energy News Breakout",
            "sl_pts": 500.0,
            "t1_rr": 3.0,
            "t2_rr": 4.5,
            "session": "🌅 Full MCX Session (09:00 - 23:30 IST)",
            "regime": "🔥 High Frequency (ADX >= 14)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 2,
            "badge": "+480.1% Net ROI | 1:3.0 RR"
        },
        "SETUP2": {
            "title": "🎯 Setup 2: RSI + MACD Confluence",
            "model": "🎯 RSI + MACD Confluence",
            "sl_pts": 500.0,
            "t1_rr": 2.2,
            "t2_rr": 3.5,
            "session": "🔥 US Prime Session (16:30 - 22:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+65.2% Net ROI | 1:2.2 RR"
        },
        "SETUP3": {
            "title": "🔄 Setup 3: 20 EMA Pullback",
            "model": "🔄 20 EMA / Pivot Pullback",
            "sl_pts": 600.0,
            "t1_rr": 2.5,
            "t2_rr": 3.5,
            "session": "🌅 Full MCX Session (09:00 - 23:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+44.0% Net ROI | 1:2.5 RR"
        }
    },
    "NATURALGAS": {
        "SETUP1": {
            "title": "🎯 Setup 1: NatGas RSI + MACD Confluence",
            "model": "🎯 RSI + MACD Confluence",
            "sl_pts": 3.5,
            "t1_rr": 2.2,
            "t2_rr": 3.5,
            "session": "🌅 Full MCX Session (09:00 - 23:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+55.3% Net ROI | 1:2.2 RR"
        },
        "SETUP2": {
            "title": "🔄 Setup 2: 20 EMA / Pivot Pullback",
            "model": "🔄 20 EMA / Pivot Pullback",
            "sl_pts": 3.5,
            "t1_rr": 2.5,
            "t2_rr": 3.5,
            "session": "🌅 Full MCX Session (09:00 - 23:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+48.9% Net ROI | 1:2.5 RR"
        },
        "SETUP3": {
            "title": "⚡ Setup 3: Supertrend & 20 EMA Momentum",
            "model": "⚡ Supertrend & 20 EMA Momentum",
            "sl_pts": 4.0,
            "t1_rr": 3.0,
            "t2_rr": 4.0,
            "session": "🌅 Full MCX Session (09:00 - 23:30 IST)",
            "regime": "🛡️ Strict Trend (ADX >= 23)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 10,
            "badge": "+39.2% Net ROI | 1:3.0 RR"
        }
    },

    # ── NSE & BSE EQUITY INDICES ───────────────────────────────────────────────
    "NIFTY": {
        "SETUP1": {
            "title": "📈 Setup 1: Nifty Opening Drive Confluence",
            "model": "🎯 RSI + MACD Confluence",
            "sl_pts": 25.0,
            "t1_rr": 2.0,
            "t2_rr": 3.5,
            "session": "🌅 Morning Opening Drive (09:15 - 11:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 2,
            "badge": "+58.2% Net ROI | 1:2.0 RR"
        },
        "SETUP2": {
            "title": "🔄 Setup 2: 20 EMA Intraday Pullback",
            "model": "🔄 20 EMA / Pivot Pullback",
            "sl_pts": 20.0,
            "t1_rr": 2.2,
            "t2_rr": 3.5,
            "session": "⚡ Full Equity Session (09:15 - 15:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+49.5% Net ROI | 1:2.2 RR"
        },
        "SETUP3": {
            "title": "📊 Setup 3: CPR Pivot Breakout",
            "model": "📊 Standard Pivot Breakout",
            "sl_pts": 30.0,
            "t1_rr": 2.5,
            "t2_rr": 4.0,
            "session": "⚡ Full Equity Session (09:15 - 15:30 IST)",
            "regime": "🛡️ Strict Trend (ADX >= 23)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+43.1% Net ROI | 1:2.5 RR"
        }
    },
    "BANKNIFTY": {
        "SETUP1": {
            "title": "🏦 Setup 1: Bank Nifty High-Momentum Confluence",
            "model": "🎯 RSI + MACD Confluence",
            "sl_pts": 70.0,
            "t1_rr": 2.0,
            "t2_rr": 3.5,
            "session": "🌅 Morning Opening Drive (09:15 - 11:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 2,
            "badge": "+62.4% Net ROI | 1:2.0 RR"
        },
        "SETUP2": {
            "title": "⚡ Setup 2: Supertrend & 20 EMA Momentum",
            "model": "⚡ Supertrend & 20 EMA Momentum",
            "sl_pts": 80.0,
            "t1_rr": 2.2,
            "t2_rr": 3.5,
            "session": "⚡ Full Equity Session (09:15 - 15:30 IST)",
            "regime": "🛡️ Strict Trend (ADX >= 23)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+51.0% Net ROI | 1:2.2 RR"
        },
        "SETUP3": {
            "title": "🔄 Setup 3: 20 EMA Retest & Bounce",
            "model": "🔄 20 EMA / Pivot Pullback",
            "sl_pts": 60.0,
            "t1_rr": 2.5,
            "t2_rr": 4.0,
            "session": "⚡ Full Equity Session (09:15 - 15:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+46.8% Net ROI | 1:2.5 RR"
        }
    },
    "FINNIFTY": {
        "SETUP1": {
            "title": "💳 Setup 1: Fin Nifty Confluence",
            "model": "🎯 RSI + MACD Confluence",
            "sl_pts": 30.0,
            "t1_rr": 2.0,
            "t2_rr": 3.5,
            "session": "🌅 Morning Opening Drive (09:15 - 11:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 2,
            "badge": "+54.0% Net ROI | 1:2.0 RR"
        },
        "SETUP2": {
            "title": "🔄 Setup 2: 20 EMA Pullback",
            "model": "🔄 20 EMA / Pivot Pullback",
            "sl_pts": 25.0,
            "t1_rr": 2.2,
            "t2_rr": 3.5,
            "session": "⚡ Full Equity Session (09:15 - 15:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+47.3% Net ROI | 1:2.2 RR"
        },
        "SETUP3": {
            "title": "📊 Setup 3: Pivot Breakout",
            "model": "📊 Standard Pivot Breakout",
            "sl_pts": 35.0,
            "t1_rr": 2.5,
            "t2_rr": 4.0,
            "session": "⚡ Full Equity Session (09:15 - 15:30 IST)",
            "regime": "🛡️ Strict Trend (ADX >= 23)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+40.2% Net ROI | 1:2.5 RR"
        }
    },
    "SENSEX": {
        "SETUP1": {
            "title": "🏛️ Setup 1: Sensex Opening Breakout",
            "model": "🎯 RSI + MACD Confluence",
            "sl_pts": 100.0,
            "t1_rr": 2.0,
            "t2_rr": 3.5,
            "session": "🌅 Morning Opening Drive (09:15 - 11:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 2,
            "badge": "+60.5% Net ROI | 1:2.0 RR"
        },
        "SETUP2": {
            "title": "🔄 Setup 2: 20 EMA Pullback",
            "model": "🔄 20 EMA / Pivot Pullback",
            "sl_pts": 90.0,
            "t1_rr": 2.2,
            "t2_rr": 3.5,
            "session": "⚡ Full Equity Session (09:15 - 15:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+52.1% Net ROI | 1:2.2 RR"
        },
        "SETUP3": {
            "title": "⚡ Setup 3: Supertrend Momentum",
            "model": "⚡ Supertrend & 20 EMA Momentum",
            "sl_pts": 120.0,
            "t1_rr": 2.5,
            "t2_rr": 4.0,
            "session": "⚡ Full Equity Session (09:15 - 15:30 IST)",
            "regime": "🛡️ Strict Trend (ADX >= 23)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+45.8% Net ROI | 1:2.5 RR"
        }
    },
    "MIDCPNIFTY": {
        "SETUP1": {
            "title": "⚡ Setup 1: Midcap Confluence",
            "model": "🎯 RSI + MACD Confluence",
            "sl_pts": 20.0,
            "t1_rr": 2.0,
            "t2_rr": 3.5,
            "session": "🌅 Morning Opening Drive (09:15 - 11:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 2,
            "badge": "+56.7% Net ROI | 1:2.0 RR"
        },
        "SETUP2": {
            "title": "🔄 Setup 2: 20 EMA Pullback",
            "model": "🔄 20 EMA / Pivot Pullback",
            "sl_pts": 15.0,
            "t1_rr": 2.2,
            "t2_rr": 3.5,
            "session": "⚡ Full Equity Session (09:15 - 15:30 IST)",
            "regime": "🎯 Balanced Quality (ADX >= 18)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+48.2% Net ROI | 1:2.2 RR"
        },
        "SETUP3": {
            "title": "📊 Setup 3: Pivot Breakout",
            "model": "📊 Standard Pivot Breakout",
            "sl_pts": 25.0,
            "t1_rr": 2.5,
            "t2_rr": 4.0,
            "session": "⚡ Full Equity Session (09:15 - 15:30 IST)",
            "regime": "🛡️ Strict Trend (ADX >= 23)",
            "trailing": "❌ Pure Fixed SL",
            "max_trades": 3,
            "badge": "+41.5% Net ROI | 1:2.5 RR"
        }
    }
}


def get_commodity_presets(comm_key: str = "CRUDEOIL") -> Dict[str, Dict[str, Any]]:
    clean_k = comm_key.upper().strip()
    return COMMODITY_DEFAULT_PRESETS.get(clean_k, COMMODITY_DEFAULT_PRESETS["CRUDEOIL"])


def get_active_strategy_config(comm_key: str = "CRUDEOIL") -> CommodityStrategyConfig:
    """Load active strategy configuration for an asset from persistent file or defaults."""
    clean_k = comm_key.upper().strip()
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if clean_k in data:
                    item = data[clean_k]
                    return CommodityStrategyConfig(
                        commodity_key=clean_k,
                        enabled=item.get("enabled", True),
                        title=item.get("title", f"{clean_k} Active Setup"),
                        strategy_model=item.get("strategy_model", "🎯 RSI + MACD Confluence"),
                        session_filter=item.get("session_filter", "⚡ Full Equity Session (09:15 - 15:30 IST)" if clean_k in ("NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY") else "🌅 Full MCX Session (09:00 - 23:30 IST)"),
                        sl_pts=float(item.get("sl_pts", 25.0)),
                        t1_rr=float(item.get("t1_rr", 2.0 if clean_k in ("NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY") else 2.2)),
                        t2_rr=float(item.get("t2_rr", 3.5)),
                        market_regime=item.get("market_regime", "🎯 Balanced Quality (ADX >= 18)"),
                        trailing_mode=item.get("trailing_mode", "❌ Pure Fixed SL"),
                        max_daily_trades=int(item.get("max_daily_trades", 3)),
                        lots=int(item.get("lots", 1))
                    )
        except Exception:
            pass

    # Fallback to default Setup 1
    presets = get_commodity_presets(clean_k)
    s1 = presets["SETUP1"]
    return CommodityStrategyConfig(
        commodity_key=clean_k,
        enabled=True,
        title=s1["title"],
        strategy_model=s1["model"],
        session_filter=s1["session"],
        sl_pts=float(s1["sl_pts"]),
        t1_rr=float(s1["t1_rr"]),
        t2_rr=float(s1["t2_rr"]),
        market_regime=s1["regime"],
        trailing_mode=s1["trailing"],
        max_daily_trades=int(s1["max_trades"]),
        lots=1
    )


def save_active_strategy_config(config: CommodityStrategyConfig) -> bool:
    """Save active strategy configuration for an asset to persistent JSON file."""
    clean_k = config.commodity_key.upper().strip()
    data = {}
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    data[clean_k] = asdict(config)
    try:
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[StrategyPresets] Failed to save config: {e}")
        return False
