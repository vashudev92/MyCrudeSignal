"""
instrument_finder.py — Dynamic Multi-Commodity Instrument Discovery & Key Resolver
Auto-discovers active futures and options contracts for MCX Crude Oil, Gold, Silver, and Natural Gas.
"""

import requests
import pandas as pd
from datetime import datetime
import pytz
from typing import Dict, Optional

from config import IST_TIMEZONE
from commodity_registry import get_commodity_spec

IST = pytz.timezone(IST_TIMEZONE)

INSTRUMENT_SEARCH_URL = "https://api.upstox.com/v2/instruments/search"

_cached_instrument_keys: Dict[str, str] = {}
_cache_dates: Dict[str, str] = {}

# Known-good fallback keys (updated monthly at expiry)
FALLBACK_KEYS = {
    "CRUDEOIL": "MCX_FO|565899",
    "GOLD": "MCX_FO|565801",
    "SILVER": "MCX_FO|565850",
    "NATURALGAS": "MCX_FO|565920",
}


def _search_active_commodity_key(symbol_keyword: str, access_token: str) -> Optional[str]:
    """Search for the nearest-expiry MCX FUT via Upstox search API."""
    try:
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        resp = requests.get(
            INSTRUMENT_SEARCH_URL,
            params={"query": symbol_keyword},
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return None

        instruments = resp.json().get("data", [])
        if not instruments:
            return None

        now = datetime.now(IST).date()
        candidates = []
        for inst in instruments:
            symbol   = inst.get("trading_symbol", "")
            expiry_s = inst.get("expiry", "")
            itype    = inst.get("instrument_type", "")
            ikey     = inst.get("instrument_key", "")
            exchange = inst.get("exchange", "")
            name     = inst.get("name", "")

            # Only MCX futures
            if exchange != "MCX" or itype != "FUT":
                continue
            if symbol_keyword.upper() not in symbol.upper() and symbol_keyword.upper() not in name.upper():
                continue
            try:
                expiry = datetime.strptime(expiry_s, "%Y-%m-%d").date()
                if expiry >= now:
                    candidates.append((expiry, ikey, symbol))
            except Exception:
                pass

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0])
        _, key, sym = candidates[0]
        print(f"[InstrumentFinder] Active contract found: {sym} -> {key}")
        return key

    except Exception as e:
        print(f"[InstrumentFinder] Search error for {symbol_keyword}: {e}")
        return None


def get_active_crude_instrument_key(access_token: Optional[str] = None, commodity_key: str = "CRUDEOIL") -> str:
    """
    Returns the instrument key for the nearest-expiry MCX futures contract for any commodity.
    Caches the result per trading day.
    """
    global _cached_instrument_keys, _cache_dates

    spec = get_commodity_spec(commodity_key)
    c_key = spec.key
    today = datetime.now(IST).strftime("%Y-%m-%d")

    # 1. Return today's cached key
    if _cached_instrument_keys.get(c_key) and _cache_dates.get(c_key) == today:
        return _cached_instrument_keys[c_key]

    # 2. Try search API
    if access_token:
        key = _search_active_commodity_key(spec.symbol_keyword, access_token)
        if key:
            _cached_instrument_keys[c_key] = key
            _cache_dates[c_key] = today
            return key

    # 3. Return stale cache
    if _cached_instrument_keys.get(c_key):
        return _cached_instrument_keys[c_key]

    # 4. Hardcoded fallback
    fallback_key = FALLBACK_KEYS.get(c_key, "MCX_FO|565899")
    _cached_instrument_keys[c_key] = fallback_key
    _cache_dates[c_key] = today
    return fallback_key


def get_commodity_options_keys(
    access_token: str,
    commodity_key: str = "CRUDEOIL",
    expiry_date: Optional[str] = None
) -> pd.DataFrame:
    """Fetch available MCX options (CE/PE) for a given commodity and expiry."""
    spec = get_commodity_spec(commodity_key)
    try:
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        resp = requests.get(
            INSTRUMENT_SEARCH_URL,
            params={"query": spec.symbol_keyword},
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return pd.DataFrame()

        instruments = resp.json().get("data", [])
        now = datetime.now(IST).date()
        rows = []
        for inst in instruments:
            symbol   = inst.get("trading_symbol", "")
            itype    = inst.get("instrument_type", "")
            expiry_s = inst.get("expiry", "")
            ikey     = inst.get("instrument_key", "")
            strike   = inst.get("strike_price", 0)
            exchange = inst.get("exchange", "")

            if exchange != "MCX" or itype not in ("CE", "PE"):
                continue
            if spec.symbol_keyword not in symbol.upper():
                continue
            try:
                expiry = datetime.strptime(expiry_s, "%Y-%m-%d").date()
                if expiry_date:
                    target = datetime.strptime(expiry_date, "%Y-%m-%d").date()
                    if expiry != target:
                        continue
                elif expiry < now:
                    continue
                rows.append({
                    "instrument_key": ikey,
                    "trading_symbol": symbol,
                    "strike": float(strike),
                    "option_type": itype,
                    "expiry": expiry_s[:10],
                })
            except Exception:
                pass

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values(["expiry", "strike"]).reset_index(drop=True)
        return df

    except Exception as e:
        print(f"[InstrumentFinder] Options fetch error for {spec.name}: {e}")
        return pd.DataFrame()


# Alias for backward compatibility
get_crude_options_keys = get_commodity_options_keys

