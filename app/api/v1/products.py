from typing import List, Optional
from urllib.parse import unquote
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products & Catalog"])

# ==========================================
# FLEXIBLE LOOKUP HELPER
# ==========================================


def find_product(identifier: str, db: Session) -> Optional[Product]:
    """
    Finds a product by numeric ID if identifier contains digits, 
    otherwise falls back to a case-insensitive exact name match (URL-decoded).
    """
    clean_identifier = unquote(identifier).strip()

    if clean_identifier.isdigit():
        product = db.query(Product).filter(Product.id == int(clean_identifier)).first()
        if product:
            return product

    # Case-insensitive match for product name
    return db.query(Product).filter(Product.name.ilike(clean_identifier)).first()


# ==========================================
# PUBLIC CATALOG ENDPOINTS
# ==========================================


@router.get("/", response_model=List[ProductResponse])
def list_products(
    q: Optional[str] = Query(None, description="Search term for name, brand, shape, or color"),
    brand: Optional[str] = Query(None, description="Filter by brand name"),
    shape: Optional[str] = Query(None, description="Filter by frame shape (e.g., Round, Square, Aviator)"),
    color: Optional[str] = Query(None, description="Filter by color description"),
    min_price: Optional[float] = Query(None, description="Minimum price filter in GBP"),
    max_price: Optional[float] = Query(None, description="Maximum price filter in GBP"),
    in_stock_only: bool = Query(False, description="Filter only products currently in stock"),
    sort_by: Optional[str] = Query("newest", description="Sort order: price_asc, price_desc, newest"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Retrieve products catalog with multi-attribute filtering, search, and pagination.
    """
    query = db.query(Product)

    # Multi-attribute search across Name, Brand, Shape, and Color Description
    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            (Product.name.ilike(search_pattern)) |
            (Product.brand.ilike(search_pattern)) |
            (Product.shape.ilike(search_pattern)) |
            (Product.color_description.ilike(search_pattern))
        )

    # Specific attribute filters
    if brand:
        query = query.filter(Product.brand.ilike(brand.strip()))
    if shape:
        query = query.filter(Product.shape.ilike(shape.strip()))
    if color:
        query = query.filter(Product.color_description.ilike(color.strip()))
    if min_price is not None:
        query = query.filter(Product.price_full_gbp >= min_price)
    if max_price is not None:
        query = query.filter(Product.price_full_gbp <= max_price)
    if in_stock_only:
        query = query.filter(Product.stock_quantity > 0)

    # Sorting
    if sort_by == "price_asc":
        query = query.order_by(Product.price_full_gbp.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Product.price_full_gbp.desc())
    else:
        query = query.order_by(Product.id.desc())

    return query.offset(skip).limit(limit).all()


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