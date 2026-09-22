import difflib
from typing import List, Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, and_, case, distinct
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, require_admin
from app.models.enums import ProductCategory
from app.models.product import Product
from app.models.categories import Brand, Category
from app.schemas.product import (
    ProductCreate, 
    ProductResponse, 
    ProductUpdate,
    PaginatedCatalogWithFacetsResponse,
    CatalogFacets,
    SearchSuggestionsResponse,
    BrandSuggestionItem,
    ProductSuggestionItem
)

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
# LIVE SEARCH AUTOCOMPLETE OVERLAY
# ==========================================


@router.get("/search/suggest", response_model=SearchSuggestionsResponse)
def get_search_suggestions(
    q: str = Query(..., min_length=1, description="Raw user search query"),
    db: Session = Depends(get_db)
):
    """
    Powers the dynamic header search overlay menu:
    1. Matches categories starting with query prefix.
    2. Matches brands with prefix or word boundary ('G%' or '% G%').
    3. Matches top 6 product titles with prefix ranking.
    """
    clean_q = q.strip()
    if not clean_q:
        return SearchSuggestionsResponse(categories=[], brands=[], products=[])

    prefix_pattern = f"{clean_q}%"
    word_boundary_pattern = f"% {clean_q}%"

    # 1. MATCH CATEGORIES
    matching_categories = []
    category_enum_matches = [
        cat.value for cat in ProductCategory 
        if cat.value.lower().startswith(clean_q.lower()) or clean_q.lower() in cat.value.lower()
    ]
    matching_categories.extend(category_enum_matches)

    # 2. MATCH BRANDS (Prefix first, word-boundary second)
    brand_matches = (
        db.query(Brand)
        .filter(
            or_(
                Brand.name.ilike(prefix_pattern),
                Brand.name.ilike(word_boundary_pattern)
            )
        )
        .order_by(
            case((Brand.name.ilike(prefix_pattern), 1), else_=2),
            Brand.sales_count.desc()
        )
        .limit(6)
        .all()
    )

    brand_suggestions = [
        BrandSuggestionItem(
            name=b.name,
            slug=b.slug,
            logo_url=b.logo_url
        ) for b in brand_matches
    ]

    # 3. MATCH PRODUCTS
    product_matches = (
        db.query(
            Product.id,
            Product.name,
            Product.brand,
            Product.image_url,
            Product.price_full_gbp
        )
        .filter(
            Product.is_active == True,
            or_(
                Product.name.ilike(prefix_pattern),
                Product.name.ilike(word_boundary_pattern),
                Product.brand.ilike(prefix_pattern),
                Product.model_code.ilike(prefix_pattern)
            )
        )
        .order_by(
            case((Product.name.ilike(prefix_pattern), 1), else_=2),
            Product.id.desc()
        )
        .limit(6)
        .all()
    )

    product_suggestions = [
        ProductSuggestionItem(
            id=p.id,
            name=p.name,
            brand=p.brand,
            image_url=p.image_url,
            price_full_gbp=p.price_full_gbp
        ) for p in product_matches
    ]

    return SearchSuggestionsResponse(
        categories=matching_categories,
        brands=brand_suggestions,
        products=product_suggestions
    )


# ==========================================
# PUBLIC CATALOG ENDPOINTS (WITH FACETS)
# ==========================================


@router.get("/brands", response_model=List[str])
def list_available_brands(db: Session = Depends(get_db)):
    """
    Fetches all distinct brand names currently present in the database catalog.
    """
    results = db.query(Product.brand).filter(Product.brand.isnot(None), Product.brand != "").distinct().all()
    brands = sorted([r[0] for r in results if r[0]])
    return brands


@router.get("/catalog", response_model=PaginatedCatalogWithFacetsResponse)
@router.get("/", response_model=PaginatedCatalogWithFacetsResponse)
def list_products(
    q: Optional[str] = Query(None, description="Search term for name, brand, shape, or color"),
    category: Optional[str] = Query(None, description="Filter by category: optical_frames, sunglasses, contact_lenses, lens_care"),
    eyewear_only: bool = Query(False, description="If True, strictly returns Optical Frames & Sunglasses"),
    brand: Optional[str] = Query(None, description="Filter by brand name"),
    gender: Optional[str] = Query(None, description="Filter by gender (male, female, unisex)"),
    shape: Optional[str] = Query(None, description="Filter by frame shape"),
    color: Optional[str] = Query(None, description="Filter by color description"),
    frame_material: Optional[str] = Query(None, description="Filter by frame material"),
    min_lens_width: Optional[float] = Query(None, description="Minimum lens width in mm"),
    max_lens_width: Optional[float] = Query(None, description="Maximum lens width in mm"),
    tier: Optional[str] = Query(None, description="Filter tier: luxury, bridge, budget"),
    is_bestseller: Optional[bool] = Query(None, description="Filter bestseller items"),
    is_featured: Optional[bool] = Query(None, description="Filter featured items"),
    min_price: Optional[float] = Query(None, description="Minimum price filter in GBP"),
    max_price: Optional[float] = Query(None, description="Maximum price filter in GBP"),
    in_stock_only: bool = Query(False, description="Filter only products currently in stock"),
    sort_by: Optional[str] = Query("newest", description="Sort order: price_asc, price_desc, newest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    High-performance catalog endpoint with:
    - Server-side pagination (`page` & `page_size`)
    - Dynamic SQLite aggregate facet calculation (`min_price`, `max_price`, distinct values)
    - Prefix & word-boundary search ranking
    - Automatic "Did You Mean?" fuzzy fallback using Python difflib
    """
    def build_filtered_query(search_term: Optional[str]):
        base_query = db.query(Product).options(joinedload(Product.contact_lens_detail)).filter(Product.is_active == True)

        if eyewear_only:
            base_query = base_query.filter(
                Product.category.in_([ProductCategory.OPTICAL_FRAMES, ProductCategory.SUNGLASSES])
            )
        elif category and category.lower() != "all":
            clean_cat = category.lower().strip()
            matched_enum = None
            for e in ProductCategory:
                if e.value.lower() == clean_cat or e.name.lower() == clean_cat:
                    matched_enum = e
                    break
            if matched_enum:
                base_query = base_query.filter(Product.category == matched_enum)

        if search_term:
            clean_term = search_term.strip()
            prefix_pat = f"{clean_term}%"
            boundary_pat = f"% {clean_term}%"
            contains_pat = f"%{clean_term}%"

            base_query = base_query.filter(
                or_(
                    Product.name.ilike(prefix_pat),
                    Product.name.ilike(boundary_pat),
                    Product.brand.ilike(prefix_pat),
                    Product.brand.ilike(boundary_pat),
                    Product.model_code.ilike(prefix_pat),
                    Product.color_description.ilike(contains_pat),
                    Product.shape.ilike(contains_pat)
                )
            )

        if brand and brand.lower() != "all":
            base_query = base_query.filter(Product.brand.ilike(brand.strip()))
        if gender and gender.lower() != "all":
            base_query = base_query.filter(or_(Product.gender.ilike(gender.strip()), Product.gender.ilike("unisex")))
        if shape and shape.lower() != "all":
            base_query = base_query.filter(Product.shape.ilike(shape.strip()))
        if color:
            base_query = base_query.filter(Product.color_description.ilike(f"%{color.strip()}%"))
        if frame_material:
            base_query = base_query.filter(Product.frame_material.ilike(f"%{frame_material.strip()}%"))
        if min_lens_width is not None:
            base_query = base_query.filter(Product.lens_width >= min_lens_width)
        if max_lens_width is not None:
            base_query = base_query.filter(Product.lens_width <= max_lens_width)
        if is_bestseller is not None:
            base_query = base_query.filter(Product.is_bestseller == is_bestseller)
        if is_featured is not None:
            base_query = base_query.filter(Product.is_featured == is_featured)

        if tier:
            tier_lower = tier.lower().strip()
            if tier_lower == "luxury":
                base_query = base_query.filter(Product.price_full_gbp >= 200.0)
            elif tier_lower == "budget":
                base_query = base_query.filter(Product.price_full_gbp <= 100.0)
            elif tier_lower == "bridge":
                base_query = base_query.filter(Product.price_full_gbp > 100.0, Product.price_full_gbp < 200.0)

        if min_price is not None:
            base_query = base_query.filter(Product.price_full_gbp >= min_price)
        if max_price is not None:
            base_query = base_query.filter(Product.price_full_gbp <= max_price)
        if in_stock_only:
            base_query = base_query.filter(Product.stock_quantity > 0)

        return base_query

    # 1. EXECUTE PRIMARY FILTER QUERY
    active_search_term = q
    did_you_mean_suggestion = None
    query = build_filtered_query(active_search_term)
    total_count = query.count()

    # 2. TRIGGER "DID YOU MEAN?" FALLBACK IF 0 RESULTS RETURNED
    if total_count == 0 and q and q.strip():
        distinct_brands = [b[0] for b in db.query(Product.brand).filter(Product.brand.isnot(None)).distinct().all() if b[0]]
        distinct_categories = [c.value for c in ProductCategory]
        corpus = distinct_brands + distinct_categories

        matches = difflib.get_close_matches(q.strip(), corpus, n=1, cutoff=0.55)
        if matches:
            did_you_mean_suggestion = matches[0]
            # Re-run query using suggested brand/category correction
            query = build_filtered_query(did_you_mean_suggestion)
            total_count = query.count()

    # 3. APPLY SORTING
    if active_search_term and active_search_term.strip():
        prefix_pat = f"{active_search_term.strip()}%"
        query = query.order_by(
            case((Product.brand.ilike(prefix_pat), 1), else_=2),
            case((Product.name.ilike(prefix_pat), 1), else_=2),
            Product.id.desc()
        )
    elif sort_by == "price_asc":
        query = query.order_by(Product.price_full_gbp.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Product.price_full_gbp.desc())
    else:
        query = query.order_by(Product.id.desc())

    # 4. EXECUTE PAGINATED PRODUCT FETCH
    skip = (page - 1) * page_size
    products = query.offset(skip).limit(page_size).all()
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    # 5. SQL-LEVEL AGGREGATION FOR DYNAMIC FACETS & PRICE BOUNDS
    facet_subquery = build_filtered_query(active_search_term if not did_you_mean_suggestion else did_you_mean_suggestion).subquery()
    
    price_stats = db.query(
        func.min(facet_subquery.c.price_full_gbp),
        func.max(facet_subquery.c.price_full_gbp)
    ).first()

    calc_min_price = float(price_stats[0]) if price_stats and price_stats[0] is not None else 0.0
    calc_max_price = float(price_stats[1]) if price_stats and price_stats[1] is not None else 0.0

    facet_brands = [r[0] for r in db.query(distinct(facet_subquery.c.brand)).all() if r[0]]
    facet_shapes = [r[0] for r in db.query(distinct(facet_subquery.c.shape)).all() if r[0]]
    facet_materials = [r[0] for r in db.query(distinct(facet_subquery.c.frame_material)).all() if r[0]]
    facet_genders = [r[0] for r in db.query(distinct(facet_subquery.c.gender)).all() if r[0]]

    facets = CatalogFacets(
        min_price=calc_min_price,
        max_price=calc_max_price,
        available_brands=sorted(facet_brands),
        available_shapes=sorted(facet_shapes),
        available_materials=sorted(facet_materials),
        available_genders=sorted(facet_genders)
    )

    return PaginatedCatalogWithFacetsResponse(
        items=products,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        facets=facets,
        did_you_mean=did_you_mean_suggestion,
        original_query=q if did_you_mean_suggestion else None
    )


@router.get("/admin/catalog", response_model=PaginatedCatalogResponse)
def get_admin_product_catalog(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
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
    new_product = Product(**product_in.model_dump() if hasattr(product_in, 'model_dump') else product_in.dict())
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

    update_data = product_in.model_dump(exclude_unset=True) if hasattr(product_in, 'model_dump') else product_in.dict(exclude_unset=True)
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