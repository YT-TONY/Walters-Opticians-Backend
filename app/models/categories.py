# app/models/categories.py
from sqlalchemy import Column, DateTime, Integer, String, Boolean, ForeignKey, Table, func
from sqlalchemy.orm import relationship
from app.db.base import Base

# Junction table for Subcategory <-> Brand (Many-to-Many)
subcategory_brand = Table(
    'subcategory_brand',
    Base.metadata,
    Column('subcategory_id', Integer, ForeignKey('subcategories.id', ondelete="CASCADE"), primary_key=True),
    Column('brand_id', Integer, ForeignKey('brands.id', ondelete="CASCADE"), primary_key=True)
)

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    is_main_nav = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)

    # Relationships
    subcategories = relationship("SubCategory", back_populates="category", cascade="all, delete-orphan")


class SubCategory(Base):
    __tablename__ = "subcategories"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    slug = Column(String, index=True, nullable=False)
    display_order = Column(Integer, default=0)

    # Relationships
    category = relationship("Category", back_populates="subcategories")
    brands = relationship("Brand", secondary=subcategory_brand, back_populates="subcategories")


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    logo_url = Column(String, nullable=True)          # Logo (URL or uploaded static path)
    hero_image_url = Column(String, nullable=True)    # Hero/Banner image for recommended grid
    tagline = Column(String, nullable=True)           # Custom brand headline set by admin
    is_popular = Column(Boolean, default=False)
    is_top_brand = Column(Boolean, default=False)     # Admin manual toggle for Top Brands grid
    promo_tag = Column(String, nullable=True)         # e.g. "50% OFF", "LUXURY", "LIMITED"
    category_type = Column(String, default="both")    # "glasses", "sunglasses", or "both"
    sales_count = Column(Integer, default=0)          # Auto-sorting for Top Brands
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    subcategories = relationship("SubCategory", secondary=subcategory_brand, back_populates="brands")

class MegaMenuBanner(Base):
    __tablename__ = "megamenu_banners"

    id = Column(Integer, primary_key=True, index=True)
    tab_slug = Column(String, nullable=False, index=True) # "glasses", "sunglasses", "brands"
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=True)
    image_url = Column(String, nullable=False)
    target_url = Column(String, nullable=False)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)