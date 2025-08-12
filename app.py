from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import httpx
from fastapi import HTTPException
from datetime import datetime
import time

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

# --- simple in-memory cache ---
_CACHE: dict[tuple[str, str, int, str], dict] = {}
_CACHE_TS: dict[tuple[str, str, int, str], float] = {}
TTL_SECONDS = 15 * 60  # 15 minutes

def _cache_get(key):
    ts = _CACHE_TS.get(key)
    if ts and (time.time() - ts) < TTL_SECONDS:
        return _CACHE.get(key)
    return None

def _cache_set(key, value):
    _CACHE[key] = value
    _CACHE_TS[key] = time.time()

@app.get("/btc-history")
def btc_history(days: int = 365, vs_currency: str = "usd", interval: str = "daily"):
    """
    Get BTC prices for the last N days from CoinGecko, with caching & backoff.
    """
    asset = "bitcoin"
    key = (asset, vs_currency.lower(), int(days), interval)

    # 1) serve from fresh cache if available
    cached = _cache_get(key)
    if cached:
        return cached

    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {"vs_currency": vs_currency, "days": days, "interval": interval}
    headers = {
        # Be polite; some providers throttle anonymous/no-UA requests more aggressively
        "User-Agent": "cool-toolbox/1.0 (+https://cool-toolbox.com)"
    }

    # 2) minimal retries & backoff
    last_err = None
    for attempt in range(3):
        try:
            r = httpx.get(url, params=params, headers=headers, timeout=15)
            if r.status_code == 429:
                # Backoff using Retry-After if provided, else 1.5s * attempt
                retry_after = r.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else (1.5 * (attempt + 1))
                time.sleep(delay)
                continue
            r.raise_for_status()
            data = r.json()

            prices = [
                {
                    "date": datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d"),
                    "price": price,
                }
                for ts, price in data.get("prices", [])
            ]
            payload = {
                "asset": "BTC",
                "vs_currency": vs_currency.upper(),
                "days": days,
                "interval": interval,
                "prices": prices,
                "source": "coingecko",
                "cached": False,
            }
            _cache_set(key, payload)
            return payload

        except Exception as e:
            last_err = e
            time.sleep(0.8 * (attempt + 1))

    # 3) if we failed after retries, return stale cache if we have it
    if key in _CACHE:
        payload = _CACHE[key].copy()
        payload["cached"] = True  # tell the client it’s from cache
        return payload

    raise HTTPException(status_code=503, detail=f"Upstream error: {last_err}")