#app/schemas/category.py
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

# --- BRAND SCHEMAS ---
class BrandBase(BaseModel):
    name: str
    slug: str
    is_popular: bool = False

class BrandCreate(BrandBase):
    pass

class BrandResponse(BrandBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
    
class BrandUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    is_popular: Optional[bool] = None

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