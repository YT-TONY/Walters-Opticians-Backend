# app/api/v1/categories.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
import shutil
import os
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api import deps
from app.models.categories import Category, SubCategory, Brand, MegaMenuBanner
from app.schemas.category import (
    CategoryCreate, CategoryUpdate, CategoryResponse,
    SubCategoryCreate, SubCategoryUpdate, SubCategoryResponse,
    BrandCreate, BrandUpdate, BrandResponse,
    MegaMenuBannerResponse, MegaMenuBannerCreate, RecommendedBrandResponse
)

UPLOAD_DIR = "public/IMAGES/BRAND LOGO"
HERO_UPLOAD_DIR = "public/IMAGES/BRAND HERO"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(HERO_UPLOAD_DIR, exist_ok=True)

router = APIRouter()

@router.get("/tree", response_model=List[CategoryResponse])
def get_category_tree(db: Session = Depends(deps.get_db)):
    """
    Fetch the full category tree including subcategories and mapped brands.
    This powers the dynamic mega-menu on the frontend.
    """
    categories = db.query(Category).order_by(Category.display_order).all()
    return categories


# ==========================================
# BRANDS DIRECT ENDPOINTS (FOR BRANDS TAB)
# ==========================================


@router.post("/brands/{brand_id}/upload-logo")
async def upload_brand_logo(
    brand_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db)
):
    """
    Upload a brand logo (PNG, recommended 600x300 canvas).
    Updates brand.logo_url directly.
    """
    if not file.content_type.startswith("image/png"):
        raise HTTPException(status_code=400, detail="Only transparent PNG files are allowed for brand logos.")

    db_brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not db_brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Generate standardized filename
    filename = f"{db_brand.slug}_logo.png"
    file_path = os.path.join(UPLOAD_DIR, filename)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Update logo URL path
    db_brand.logo_url = f"/IMAGES/BRAND LOGO/{filename}"
    db.commit()
    db.refresh(db_brand)

    return {"message": "Logo uploaded successfully", "logo_url": db_brand.logo_url}


@router.post("/brands/{brand_id}/upload-hero")
async def upload_brand_hero(
    brand_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db)
):
    """
    Upload a brand hero banner image (JPEG, PNG, WEBP).
    Updates brand.hero_image_url directly with local static asset path.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed for brand banners.")

    db_brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not db_brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{db_brand.slug}_hero.{ext}"
    file_path = os.path.join(HERO_UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db_brand.hero_image_url = f"/IMAGES/BRAND HERO/{filename}"
    db.commit()
    db.refresh(db_brand)

    return {"message": "Hero banner uploaded successfully", "hero_image_url": db_brand.hero_image_url}


@router.get("/brands/all", response_model=List[BrandResponse])
def get_all_brands(
    category_type: Optional[str] = None,  # "glasses", "sunglasses", or None for all
    top_only: bool = False,
    db: Session = Depends(deps.get_db)
):
    """
    Fetch all brands for the dedicated Brands mega-menu tab.
    Supports filtering by category_type and sorting Top Brands by sales volume.
    """
    query = db.query(Brand)
    
    if category_type:
        query = query.filter(Brand.category_type.in_([category_type, "both"]))
        
    if top_only:
        query = query.filter((Brand.is_top_brand == True) | (Brand.is_popular == True)).order_by(Brand.sales_count.desc())
    else:
        query = query.order_by(Brand.name.asc())
        
    return query.all()


@router.get("/brands/recommended", response_model=List[RecommendedBrandResponse])
def get_recommended_brands(
    user_searches: Optional[str] = None,  # Comma-separated search terms or slugs
    db: Session = Depends(deps.get_db)
):
    """
    Computes personalized brand recommendations based on user search activity
    combined with overall sales volume. Uses dynamic admin database fields.
    """
    searched_slugs = []
    if user_searches:
        searched_slugs = [s.strip().lower() for s in user_searches.split(",") if s.strip()]

    recommended_brands = []

    # 1. Match brands based on search history keywords or slugs
    if searched_slugs:
        for query_term in searched_slugs[:3]:
            matched = db.query(Brand).filter(
                (Brand.slug.ilike(f"%{query_term}%")) | (Brand.name.ilike(f"%{query_term}%"))
            ).first()
            if matched and matched not in recommended_brands:
                recommended_brands.append(matched)

    # 2. Backfill up to 3 items using top sales_count and popular status
    if len(recommended_brands) < 3:
        existing_ids = {b.id for b in recommended_brands}
        fallback_query = db.query(Brand)
        if existing_ids:
            fallback_query = fallback_query.filter(Brand.id.not_in(existing_ids))
        
        top_sales = fallback_query.order_by(
            Brand.sales_count.desc(), 
            Brand.is_popular.desc()
        ).limit(3 - len(recommended_brands)).all()
        
        recommended_brands.extend(top_sales)

    # Default fallback images if admin hasn't configured custom hero_image_url or tagline yet
    DEFAULT_HEROES = [
        "/IMAGES/HOMEPAGE/LUXURY_BANNER.jpg",
        "/IMAGES/HOMEPAGE/BUDGET_BANNER.jpg",
        "/IMAGES/HOMEPAGE/DISCOUNT_BANNER.jpg"
    ]

    result = []
    for idx, brand in enumerate(recommended_brands[:3]):
        # Dynamic precedence: Admin database field -> Fallback local asset
        hero_url = brand.hero_image_url or DEFAULT_HEROES[idx % len(DEFAULT_HEROES)]
        tagline_str = brand.tagline or f"Explore Precision Crafted {brand.name} Eyewear"

        result.append(
            RecommendedBrandResponse(
                id=brand.id,
                name=brand.name,
                slug=brand.slug,
                logo_url=brand.logo_url,
                hero_image_url=hero_url,
                tagline=tagline_str,
                category_type=brand.category_type or "both",
                sales_count=brand.sales_count,
                is_popular=brand.is_popular,
                badge_text=brand.promo_tag or ("RECOMMENDED" if idx == 0 else "POPULAR")
            )
        )

    return result

# ==========================================
# MEGA-MENU BANNERS (ADMIN CONTROLLED)
# ==========================================

@router.get("/banners/{tab_slug}", response_model=List[MegaMenuBannerResponse])
def get_banners_for_tab(tab_slug: str, db: Session = Depends(deps.get_db)):
    """Fetch active dynamic side banners for a specific mega-menu tab."""
    return db.query(MegaMenuBanner).filter(
        MegaMenuBanner.tab_slug == tab_slug,
        MegaMenuBanner.is_active == True
    ).order_by(MegaMenuBanner.display_order).all()

@router.post("/banners", response_model=MegaMenuBannerResponse)
def create_banner(banner_in: MegaMenuBannerCreate, db: Session = Depends(deps.get_db)):
    """Create a new mega-menu promotional banner (Admin)."""
    new_banner = MegaMenuBanner(**banner_in.model_dump())
    db.add(new_banner)
    db.commit()
    db.refresh(new_banner)
    return new_banner

# ==========================================
# MAIN CATEGORIES: CREATE, EDIT & DELETE
# ==========================================

@router.post("", response_model=CategoryResponse)
def create_category(
    category_in: CategoryCreate, 
    db: Session = Depends(deps.get_db)
):
    """Create a new main category (Admin only)."""
    db_category = db.query(Category).filter(Category.slug == category_in.slug).first()
    if db_category:
        raise HTTPException(status_code=400, detail="Category with this slug already exists.")
    
    new_category = Category(**category_in.model_dump())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: Session = Depends(deps.get_db)
):
    """Update a main category."""
    db_category = db.query(Category).filter(Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = category_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_category, key, value)
        
    db.commit()
    db.refresh(db_category)
    return db_category

@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(deps.get_db)
):
    """Delete a main category (cascades to subcategories)."""
    db_category = db.query(Category).filter(Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    db.delete(db_category)
    db.commit()
    return {"message": "Category deleted successfully"}


# ==========================================
# SUBCATEGORIES: CREATE, EDIT & DELETE
# ==========================================

@router.post("/subcategories", response_model=SubCategoryResponse)
def create_subcategory(
    sub_in: SubCategoryCreate,
    db: Session = Depends(deps.get_db)
):
    """Create a new subcategory."""
    parent_cat = db.query(Category).filter(Category.id == sub_in.category_id).first()
    if not parent_cat:
        raise HTTPException(status_code=404, detail="Parent category not found")

    new_sub = SubCategory(**sub_in.model_dump())
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)
    return new_sub

@router.put("/subcategories/{subcategory_id}", response_model=SubCategoryResponse)
def update_subcategory(
    subcategory_id: int,
    sub_in: SubCategoryUpdate,
    db: Session = Depends(deps.get_db)
):
    """Update a subcategory."""
    db_sub = db.query(SubCategory).filter(SubCategory.id == subcategory_id).first()
    if not db_sub:
        raise HTTPException(status_code=404, detail="Subcategory not found")
        
    update_data = sub_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_sub, key, value)
        
    db.commit()
    db.refresh(db_sub)
    return db_sub

@router.delete("/subcategories/{subcategory_id}")
def delete_subcategory(
    subcategory_id: int,
    db: Session = Depends(deps.get_db)
):
    """Delete a subcategory."""
    db_sub = db.query(SubCategory).filter(SubCategory.id == subcategory_id).first()
    if not db_sub:
        raise HTTPException(status_code=404, detail="Subcategory not found")
        
    db.delete(db_sub)
    db.commit()
    return {"message": "Subcategory deleted successfully"}


# ==========================================
# BRANDS: CREATE, EDIT, DELETE & LINKING
# ==========================================

@router.post("/brands", response_model=BrandResponse)
def create_brand(
    brand_in: BrandCreate,
    db: Session = Depends(deps.get_db)
):
    """Create a new brand."""
    db_brand = db.query(Brand).filter(Brand.slug == brand_in.slug).first()
    if db_brand:
        raise HTTPException(status_code=400, detail="Brand slug already exists")

    new_brand = Brand(**brand_in.model_dump())
    db.add(new_brand)
    db.commit()
    db.refresh(new_brand)
    return new_brand

@router.put("/brands/{brand_id}", response_model=BrandResponse)
def update_brand(
    brand_id: int,
    brand_in: BrandUpdate,
    db: Session = Depends(deps.get_db)
):
    """Update a brand."""
    db_brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not db_brand:
        raise HTTPException(status_code=404, detail="Brand not found")
        
    update_data = brand_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_brand, key, value)
        
    db.commit()
    db.refresh(db_brand)
    return db_brand

@router.get("/brands/by-slug/{slug}", response_model=BrandResponse)
def get_brand_by_slug(
    slug: str,
    db: Session = Depends(deps.get_db)
):
    """Fetch a single brand by its URL slug (for /brands/:brandSlug PDP pages)."""
    db_brand = db.query(Brand).filter(Brand.slug == slug).first()
    if not db_brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return db_brand

@router.delete("/brands/{brand_id}")
def delete_brand(
    brand_id: int,
    db: Session = Depends(deps.get_db)
):
    """Delete a brand."""
    db_brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not db_brand:
        raise HTTPException(status_code=404, detail="Brand not found")
        
    db.delete(db_brand)
    db.commit()
    return {"message": "Brand deleted successfully"}


# --- BRAND TO SUBCATEGORY MAPPING (Many-to-Many) ---

@router.post("/subcategories/{subcategory_id}/brands/{brand_id}")
def link_brand_to_subcategory(
    subcategory_id: int,
    brand_id: int,
    db: Session = Depends(deps.get_db)
):
    """Link a brand to a specific subcategory."""
    db_sub = db.query(SubCategory).filter(SubCategory.id == subcategory_id).first()
    db_brand = db.query(Brand).filter(Brand.id == brand_id).first()
    
    if not db_sub or not db_brand:
        raise HTTPException(status_code=404, detail="Subcategory or Brand not found")
        
    if db_brand in db_sub.brands:
        raise HTTPException(status_code=400, detail="Brand is already linked to this subcategory")
        
    db_sub.brands.append(db_brand)
    db.commit()
    return {"message": f"Successfully linked {db_brand.name} to {db_sub.name}"}

@router.delete("/subcategories/{subcategory_id}/brands/{brand_id}")
def unlink_brand_from_subcategory(
    subcategory_id: int,
    brand_id: int,
    db: Session = Depends(deps.get_db)
):
    """Remove a brand from a specific subcategory."""
    db_sub = db.query(SubCategory).filter(SubCategory.id == subcategory_id).first()
    db_brand = db.query(Brand).filter(Brand.id == brand_id).first()
    
    if not db_sub or not db_brand:
        raise HTTPException(status_code=404, detail="Subcategory or Brand not found")
        
    if db_brand not in db_sub.brands:
        raise HTTPException(status_code=400, detail="Brand is not linked to this subcategory")
        
    db_sub.brands.remove(db_brand)
    db.commit()
    return {"message": f"Successfully removed {db_brand.name} from {db_sub.name}"}