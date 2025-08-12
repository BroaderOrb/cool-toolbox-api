from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import httpx
from fastapi import HTTPException
from datetime import datetime

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

@app.get("/btc-history")
def btc_history(days: int = 365):
    """Get Bitcoin daily prices for the last N days."""
    url = f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}

    try:
        r = httpx.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    prices = [
        {"date": datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d"), "price": price}
        for ts, price in data["prices"]
    ]
    return {"currency": "BTC", "vs_currency": "USD", "days": days, "prices": prices}

