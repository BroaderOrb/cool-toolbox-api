from pydantic import BaseModel, Field
from datetime import date

class PricePoint(BaseModel):
    date: date
    price: float

class HistoryResponse(BaseModel):
    asset: str
    quote: str
    start: date
    end: date
    interval: str = "daily"
    source: str = "coingecko"
    prices: list[PricePoint]
    filled_from_upstream: bool = Field(default=False)
