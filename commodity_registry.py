"""
commodity_registry.py — Multi-Asset Specifications & Rules Registry
Defines specifications, strike intervals, lot sizes, default SL/Target, and tax structures
for MCX Commodities (Crude Oil, Gold, Silver, Natural Gas) and NSE/BSE Equity Indices (Nifty 50, Bank Nifty, Fin Nifty, Sensex, Midcap Nifty).
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class CommoditySpec:
    key: str
    name: str
    symbol_keyword: str
    icon: str
    futures_lot_size: int
    mini_lot_size: int
    default_lot_type: str  # "REGULAR" or "MINI"
    active_lot_size: int
    lot_unit: str
    strike_step: int
    default_sl_pts: float
    default_t1_rr: float
    default_t2_rr: float
    atm_delta: float
    base_spot_estimate: float
    base_option_premium: float
    tick_size: float
    category: str = "COMMODITY"  # "COMMODITY" or "INDEX"
    segment: str = "MCX_FO"      # "MCX_FO", "NSE_INDEX", "BSE_INDEX"
    market_open_time: str = "09:00"
    market_close_time: str = "23:30"
    ctt_rate: float = 0.000125  # 0.0125% on option sell turnover (MCX CTT)
    exchange_fee_rate: float = 0.0005


COMMODITY_REGISTRY: Dict[str, CommoditySpec] = {
    # ── MCX COMMODITIES ────────────────────────────────────────────────────────
    "CRUDEOIL": CommoditySpec(
        key="CRUDEOIL",
        name="Crude Oil",
        symbol_keyword="CRUDEOIL",
        icon="🛢️",
        futures_lot_size=100,
        mini_lot_size=10,
        default_lot_type="REGULAR",
        active_lot_size=100,
        lot_unit="bbl",
        strike_step=50,
        default_sl_pts=25.0,
        default_t1_rr=2.2,
        default_t2_rr=3.5,
        atm_delta=0.50,
        base_spot_estimate=7500.0,
        base_option_premium=180.0,
        tick_size=1.0,
        category="COMMODITY",
        segment="MCX_FO",
        market_open_time="09:00",
        market_close_time="23:30",
    ),
    "GOLD": CommoditySpec(
        key="GOLD",
        name="Gold (100g Mini / 1kg)",
        symbol_keyword="GOLD",
        icon="🪙",
        futures_lot_size=100,
        mini_lot_size=10,
        default_lot_type="MINI",
        active_lot_size=10,
        lot_unit="grams",
        strike_step=100,
        default_sl_pts=250.0,
        default_t1_rr=2.2,
        default_t2_rr=3.5,
        atm_delta=0.50,
        base_spot_estimate=74200.0,
        base_option_premium=650.0,
        tick_size=1.0,
        category="COMMODITY",
        segment="MCX_FO",
        market_open_time="09:00",
        market_close_time="23:30",
    ),
    "SILVER": CommoditySpec(
        key="SILVER",
        name="Silver (5kg Mini / 30kg)",
        symbol_keyword="SILVER",
        icon="🥈",
        futures_lot_size=30,
        mini_lot_size=5,
        default_lot_type="MINI",
        active_lot_size=5,
        lot_unit="kg",
        strike_step=500,
        default_sl_pts=500.0,
        default_t1_rr=2.2,
        default_t2_rr=3.5,
        atm_delta=0.50,
        base_spot_estimate=86500.0,
        base_option_premium=1400.0,
        tick_size=1.0,
        category="COMMODITY",
        segment="MCX_FO",
        market_open_time="09:00",
        market_close_time="23:30",
    ),
    "NATURALGAS": CommoditySpec(
        key="NATURALGAS",
        name="Natural Gas",
        symbol_keyword="NATURALGAS",
        icon="🔥",
        futures_lot_size=1250,
        mini_lot_size=250,
        default_lot_type="REGULAR",
        active_lot_size=1250,
        lot_unit="mmBtu",
        strike_step=5,
        default_sl_pts=3.5,
        default_t1_rr=2.2,
        default_t2_rr=3.5,
        atm_delta=0.50,
        base_spot_estimate=245.0,
        base_option_premium=14.0,
        tick_size=0.10,
        category="COMMODITY",
        segment="MCX_FO",
        market_open_time="09:00",
        market_close_time="23:30",
    ),

    # ── NSE & BSE EQUITY INDICES ───────────────────────────────────────────────
    "NIFTY": CommoditySpec(
        key="NIFTY",
        name="NSE Nifty 50",
        symbol_keyword="NIFTY",
        icon="📈",
        futures_lot_size=75,
        mini_lot_size=25,
        default_lot_type="REGULAR",
        active_lot_size=75,
        lot_unit="shares",
        strike_step=50,
        default_sl_pts=25.0,
        default_t1_rr=2.0,
        default_t2_rr=3.5,
        atm_delta=0.50,
        base_spot_estimate=24500.0,
        base_option_premium=145.0,
        tick_size=0.05,
        category="INDEX",
        segment="NSE_INDEX",
        market_open_time="09:15",
        market_close_time="15:30",
        ctt_rate=0.000625,  # 0.0625% STT on Option Sell
        exchange_fee_rate=0.000505,
    ),
    "BANKNIFTY": CommoditySpec(
        key="BANKNIFTY",
        name="NSE Bank Nifty",
        symbol_keyword="BANKNIFTY",
        icon="🏦",
        futures_lot_size=15,
        mini_lot_size=15,
        default_lot_type="REGULAR",
        active_lot_size=15,
        lot_unit="shares",
        strike_step=100,
        default_sl_pts=70.0,
        default_t1_rr=2.0,
        default_t2_rr=3.5,
        atm_delta=0.50,
        base_spot_estimate=51200.0,
        base_option_premium=320.0,
        tick_size=0.05,
        category="INDEX",
        segment="NSE_INDEX",
        market_open_time="09:15",
        market_close_time="15:30",
        ctt_rate=0.000625,
        exchange_fee_rate=0.000505,
    ),
    "FINNIFTY": CommoditySpec(
        key="FINNIFTY",
        name="NSE Fin Nifty",
        symbol_keyword="FINNIFTY",
        icon="💳",
        futures_lot_size=25,
        mini_lot_size=25,
        default_lot_type="REGULAR",
        active_lot_size=25,
        lot_unit="shares",
        strike_step=50,
        default_sl_pts=30.0,
        default_t1_rr=2.0,
        default_t2_rr=3.5,
        atm_delta=0.50,
        base_spot_estimate=23800.0,
        base_option_premium=120.0,
        tick_size=0.05,
        category="INDEX",
        segment="NSE_INDEX",
        market_open_time="09:15",
        market_close_time="15:30",
        ctt_rate=0.000625,
        exchange_fee_rate=0.000505,
    ),
    "SENSEX": CommoditySpec(
        key="SENSEX",
        name="BSE Sensex",
        symbol_keyword="SENSEX",
        icon="🏛️",
        futures_lot_size=10,
        mini_lot_size=10,
        default_lot_type="REGULAR",
        active_lot_size=10,
        lot_unit="shares",
        strike_step=100,
        default_sl_pts=100.0,
        default_t1_rr=2.0,
        default_t2_rr=3.5,
        atm_delta=0.50,
        base_spot_estimate=80500.0,
        base_option_premium=380.0,
        tick_size=0.05,
        category="INDEX",
        segment="BSE_INDEX",
        market_open_time="09:15",
        market_close_time="15:30",
        ctt_rate=0.000625,
        exchange_fee_rate=0.000050,  # BSE lower turnover charge
    ),
    "MIDCPNIFTY": CommoditySpec(
        key="MIDCPNIFTY",
        name="NSE Midcap Nifty",
        symbol_keyword="MIDCPNIFTY",
        icon="⚡",
        futures_lot_size=50,
        mini_lot_size=50,
        default_lot_type="REGULAR",
        active_lot_size=50,
        lot_unit="shares",
        strike_step=25,
        default_sl_pts=20.0,
        default_t1_rr=2.0,
        default_t2_rr=3.5,
        atm_delta=0.50,
        base_spot_estimate=12800.0,
        base_option_premium=95.0,
        tick_size=0.05,
        category="INDEX",
        segment="NSE_INDEX",
        market_open_time="09:15",
        market_close_time="15:30",
        ctt_rate=0.000625,
        exchange_fee_rate=0.000505,
    ),
}


def get_commodity_spec(comm_key: str = "CRUDEOIL") -> CommoditySpec:
    """Retrieve asset specification with fallback to CRUDEOIL."""
    clean_key = comm_key.upper().strip()
    for k, spec in COMMODITY_REGISTRY.items():
        if k == clean_key or k in clean_key or clean_key in k:
            return spec
    return COMMODITY_REGISTRY["CRUDEOIL"]


def calculate_commodity_option_charges(
    buy_premium: float,
    exit_premium: float,
    commodity_key: str = "CRUDEOIL",
    lots: int = 1
) -> Dict[str, float]:
    """Calculate exact option buying transaction charges per asset (MCX CTT vs Equity STT)."""
    spec = get_commodity_spec(commodity_key)
    qty = spec.active_lot_size * lots
    buy_turnover = buy_premium * qty
    sell_turnover = exit_premium * qty
    total_turnover = buy_turnover + sell_turnover

    brokerage = 40.0
    ctt = sell_turnover * spec.ctt_rate
    exchange_fee = total_turnover * spec.exchange_fee_rate
    sebi_fee = total_turnover * 0.000001
    gst = (brokerage + exchange_fee + sebi_fee) * 0.18
    stamp_duty = buy_turnover * 0.00003

    total_charges = round(brokerage + ctt + exchange_fee + sebi_fee + gst + stamp_duty, 2)

    return {
        "brokerage": round(brokerage, 2),
        "ctt": round(ctt, 2),
        "exchange_fee": round(exchange_fee, 2),
        "gst": round(gst, 2),
        "sebi_fee": round(sebi_fee, 2),
        "stamp_duty": round(stamp_duty, 2),
        "total_charges": total_charges,
    }

