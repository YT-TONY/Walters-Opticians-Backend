from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
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
    is_popular = Column(Boolean, default=False)

    # Relationships
    subcategories = relationship("SubCategory", secondary=subcategory_brand, back_populates="brands")