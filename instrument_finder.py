"""
instrument_finder.py — Auto-discover active MCX Crude Oil futures contract key
Uses Upstox Instrument Search API with a known-good fallback key.
"""

import requests
import pandas as pd
from datetime import datetime
import pytz

from config import IST_TIMEZONE, CRUDE_SYMBOL_KEYWORD, INSTRUMENT_TYPE

IST = pytz.timezone(IST_TIMEZONE)

INSTRUMENT_SEARCH_URL = "https://api.upstox.com/v2/instruments/search"

_cached_instrument_key: str | None = None
_cache_date: str | None = None


def _search_active_crude_key(access_token: str) -> str | None:
    """Search for the nearest-expiry MCX CRUDEOIL FUT via Upstox search API."""
    try:
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        resp = requests.get(
            INSTRUMENT_SEARCH_URL,
            params={"query": "CRUDEOIL"},
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"[InstrumentFinder] Search returned {resp.status_code}: {resp.text[:200]}")
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
            if "CRUDE" not in symbol.upper() and "CRUDE" not in name.upper():
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
        print(f"[InstrumentFinder] Found active contract: {sym} -> {key}")
        return key

    except Exception as e:
        print(f"[InstrumentFinder] Search error: {e}")
        return None


def get_active_crude_instrument_key(access_token: str | None = None) -> str:
    """
    Returns the instrument key for the nearest-expiry MCX CRUDEOIL futures contract.
    Caches the result per trading day.

    Strategy:
      1. Return today's cached key (fastest)
      2. Try Upstox search API (most accurate)
      3. Return previously cached key even if from yesterday
      4. Use hardcoded known key as last resort (updated monthly at expiry)

    Args:
        access_token: Upstox access token

    Returns:
        Instrument key string, e.g. "MCX_FO|565899"
    """
    global _cached_instrument_key, _cache_date

    today = datetime.now(IST).strftime("%Y-%m-%d")

    # 1. Return today's cached key
    if _cached_instrument_key and _cache_date == today:
        return _cached_instrument_key

    # 2. Try search API
    if access_token:
        key = _search_active_crude_key(access_token)
        if key:
            _cached_instrument_key = key
            _cache_date = today
            return key

    # 3. Return stale cache
    if _cached_instrument_key:
        print("[InstrumentFinder] Using stale cached key (API unavailable).")
        return _cached_instrument_key

    # 4. Hardcoded fallback — CRUDEOIL FUT 21 SEP 26
    #    Update this key each month after expiry from Upstox instrument list
    fallback_key = "MCX_FO|565899"
    print(f"[InstrumentFinder] Using hardcoded fallback key: {fallback_key}")
    _cached_instrument_key = fallback_key
    _cache_date = today
    return fallback_key


def get_crude_options_keys(access_token: str, expiry_date: str | None = None) -> pd.DataFrame:
    """
    Fetch available CRUDEOIL options (CE/PE) for a given expiry.

    Args:
        access_token: Upstox access token
        expiry_date: 'YYYY-MM-DD', defaults to nearest expiry

    Returns:
        DataFrame with [instrument_key, trading_symbol, strike, option_type, expiry]
    """
    try:
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        resp = requests.get(
            INSTRUMENT_SEARCH_URL,
            params={"query": "CRUDEOIL"},
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
            if "CRUDE" not in symbol.upper():
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
        print(f"[InstrumentFinder] Options fetch error: {e}")
        return pd.DataFrame()
