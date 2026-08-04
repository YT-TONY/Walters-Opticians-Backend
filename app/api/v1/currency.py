from fastapi import APIRouter, HTTPException
import httpx
from app.schemas.currency import CurrencyConversionRequest, CurrencyConversionResponse

router = APIRouter(prefix="/currency", tags=["Multi-Currency"])

# Static conversion rates fallback (in case external API fails)
FALLBACK_RATES = {
    "GBP": 1.0,
    "USD": 1.28,
    "EUR": 1.18,
    "NGN": 2000.0
}

@router.post("/convert", response_model=CurrencyConversionResponse)
async def convert_currency(request: CurrencyConversionRequest):
    target = request.target_currency.upper()
    rate = FALLBACK_RATES.get(target)
    
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get("https://open.er-api.com/v6/latest/GBP")
            if res.status_code == 200:
                rates = res.json().get("rates", {})
                if target in rates:
                    rate = rates[target]
    except Exception:
        pass  # Gracefully fall back to pre-defined exchange rates

    if not rate:
        raise HTTPException(status_code=400, detail=f"Unsupported currency: {target}")

    converted = round(request.amount_gbp * rate, 2)
    return {
        "amount_gbp": request.amount_gbp,
        "target_currency": target,
        "converted_amount": converted,
        "exchange_rate": rate
    }