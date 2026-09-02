#app/schemas/product.py
from pydantic import BaseModel, Field
from typing import Optional, List

class ProductBase(BaseModel):
    model_code: Optional[str] = None
    name: str
    brand: str
    gender: Optional[str] = "unisex"
    shape: str
    color_description: str
    color_code: Optional[str] = None
    frame_type: str = "full-rim"
    description: Optional[str] = None
    frame_material: Optional[str] = "Plastic"
    lens_material: Optional[str] = "Demo Lens"
    lens_color: Optional[str] = "Transparent"
    glass_base: Optional[str] = "Base 4"
    polarized: Optional[bool] = False
    photochromic: Optional[bool] = False
    gradables: Optional[bool] = False
    
    # Dynamic Optical Sizing
    lens_width: Optional[float] = None
    bridge_width: Optional[float] = None
    temple_length: Optional[float] = None
    lens_height: Optional[float] = None
    
    # Sizes & Size Chart URL
    sizes: Optional[List[str]] = Field(default_factory=list)
    size_chart_url: Optional[str] = None

    price_full_gbp: float
    allow_frame_only: bool = True
    price_frame_only_gbp: float
    image_url: str
    gallery: List[str] = Field(default_factory=list)
    stock_quantity: int = Field(default=15, ge=0)
    is_active: bool = True
    is_featured: bool = False
    is_bestseller: bool = False

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    model_code: Optional[str] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    gender: Optional[str] = None
    shape: Optional[str] = None
    color_description: Optional[str] = None
    color_code: Optional[str] = None
    frame_type: Optional[str] = None
    description: Optional[str] = None
    frame_material: Optional[str] = None
    lens_material: Optional[str] = None
    lens_color: Optional[str] = None
    glass_base: Optional[str] = None
    polarized: Optional[bool] = None
    photochromic: Optional[bool] = None
    gradables: Optional[bool] = None
    lens_width: Optional[float] = None
    bridge_width: Optional[float] = None
    temple_length: Optional[float] = None
    lens_height: Optional[float] = None
    sizes: Optional[List[str]] = None
    size_chart_url: Optional[str] = None
    price_full_gbp: Optional[float] = None
    allow_frame_only: Optional[bool] = None
    price_frame_only_gbp: Optional[float] = None
    image_url: Optional[str] = None
    gallery: Optional[List[str]] = None
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_bestseller: Optional[bool] = None

class ProductResponse(ProductBase):
    id: int

    class Config:
        from_attributes = True