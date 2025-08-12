from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import httpx
from fastapi import HTTPException
from datetime import datetime
import time
import asyncio

app = FastAPI(title="Cool Toolbox API")

ALLOWED_ORIGINS = [
    "https://cool-toolbox.com",
    "https://www.cool-toolbox.com",
    "http://localhost:3000",  # local dev
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

import threading

# --- thread-safe in-memory cache ---
# key: (asset, vs_currency, days, interval)
_CACHE: dict[tuple[str, str, int, str], dict] = {}
_CACHE_TS: dict[tuple[str, str, int, str], float] = {}
_CACHE_LOCK = threading.RLock()
TTL_SECONDS = 15 * 60  # 15 minutes

def _cache_get(key):
    with _CACHE_LOCK:
        ts = _CACHE_TS.get(key)
        if ts and (time.time() - ts) < TTL_SECONDS:
            # return a copy and mark it as cached for this response
            out = dict(_CACHE[key])
            out["cached"] = True
            return out
        return None

def _cache_set(key, value: dict):
    with _CACHE_LOCK:
        # store a copy with cached=False; we will set True only when serving from cache
        v = dict(value)
        v["cached"] = False
        _CACHE[key] = v
        _CACHE_TS[key] = time.time()

@app.get("/btc-history")
def btc_history(days: int = 365, vs_currency: str = "usd", interval: str = "daily"):
    """
    Get BTC prices for the last N days from CoinGecko, with caching & backoff.
    """
    asset = "bitcoin"
    key = (asset, vs_currency.lower(), int(days), interval)

    # 1) Serve from fresh cache if available
    cached = _cache_get(key)
    if cached:
        return cached

    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {"vs_currency": vs_currency, "days": days, "interval": interval}
    headers = {"User-Agent": "cool-toolbox/1.0 (+https://cool-toolbox.com)"}

    last_err = None
    for attempt in range(3):
        try:
            r = httpx.get(url, params=params, headers=headers, timeout=15)
            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else (1.5 * (attempt + 1))
                time.sleep(delay)
                continue
            r.raise_for_status()
            data = r.json()

            prices = [
                {"date": datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d"), "price": price}
                for ts, price in data.get("prices", [])
            ]
            payload = {
                "asset": "BTC",
                "vs_currency": vs_currency.upper(),
                "days": days,
                "interval": interval,
                "prices": prices,
                "source": "coingecko",
                # cached field set to False when storing; turned True on read
            }
            _cache_set(key, payload)
            return payload  # first response (fresh from upstream) = cached:false

        except Exception as e:
            last_err = e
            time.sleep(0.8 * (attempt + 1))

    # 3) On failure, serve stale cache if we have it
    with _CACHE_LOCK:
        if key in _CACHE:
            stale = dict(_CACHE[key])
            stale["cached"] = True
            return stale

    raise HTTPException(status_code=503, detail=f"Upstream error: {last_err}")