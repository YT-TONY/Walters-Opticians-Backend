from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api import deps
from app.models.categories import Category, SubCategory, Brand
from app.schemas.category import CategoryResponse, CategoryCreate
from app.schemas.category import (
    CategoryUpdate, 
    SubCategoryCreate, SubCategoryUpdate, SubCategoryResponse,
    BrandCreate, BrandUpdate, BrandResponse
)

router = APIRouter()

@router.get("/tree", response_model=List[CategoryResponse])
def get_category_tree(db: Session = Depends(deps.get_db)):
    """
    Fetch the full category tree including subcategories and mapped brands.
    This powers the dynamic mega-menu on the frontend.
    """
    categories = db.query(Category).order_by(Category.display_order).all()
    return categories

# Example Admin Endpoint (Protect this with your admin dependency)
@router.post("/", response_model=CategoryResponse)
def create_category(
    category_in: CategoryCreate, 
    db: Session = Depends(deps.get_db),
    # current_user = Depends(deps.get_current_admin_user) # Uncomment when ready
):
    """
    Create a new main category (Admin only).
    """
    db_category = db.query(Category).filter(Category.slug == category_in.slug).first()
    if db_category:
        raise HTTPException(status_code=400, detail="Category with this slug already exists.")
    
    new_category = Category(**category_in.model_dump())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


# ==========================================
# MAIN CATEGORIES: EDIT & DELETE
# ==========================================

@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: Session = Depends(deps.get_db),
    # current_user = Depends(deps.get_current_admin_user)
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
    db: Session = Depends(deps.get_db),
    # current_user = Depends(deps.get_current_admin_user)
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
    # Verify parent category exists
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
    """Link a brand to a specific subcategory (e.g. mapping 'Ray-Ban' to 'Sunglasses -> Lifestyle')."""
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
# Note: You would add similar POST/PUT/DELETE endpoints here for Subcategories and Brands.