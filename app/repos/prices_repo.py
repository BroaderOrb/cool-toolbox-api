from datetime import date, timedelta
from supabase import Client
from typing import Iterable

TABLE = "asset_quotes"

def get_quote_id(sb: Client, code: str) -> int:
    q = sb.table("quotes").select("id").eq("code", code.upper()).limit(1).execute()
    rows = q.data or []
    if not rows:
        # auto-insert unknown quote
        ins = sb.table("quotes").insert({"code": code.upper(), "name": code.upper(), "decimals": 2}).execute()
        return ins.data[0]["id"]
    return rows[0]["id"]

def get_existing_prices(sb: Client, asset_id: int, quote_id: int, start: date, end: date) -> dict[date, float]:
    res = (
        sb.table(TABLE).select("ts, price")
        .eq("asset_id", asset_id).eq("quote_id", quote_id)
        .gte("ts", start.isoformat()).lte("ts", end.isoformat())
        .order("ts")
        .execute()
    )
    out: dict[date, float] = {}
    for row in res.data or []:
        out[date.fromisoformat(row["ts"])] = float(row["price"])
    return out

def upsert_prices(sb: Client, asset_id: int, quote_id: int, rows: Iterable[tuple[date, float]], source: str = "coingecko") -> None:
    payload = [
        {"asset_id": asset_id, "quote_id": quote_id, "ts": d.isoformat(), "price": p, "source": source}
        for d, p in rows
    ]
    if payload:
        sb.table(TABLE).upsert(payload).execute()

def date_range(start: date, end: date):
    n = (end - start).days
    for i in range(n + 1):
        yield start + timedelta(days=i)

def missing_ranges(have: dict[date, float], start: date, end: date):
    gaps = []
    cur = None
    for d in date_range(start, end):
        if d not in have:
            cur = d if cur is None else cur
        else:
            if cur is not None:
                gaps.append((cur, d - timedelta(days=1)))
                cur = None
    if cur is not None:
        gaps.append((cur, end))
    return gaps
