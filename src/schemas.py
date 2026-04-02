from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime

class PriceHistoryOut(BaseModel):
    price: float
    scraped_at: datetime
    
    class Config:
        orm_mode = True
        from_attributes = True

class ProductBase(BaseModel):
    source: str
    external_id: str
    url: str
    brand: Optional[str]
    model: Optional[str]
    currency: str
    metadata_json: Optional[Dict[str, Any]]

class ProductOut(ProductBase):
    id: int
    price_history: List[PriceHistoryOut] = []

    class Config:
        orm_mode = True
        from_attributes = True

class AnalyticsOut(BaseModel):
    total_products: int
    totals_by_source: Dict[str, int]
    avg_price_by_brand: Dict[str, float]
