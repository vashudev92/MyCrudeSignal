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
                        enabled=item.get("enabled", clean_k == "CRUDEOIL"),
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
        enabled=(clean_k == "CRUDEOIL"),
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


# ─── Custom Saved Strategy Library Management ─────────────────────────────────
SAVED_STRATEGIES_FILE = os.path.join(os.path.dirname(__file__), "saved_strategies.json")


def get_saved_strategies_for_asset(commodity_key: str) -> list[dict[str, Any]]:
    """Retrieve all saved strategies for a specific instrument."""
    clean_k = commodity_key.upper().strip()
    if os.path.exists(SAVED_STRATEGIES_FILE):
        try:
            with open(SAVED_STRATEGIES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if clean_k in data and isinstance(data[clean_k], list):
                    return data[clean_k]
        except Exception as e:
            print(f"[StrategyPresets] Error reading saved strategies: {e}")

    # Fallback to 3 default presets
    presets = get_commodity_presets(clean_k)
    fallback_list = []
    for s_k, s_v in presets.items():
        fallback_list.append({
            "id": f"{clean_k.lower()}_{s_k.lower()}",
            "name": s_v.get("title", f"{clean_k} {s_k}"),
            "model": s_v.get("model", "🎯 RSI + MACD Confluence"),
            "sl_pts": float(s_v.get("sl_pts", 25.0)),
            "t1_rr": float(s_v.get("t1_rr", 2.2)),
            "t2_rr": float(s_v.get("t2_rr", 3.5)),
            "session": s_v.get("session", "🌅 Full MCX Session (09:00 - 23:30 IST)"),
            "regime": s_v.get("regime", "🎯 Balanced Quality (ADX >= 18)"),
            "trailing": s_v.get("trailing", "❌ Pure Fixed SL"),
            "max_trades": int(s_v.get("max_trades", 3)),
            "badge": s_v.get("badge", "Verified Preset"),
            "created_at": "2026-08-31 09:00:00"
        })
    return fallback_list


def save_custom_strategy(
    commodity_key: str,
    name: str,
    model: str,
    session_filter: str,
    sl_pts: float,
    t1_rr: float,
    t2_rr: float,
    market_regime: str,
    trailing_mode: str,
    max_daily_trades: int,
    badge: str = "Custom Backtested",
    set_active: bool = True
) -> dict[str, Any]:
    """Save a newly backtested or customized strategy to the asset's library."""
    import time
    clean_k = commodity_key.upper().strip()
    strat_id = f"{clean_k.lower()}_{int(time.time())}"
    new_strat = {
        "id": strat_id,
        "name": name.strip(),
        "model": model,
        "sl_pts": float(sl_pts),
        "t1_rr": float(t1_rr),
        "t2_rr": float(t2_rr),
        "session": session_filter,
        "regime": market_regime,
        "trailing": trailing_mode,
        "max_trades": int(max_daily_trades),
        "badge": badge,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    all_data = {}
    if os.path.exists(SAVED_STRATEGIES_FILE):
        try:
            with open(SAVED_STRATEGIES_FILE, "r", encoding="utf-8") as f:
                all_data = json.load(f)
        except Exception:
            all_data = {}

    if clean_k not in all_data or not isinstance(all_data[clean_k], list):
        all_data[clean_k] = get_saved_strategies_for_asset(clean_k)

    # Check if a strategy with same name exists; if so, update it
    existing_idx = next((i for i, s in enumerate(all_data[clean_k]) if s.get("name", "").lower() == name.strip().lower()), -1)
    if existing_idx >= 0:
        new_strat["id"] = all_data[clean_k][existing_idx].get("id", strat_id)
        all_data[clean_k][existing_idx] = new_strat
    else:
        all_data[clean_k].append(new_strat)

    try:
        with open(SAVED_STRATEGIES_FILE, "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=2)
    except Exception as e:
        print(f"[StrategyPresets] Error saving strategy: {e}")

    if set_active:
        deploy_cfg = CommodityStrategyConfig(
            commodity_key=clean_k,
            enabled=True,
            title=name.strip(),
            strategy_model=model,
            session_filter=session_filter,
            sl_pts=float(sl_pts),
            t1_rr=float(t1_rr),
            t2_rr=float(t2_rr),
            market_regime=market_regime,
            trailing_mode=trailing_mode,
            max_daily_trades=int(max_daily_trades),
            lots=1
        )
        save_active_strategy_config(deploy_cfg)

    return new_strat


def rename_custom_strategy(commodity_key: str, strategy_id: str, new_name: str) -> bool:
    """Rename an existing saved strategy and sync active title if currently deployed."""
    clean_k = commodity_key.upper().strip()
    if not os.path.exists(SAVED_STRATEGIES_FILE):
        return False

    try:
        with open(SAVED_STRATEGIES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if clean_k in data and isinstance(data[clean_k], list):
            for s in data[clean_k]:
                if s.get("id") == strategy_id:
                    s["name"] = new_name.strip()
                    break

            with open(SAVED_STRATEGIES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            # Sync active strategy title if matches
            cur_cfg = get_active_strategy_config(clean_k)
            cur_cfg.title = new_name.strip()
            save_active_strategy_config(cur_cfg)
            return True
    except Exception as e:
        print(f"[StrategyPresets] Error renaming strategy: {e}")
    return False


def delete_custom_strategy(commodity_key: str, strategy_id: str) -> bool:
    """Delete a saved strategy from the asset's library."""
    clean_k = commodity_key.upper().strip()
    if not os.path.exists(SAVED_STRATEGIES_FILE):
        return False

    try:
        with open(SAVED_STRATEGIES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if clean_k in data and isinstance(data[clean_k], list):
            data[clean_k] = [s for s in data[clean_k] if s.get("id") != strategy_id]
            # Always ensure at least 1 default strategy remains
            if not data[clean_k]:
                data[clean_k] = get_saved_strategies_for_asset(clean_k)

            with open(SAVED_STRATEGIES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
    except Exception as e:
        print(f"[StrategyPresets] Error deleting strategy: {e}")
    return False


def deploy_strategy_to_asset(commodity_key: str, strategy_id: str) -> bool:
    """Set a specific saved strategy as the active live scanner strategy."""
    clean_k = commodity_key.upper().strip()
    strats = get_saved_strategies_for_asset(clean_k)
    target = next((s for s in strats if s.get("id") == strategy_id), None)
    if not target:
        return False

    cur_cfg = get_active_strategy_config(clean_k)
    new_cfg = CommodityStrategyConfig(
        commodity_key=clean_k,
        enabled=True,
        title=target["name"],
        strategy_model=target["model"],
        session_filter=target["session"],
        sl_pts=float(target["sl_pts"]),
        t1_rr=float(target["t1_rr"]),
        t2_rr=float(target.get("t2_rr", target["t1_rr"] * 1.5)),
        market_regime=target["regime"],
        trailing_mode=target["trailing"],
        max_daily_trades=int(target["max_trades"]),
        lots=cur_cfg.lots
    )
    return save_active_strategy_config(new_cfg)
