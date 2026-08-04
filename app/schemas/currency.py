from pydantic import BaseModel
from typing import Dict

class CurrencyConversionRequest(BaseModel):
    amount_gbp: float
    target_currency: str  # USD, EUR, NGN, GBP

class CurrencyConversionResponse(BaseModel):
    amount_gbp: float
    target_currency: str
    converted_amount: float
    exchange_rate: float