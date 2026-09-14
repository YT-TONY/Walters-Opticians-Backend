# app/api/v1/products.py
from typing import List, Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, require_admin
from app.models.enums import ProductCategory
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products & Catalog"])


class PaginatedCatalogResponse(BaseModel):
    items: List[ProductResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    available_brands: List[str]


# ==========================================
# FLEXIBLE LOOKUP HELPER
# ==========================================


def find_product(identifier: str, db: Session) -> Optional[Product]:
    """
    Finds a product by numeric ID if identifier contains digits, 
    otherwise falls back to a case-insensitive exact name match (URL-decoded).
    Eagerly loads contact_lens_detail.
    """
    clean_identifier = unquote(identifier).strip()
    query = db.query(Product).options(joinedload(Product.contact_lens_detail))

    if clean_identifier.isdigit():
        product = query.filter(Product.id == int(clean_identifier)).first()
        if product:
            return product

    return query.filter(Product.name.ilike(clean_identifier)).first()


# ==========================================
# PUBLIC CATALOG ENDPOINTS
# ==========================================


@router.get("/brands", response_model=List[str])
def list_available_brands(db: Session = Depends(get_db)):
    """
    Fetches all distinct brand names currently present in the database catalog.
    """
    results = db.query(Product.brand).filter(Product.brand.isnot(None), Product.brand != "").distinct().all()
    brands = sorted([r[0] for r in results if r[0]])
    return brands


@router.get("/", response_model=List[ProductResponse])
def list_products(
    q: Optional[str] = Query(None, description="Search term for name, brand, shape, or color"),
    category: Optional[ProductCategory] = Query(None, description="Filter by category: optical_frames, sunglasses, contact_lenses, lens_care"),
    brand: Optional[str] = Query(None, description="Filter by brand name"),
    shape: Optional[str] = Query(None, description="Filter by frame shape"),
    color: Optional[str] = Query(None, description="Filter by color description"),
    tier: Optional[str] = Query(None, description="Filter tier: luxury, bridge, budget"),
    is_bestseller: Optional[bool] = Query(None, description="Filter bestseller items"),
    min_price: Optional[float] = Query(None, description="Minimum price filter in GBP"),
    max_price: Optional[float] = Query(None, description="Maximum price filter in GBP"),
    in_stock_only: bool = Query(False, description="Filter only products currently in stock"),
    sort_by: Optional[str] = Query("newest", description="Sort order: price_asc, price_desc, newest"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Retrieve products catalog with multi-attribute filtering, search, category filtering, and pagination.
    Eagerly loads contact lens metadata.
    """
    query = db.query(Product).options(joinedload(Product.contact_lens_detail)).filter(Product.is_active == True)

    if category:
        query = query.filter(Product.category == category)

    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            (Product.name.ilike(search_pattern)) |
            (Product.brand.ilike(search_pattern)) |
            (Product.shape.ilike(search_pattern)) |
            (Product.color_description.ilike(search_pattern))
        )

    if brand:
        query = query.filter(Product.brand.ilike(brand.strip()))
    if shape:
        query = query.filter(Product.shape.ilike(shape.strip()))
    if color:
        query = query.filter(Product.color_description.ilike(color.strip()))
    if is_bestseller is not None:
        query = query.filter(Product.is_bestseller == is_bestseller)

    # Dynamic Price Tier Filtering
    if tier:
        tier_lower = tier.lower().strip()
        if tier_lower == "luxury":
            query = query.filter(Product.price_full_gbp >= 200.0)
        elif tier_lower == "budget":
            query = query.filter(Product.price_full_gbp <= 100.0)
        elif tier_lower == "bridge":
            query = query.filter(Product.price_full_gbp > 100.0, Product.price_full_gbp < 200.0)

    if min_price is not None:
        query = query.filter(Product.price_full_gbp >= min_price)
    if max_price is not None:
        query = query.filter(Product.price_full_gbp <= max_price)
    if in_stock_only:
        query = query.filter(Product.stock_quantity > 0)

    if sort_by == "price_asc":
        query = query.order_by(Product.price_full_gbp.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Product.price_full_gbp.desc())
    else:
        query = query.order_by(Product.id.desc())

    return query.offset(skip).limit(limit).all()


@router.get("/admin/catalog", response_model=PaginatedCatalogResponse)
def get_admin_product_catalog(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    brand: Optional[str] = Query(default=None),
    shape: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    """
    Optimized paginated query for large inventory sizes with dynamic brand list.
    """
    query = db.query(Product).options(joinedload(Product.contact_lens_detail))

    if brand and brand.lower() != "all":
        query = query.filter(func.lower(Product.brand) == brand.lower())

    if shape and shape.lower() != "all":
        query = query.filter(func.lower(Product.shape) == shape.lower())

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Product.name.ilike(search_pattern),
                Product.brand.ilike(search_pattern),
                Product.color_description.ilike(search_pattern)
            )
        )

    total_count = query.count()
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    products = query.order_by(Product.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Extract dynamic brands from database
    brand_results = db.query(Product.brand).filter(Product.brand.isnot(None), Product.brand != "").distinct().all()
    available_brands = sorted([b[0] for b in brand_results if b[0]])

    return {
        "items": products,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "available_brands": available_brands
    }


@router.get("/{identifier}", response_model=ProductResponse)
def get_product(identifier: str, db: Session = Depends(get_db)):
    """
    Get detailed information for a specific product by numeric ID or exact Name.
    """
    product = find_product(identifier, db)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{identifier}' not found."
        )
    return product


# ==========================================
# ADMIN-ONLY PRODUCT MANAGEMENT
# ==========================================


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    """
    Add a new product to the catalog (Admin only).
    """
    new_product = Product(**product_in.dict())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


@router.put("/{identifier}", response_model=ProductResponse)
def update_product(
    identifier: str,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    """
    Update product details dynamically by numeric ID or Name (Admin only).
    """
    product = find_product(identifier, db)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{identifier}' not found."
        )

    update_data = product_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{identifier}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    identifier: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    """
    Delete a product by numeric ID or Name (Admin only).
    """
    product = find_product(identifier, db)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{identifier}' not found."
        )

    db.delete(product)
    db.commit()
    return None