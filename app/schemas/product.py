# app/schemas/product.py

from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.enums import ProductCategory, ReplacementFrequency, LensDesign

class ContactLensDetailResponse(BaseModel):
    id: int
    replacement_frequency: ReplacementFrequency
    lens_design: LensDesign
    pack_size: int
    water_content: Optional[float] = None
    material_type: Optional[str] = None
    base_curve_options: str
    diameter_options: str
    min_power: float
    max_power: float

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    category: Optional[ProductCategory] = ProductCategory.OPTICAL_FRAMES
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
    category: Optional[ProductCategory] = None
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
    contact_lens_detail: Optional[ContactLensDetailResponse] = None

    class Config:
        from_attributes = True

# ==========================================
# SEARCH, AUTOCOMPLETE & FACET SCHEMAS
# ==========================================

class CatalogFacets(BaseModel):
    min_price: float = 0.0
    max_price: float = 0.0
    available_brands: List[str] = Field(default_factory=list)
    available_shapes: List[str] = Field(default_factory=list)
    available_materials: List[str] = Field(default_factory=list)
    available_genders: List[str] = Field(default_factory=list)

class PaginatedCatalogWithFacetsResponse(BaseModel):
    items: List[ProductResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    facets: CatalogFacets
    did_you_mean: Optional[str] = None
    original_query: Optional[str] = None

class BrandSuggestionItem(BaseModel):
    name: str
    slug: str
    logo_url: Optional[str] = None

class ProductSuggestionItem(BaseModel):
    id: int
    name: str
    brand: str
    image_url: str
    price_full_gbp: float

class SearchSuggestionsResponse(BaseModel):
    categories: List[str] = Field(default_factory=list)
    brands: List[BrandSuggestionItem] = Field(default_factory=list)
    products: List[ProductSuggestionItem] = Field(default_factory=list)