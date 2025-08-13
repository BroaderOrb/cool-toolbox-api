from fastapi import APIRouter, HTTPException, Query
from datetime import date
from dateutil.relativedelta import relativedelta

from ..db import get_supabase
from ..schemas import HistoryResponse, PricePoint
from ..repos.assets_repo import get_asset_by_symbol, upsert_asset, resolve_symbol_to_cgid
from ..repos.prices_repo import (
    get_quote_id, get_existing_prices, upsert_prices, missing_ranges
)
from ..clients.coingecko import fetch_coin_list, fetch_range

router = APIRouter(prefix="/history", tags=["history"])

@router.get("/{asset_symbol}", response_model=HistoryResponse)
def get_history(
    asset_symbol: str,
    vs_currency: str = Query("USD", description="Quote currency, e.g. USD/GBP/EUR"),
    start: date | None = None,
    end: date | None = None,
):
    """
    Write-through cache: return daily closes for any asset symbol (e.g., BTC/ETH) in the given quote.
    If missing days exist in Supabase, fetch only the gaps from CoinGecko, upsert, and return the full series.
    """
    if end is None:
        end = date.today()
    if start is None:
        start = end - relativedelta(days=365)
    if start > end:
        raise HTTPException(status_code=400, detail="start must be <= end")

    sb = get_supabase()

    # ...

 # 1) Resolve asset -> (asset_id, cg_id, name). Insert if new.
    asset = get_asset_by_symbol(sb, asset_symbol)
    if not asset:
        try:
            resolved = resolve_symbol_to_cgid(asset_symbol)  # {'symbol','name','cg_id'}
        except ValueError as e:
            # Return a friendly client error instead of a 500
            raise HTTPException(status_code=400, detail=str(e))
        asset = upsert_asset(sb, symbol=resolved["symbol"], name=resolved["name"], cg_id=resolved["cg_id"])

    asset_id = asset["id"]
    cg_id = asset["cg_id"]
    symbol = asset["symbol"]

    # 2) Resolve quote -> quote_id (auto-insert if missing)
    quote_id = get_quote_id(sb, vs_currency)

    # 3) Read what we already have
    have = get_existing_prices(sb, asset_id, quote_id, start, end)

    # 4) Fill gaps from CoinGecko (range endpoint), upsert into DB
    filled_from_upstream = False
    for s, e in missing_ranges(have, start, end):
        fetched = fetch_range(cg_id, vs_currency, s, e)
        if fetched:
            upsert_prices(sb, asset_id, quote_id, fetched, source="coingecko")
            for d, p in fetched:
                have[d] = p
            filled_from_upstream = True

    # 5) Build ordered response
    ordered = sorted((d, p) for d, p in have.items() if start <= d <= end)
    prices = [PricePoint(date=d, price=p) for d, p in ordered]

    return HistoryResponse(
        asset=symbol.upper(),
        quote=vs_currency.upper(),
        start=start,
        end=end,
        prices=prices,
        filled_from_upstream=filled_from_upstream,
    )
