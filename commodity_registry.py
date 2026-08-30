"""
commodity_registry.py — Multi-Commodity Specifications & Rules Registry
Defines specifications, strike intervals, lot sizes, default SL/Target, and MCX charges
for MCX Crude Oil, Gold, Silver, and Natural Gas.
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
    ctt_rate: float = 0.000125  # 0.0125% on option sell turnover (MCX CTT)
    exchange_fee_rate: float = 0.0005


COMMODITY_REGISTRY: Dict[str, CommoditySpec] = {
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
    ),
    "GOLD": CommoditySpec(
        key="GOLD",
        name="Gold (100g Mini / 1kg)",
        symbol_keyword="GOLD",
        icon="🪙",
        futures_lot_size=100,   # 100g unit / 1kg contract
        mini_lot_size=10,       # 10g unit / 100g GOLDM contract
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
    ),
    "SILVER": CommoditySpec(
        key="SILVER",
        name="Silver (5kg Mini / 30kg)",
        symbol_keyword="SILVER",
        icon="🥈",
        futures_lot_size=30,    # 30 kg contract
        mini_lot_size=5,        # 5 kg SILVERM contract
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
    ),
    "NATURALGAS": CommoditySpec(
        key="NATURALGAS",
        name="Natural Gas",
        symbol_keyword="NATURALGAS",
        icon="🔥",
        futures_lot_size=1250,  # 1,250 mmBtu
        mini_lot_size=250,      # 250 mmBtu NATGASMINI
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
    ),
}


def get_commodity_spec(comm_key: str = "CRUDEOIL") -> CommoditySpec:
    """Retrieve commodity configuration with fallback to CRUDEOIL."""
    clean_key = comm_key.upper().strip()
    for k, spec in COMMODITY_REGISTRY.items():
        if k in clean_key or clean_key in k:
            return spec
    return COMMODITY_REGISTRY["CRUDEOIL"]


def calculate_commodity_option_charges(
    buy_premium: float,
    exit_premium: float,
    commodity_key: str = "CRUDEOIL",
    lots: int = 1
) -> Dict[str, float]:
    """Calculate exact MCX option buying transaction charges per commodity."""
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
