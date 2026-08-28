"""
upstox_client.py — Upstox API v2 Client for MCX Crude Oil
Supports Analytics Token (1-year validity), Token Management,
and Automatic 28-Day Date Range Chunking for multi-month real exchange historical data.
"""

import requests
import pandas as pd
import json
import time
import os
from datetime import datetime, timedelta
from typing import Optional
import pytz

from config import (
    UPSTOX_API_KEY, UPSTOX_API_SECRET, UPSTOX_REDIRECT_URI,
    UPSTOX_ACCESS_TOKEN, TOKEN_EXPIRY_DATE,
    HISTORY_URL, INTRADAY_URL, QUOTE_URL, TOKEN_URL,
    PRIMARY_TIMEFRAME, CANDLES_TO_SHOW, IST_TIMEZONE,
    HAS_ANALYTICS_TOKEN,
)

IST = pytz.timezone(IST_TIMEZONE)


class TokenManager:
    """Manages Upstox access token storage, validity check, and loading."""

    def __init__(self):
        self._token: Optional[str] = None
        self._expiry: Optional[datetime] = None
        self._load_from_env()

    def _load_from_env(self):
        if UPSTOX_ACCESS_TOKEN:
            self._token = UPSTOX_ACCESS_TOKEN
            if TOKEN_EXPIRY_DATE:
                try:
                    self._expiry = datetime.strptime(TOKEN_EXPIRY_DATE, "%Y-%m-%d")
                except ValueError:
                    self._expiry = datetime.now() + timedelta(days=365)
            else:
                self._expiry = datetime.now() + timedelta(days=365)

    def get_token(self) -> Optional[str]:
        if self._token:
            return self._token
        self._load_from_env()
        return self._token

    def is_valid(self) -> bool:
        token = self.get_token()
        if not token:
            return False
        if self._expiry and datetime.now() > self._expiry:
            return False
        return True

    def set_token(self, token: str, expiry_days: int = 365):
        self._token = token
        self._expiry = datetime.now() + timedelta(days=expiry_days)
        self._save_to_env(token)

    def _save_to_env(self, token: str):
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()

        token_written = False
        new_lines = []
        for line in lines:
            if line.startswith("UPSTOX_ACCESS_TOKEN="):
                new_lines.append(f"UPSTOX_ACCESS_TOKEN={token}\n")
                token_written = True
            else:
                new_lines.append(line)

        if not token_written:
            new_lines.append(f"UPSTOX_ACCESS_TOKEN={token}\n")

        with open(env_path, "w") as f:
            f.writelines(new_lines)


class UpstoxClient:
    """Upstox API v2 Client for MCX Crude Oil Market Data."""

    def __init__(self, token_manager: Optional[TokenManager] = None):
        self.token_manager = token_manager or TokenManager()

    def _headers(self) -> dict:
        token = self.token_manager.get_token()
        headers = {
            "Accept": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def get_historical_candles(
        self,
        instrument_key: str,
        interval: str = "30minute",
        days_back: int = 4,
        to_date: Optional[str] = None,
        from_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV candles from Upstox API v2.
        Automatically chunks date ranges > 25 days into separate API requests
        to bypass Upstox's UDAPI1148 30-day limit and retrieve full real exchange history.
        """
        try:
            if not to_date:
                to_date = datetime.now(IST).strftime("%Y-%m-%d")
            if not from_date:
                from_date = (datetime.now(IST) - timedelta(days=days_back)).strftime("%Y-%m-%d")

            start_dt = datetime.strptime(from_date, "%Y-%m-%d")
            end_dt = datetime.strptime(to_date, "%Y-%m-%d")

            # If requesting Daily candles or span <= 25 days, single request is sufficient
            if interval in ("day", "week", "month") or (end_dt - start_dt).days <= 25:
                return self._fetch_single_candle_chunk(instrument_key, interval, from_date, to_date)

            # For multi-month intraday requests, chunk into 25-day blocks
            all_chunks = []
            curr_end = end_dt

            while curr_end > start_dt:
                curr_start = max(start_dt, curr_end - timedelta(days=25))
                f_str = curr_start.strftime("%Y-%m-%d")
                t_str = curr_end.strftime("%Y-%m-%d")

                df_chunk = self._fetch_single_candle_chunk(instrument_key, interval, f_str, t_str)
                if not df_chunk.empty:
                    all_chunks.append(df_chunk)

                curr_end = curr_start - timedelta(days=1)

            if all_chunks:
                full_df = pd.concat(all_chunks, ignore_index=True)
                full_df = full_df.drop_duplicates(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
                return full_df

            return pd.DataFrame()

        except Exception as e:
            print(f"[UpstoxClient] Error fetching candles: {e}")
            return pd.DataFrame()

    def _fetch_single_candle_chunk(
        self,
        instrument_key: str,
        interval: str,
        from_date: str,
        to_date: str
    ) -> pd.DataFrame:
        """Fetches a single chunk of candles (< 28 days) from Upstox API."""
        try:
            url = f"{HISTORY_URL}/{instrument_key}/{interval}/{to_date}/{from_date}"
            resp = requests.get(url, headers=self._headers(), timeout=10)
            if not resp.ok:
                return pd.DataFrame()

            data = resp.json()
            candles = data.get("data", {}).get("candles", [])
            if not candles:
                return pd.DataFrame()

            df = pd.DataFrame(candles, columns=["datetime", "open", "high", "low", "close", "volume", "oi"])
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.sort_values("datetime").reset_index(drop=True)
            df = df[["datetime", "open", "high", "low", "close", "volume"]]
            df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric)
            return df
        except Exception:
            return pd.DataFrame()

    def get_intraday_candles(
        self,
        instrument_key: str,
        interval: str = "30minute"
    ) -> pd.DataFrame:
        """
        Fetch today's candles using historical-candle endpoint with today's date range.
        Upstox intraday endpoint is unreliable — this method uses the stable historical API.
        """
        today_str = datetime.now(IST).strftime("%Y-%m-%d")
        three_days_ago = (datetime.now(IST) - timedelta(days=3)).strftime("%Y-%m-%d")
        return self.get_historical_candles(
            instrument_key=instrument_key,
            interval=interval,
            from_date=three_days_ago,
            to_date=today_str,
        )

    def get_live_quote(self, instrument_key: str) -> dict:
        """Fetch real-time LTP, OHLC, and market depth for an instrument."""
        try:
            params = {"instrument_key": instrument_key}
            resp = requests.get(QUOTE_URL, params=params, headers=self._headers(), timeout=5)
            if not resp.ok:
                print(f"[UpstoxClient] Quote error ({resp.status_code}): {resp.text[:200]}")
                return {}

            data = resp.json()
            quote_data = data.get("data", {})
            clean_key = instrument_key.replace("|", ":")
            quote = quote_data.get(clean_key, quote_data.get(instrument_key, {}))
            if not quote:
                keys = list(quote_data.keys())
                if keys:
                    quote = quote_data[keys[0]]

            if not quote:
                return {}

            ohlc = quote.get("ohlc", {})
            return {
                "ltp": float(quote.get("last_price", 0.0)),
                "open": float(ohlc.get("open", 0.0)),
                "high": float(ohlc.get("high", 0.0)),
                "low": float(ohlc.get("low", 0.0)),
                "close": float(ohlc.get("close", 0.0)),
                "prev_close": float(ohlc.get("close", quote.get("last_price", 0.0))),
                "volume": int(quote.get("volume", 0)),
                "oi": int(quote.get("oi", 0)),
                "timestamp": quote.get("timestamp", ""),
            }

        except Exception as e:
            print(f"[UpstoxClient] Error fetching quote: {e}")
            return {}

    def get_previous_day_ohlc(self, instrument_key: str) -> dict:
        """Fetch previous completed day's High, Low, Close for standard Pivot calculation."""
        try:
            today = datetime.now(IST).date()
            from_date = (today - timedelta(days=10)).strftime("%Y-%m-%d")
            to_date = today.strftime("%Y-%m-%d")

            df = self.get_historical_candles(
                instrument_key=instrument_key,
                interval="day",
                from_date=from_date,
                to_date=to_date,
            )
            if df.empty:
                return {}

            df["date"] = df["datetime"].dt.date
            past_days = df[df["date"] < today]

            if past_days.empty:
                if len(df) >= 2:
                    last_row = df.iloc[-2]
                elif len(df) == 1:
                    last_row = df.iloc[0]
                else:
                    return {}
            else:
                last_row = past_days.iloc[-1]

            return {
                "high": float(last_row["high"]),
                "low": float(last_row["low"]),
                "close": float(last_row["close"]),
                "open": float(last_row["open"]),
                "date": str(last_row.get("date", last_row["datetime"])),
            }

        except Exception as e:
            print(f"[UpstoxClient] Error fetching prev day OHLC: {e}")
            return {}


_client_instance: Optional[UpstoxClient] = None

def get_client() -> UpstoxClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = UpstoxClient()
    return _client_instance
