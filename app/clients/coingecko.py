import httpx
import time
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from ..config import settings

UA = {"User-Agent": "cool-toolbox/1.0 (+https://cool-toolbox.com)"}

def _headers() -> Dict[str, str]:
    headers = dict(UA)
    if settings.coingecko_api_key:
        # CoinGecko v3 Pro header (if you have a key)
        headers["x-cg-pro-api-key"] = settings.coingecko_api_key
    return headers

def _epoch(d: date) -> int:
    # Midnight UTC timestamps (seconds)
    return int(datetime(d.year, d.month, d.day).timestamp())

def fetch_coin_list() -> List[Dict[str, Any]]:
    url = "https://api.coingecko.com/api/v3/coins/list"
    last_err = None
    for attempt in range(3):
        try:
            r = httpx.get(url, headers=_headers(), timeout=30)
            if r.status_code in (401, 403):
                raise RuntimeError(f"Unauthorized fetching {url} (API key may be required).")
            if r.status_code == 429:
                delay = float(r.headers.get("Retry-After", 1.5 * (attempt + 1)))
                time.sleep(delay); continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch CoinGecko coin list: {last_err}")

def fetch_range(cg_id: str, vs_currency: str, start: date, end: date) -> List[tuple[date, float]]:
    """
    Generic range fetch for any coin (by CoinGecko id).
    Returns a list of (date, price) with daily resolution.
    """
    url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart/range"
    params = {"vs_currency": vs_currency.lower(), "from": _epoch(start), "to": _epoch(end)}
    last_err = None
    for attempt in range(3):
        try:
            with httpx.Client(headers=_headers(), timeout=30) as client:
                r = client.get(url, params=params)
                if r.status_code in (401, 403):
                    # Treat as bad id / not accessible without key
                    raise RuntimeError(f"Unauthorized for id={cg_id}. Check id/key.")
                if r.status_code == 429:
                    delay = float(r.headers.get("Retry-After", 1.5 * (attempt + 1)))
                    time.sleep(delay); continue
                if r.status_code == 404:
                    raise RuntimeError(f"Coin id not found: {cg_id}")
                r.raise_for_status()
                data = r.json()
                points = []
                for ts_ms, price in data.get("prices", []):
                    d = datetime.utcfromtimestamp(ts_ms / 1000).date()
                    points.append((d, float(price)))
                dedup = {}
                for d, p in points:
                    dedup[d] = p
                return sorted(dedup.items(), key=lambda x: x[0])
        except Exception as e:
            last_err = e
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"CoinGecko range fetch failed: {last_err}")

