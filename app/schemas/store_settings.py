from typing import Dict, Optional
from pydantic import BaseModel


class StoreSettingsUpdate(BaseModel):
    standard_lens_fee: Optional[float] = None
    eye_exam_fee: Optional[float] = None
    uk_base_shipping: Optional[float] = None
    eu_base_shipping: Optional[float] = None
    intl_base_shipping: Optional[float] = None


class StoreSettingsResponse(BaseModel):
    rates: Dict[str, float]