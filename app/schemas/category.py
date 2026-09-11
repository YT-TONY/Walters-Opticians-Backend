# app/schemas/category.py
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

# --- BRAND SCHEMAS ---
class BrandBase(BaseModel):
    name: str
    slug: str
    logo_url: Optional[str] = None
    hero_image_url: Optional[str] = None  # Accepts uploaded path or external URL
    tagline: Optional[str] = None         # Admin tagline input
    is_popular: bool = False
    is_top_brand: bool = False
    promo_tag: Optional[str] = None
    category_type: str = "both"
    sales_count: int = 0

class BrandCreate(BrandBase):
    pass

class BrandResponse(BrandBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
    
class BrandUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    logo_url: Optional[str] = None
    hero_image_url: Optional[str] = None
    tagline: Optional[str] = None
    is_popular: Optional[bool] = None
    is_top_brand: Optional[bool] = None
    promo_tag: Optional[str] = None
    category_type: Optional[str] = None
    sales_count: Optional[int] = None

class RecommendedBrandResponse(BaseModel):
    id: int
    name: str
    slug: str
    logo_url: Optional[str] = None
    hero_image_url: Optional[str] = None
    tagline: Optional[str] = None
    category_type: str = "both"
    sales_count: int = 0
    is_popular: bool = False
    badge_text: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# --- SUBCATEGORY SCHEMAS ---
class SubCategoryBase(BaseModel):
    name: str
    slug: str
    display_order: int = 0

class SubCategoryCreate(SubCategoryBase):
    category_id: int

class SubCategoryResponse(SubCategoryBase):
    id: int
    category_id: int
    brands: List[BrandResponse] = []
    model_config = ConfigDict(from_attributes=True)

class SubCategoryUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    display_order: Optional[int] = None


# --- CATEGORY SCHEMAS ---
class CategoryBase(BaseModel):
    name: str
    slug: str
    is_main_nav: bool = True
    display_order: int = 0

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    subcategories: List[SubCategoryResponse] = []
    model_config = ConfigDict(from_attributes=True)

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    is_main_nav: Optional[bool] = None
    display_order: Optional[int] = None


# --- BANNER SCHEMAS ---
class MegaMenuBannerBase(BaseModel):
    tab_slug: str
    title: str
    subtitle: Optional[str] = None
    image_url: str
    target_url: str
    display_order: int = 0
    is_active: bool = True

class MegaMenuBannerCreate(MegaMenuBannerBase):
    pass

class MegaMenuBannerResponse(MegaMenuBannerBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
    