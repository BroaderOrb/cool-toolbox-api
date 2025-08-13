from supabase import Client
from typing import Optional, Dict, Any
import httpx
from ..config import settings

TABLE = "assets"

# Curated map for common symbols
PREFERRED: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "SOL": "solana",
    "ADA": "cardano",
    "XRP": "ripple",
    "DOGE": "dogecoin",
}

def get_asset_by_symbol(sb: Client, symbol: str) -> dict | None:
    res = sb.table(TABLE).select("*").eq("symbol", symbol.upper()).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None

def upsert_asset(sb: Client, symbol: str, name: str, cg_id: str) -> dict:
    payload = {"symbol": symbol.upper(), "name": name, "cg_id": cg_id}
    res = sb.table(TABLE).upsert(payload).execute()
    return (res.data or [payload])[0]

def _headers():
    h = {"User-Agent": "cool-toolbox/1.0 (+https://cool-toolbox.com)"}
    if settings.coingecko_api_key:
        h["x-cg-pro-api-key"] = settings.coingecko_api_key
    return h

def resolve_symbol_to_cgid(symbol: str) -> dict:
    """
    Return {'symbol','name','cg_id'} by trying:
    1) curated map for common symbols,
    2) /search with exact symbol match,
    3) /coins/list fallback (exact symbol match).
    Raises if nothing found.
    """
    symu = symbol.upper()

    # 1) curated
    if symu in PREFERRED:
        cg_id = PREFERRED[symu]
        # Try to get a name from /search for nice display (optional)
        try:
            r = httpx.get("https://api.coingecko.com/api/v3/search",
                          params={"query": symu}, headers=_headers(), timeout=20)
            if r.status_code == 200:
                for c in r.json().get("coins", []):
                    if c.get("id") == cg_id:
                        return {"symbol": symu, "name": c.get("name", symu), "cg_id": cg_id}
        except Exception:
            pass
        return {"symbol": symu, "name": symu, "cg_id": cg_id}

    # 2) /search exact symbol
    try:
        r = httpx.get("https://api.coingecko.com/api/v3/search",
                      params={"query": symbol}, headers=_headers(), timeout=20)
        if r.status_code == 200:
            coins = r.json().get("coins", [])
            exacts = [c for c in coins if c.get("symbol", "").upper() == symu]
            if exacts:
                # Prefer highest market cap rank if available
                exacts.sort(key=lambda c: (c.get("market_cap_rank") or 10**9))
                c = exacts[0]
                return {"symbol": symu, "name": c.get("name", symu), "cg_id": c["id"]}
    except Exception:
        pass

    # 3) /coins/list fallback (exact symbol)
    try:
        r = httpx.get("https://api.coingecko.com/api/v3/coins/list",
                      headers=_headers(), timeout=30)
        if r.status_code == 200:
            coins = r.json()
            exacts = [c for c in coins if c.get("symbol", "").upper() == symu]
            if exacts:
                # choose id==symbol if it exists, else first
                chosen = next((c for c in exacts if c["id"].upper() == symu), exacts[0])
                return {"symbol": symu, "name": chosen.get("name", symu), "cg_id": chosen["id"]}
    except Exception:
        pass

    raise ValueError(f"Unknown or ambiguous symbol: {symbol}")
