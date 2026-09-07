# app/models/order.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    reference_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Legacy single-product fallback columns (nullable for multi-item orders)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    quantity = Column(Integer, default=1, nullable=True)
    order_type = Column(String, nullable=True)

    # Delivery & Location
    shipping_address = Column(String, nullable=False)
    country = Column(String, nullable=False)

    # Financial Breakdown (All in GBP £)
    frame_price = Column(Float, default=0.0, nullable=False)
    lens_fee = Column(Float, default=0.0, nullable=False)
    exam_fee = Column(Float, default=0.0, nullable=False)
    shipping_fee = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)

    # Fulfillment Status
    status = Column(String, default="Order Placed")

    # Prescription Status
    prescription_status = Column(String, default="pending_review")

    # Shipping & Tracking Metadata
    carrier = Column(String, nullable=True)
    tracking_number = Column(String, nullable=True, index=True)
    shipping_label_url = Column(String, nullable=True)
    estimated_delivery = Column(DateTime, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Appointment Details (UK only)
    appointment_date = Column(DateTime, nullable=True)

    # Legacy flat prescription details (fallback)
    prescription_file_url = Column(String, nullable=True)
    right_sph = Column(Float, nullable=True)
    right_cyl = Column(Float, nullable=True)
    right_axis = Column(Integer, nullable=True)
    left_sph = Column(Float, nullable=True)
    left_cyl = Column(Float, nullable=True)
    left_axis = Column(Integer, nullable=True)
    pd_mm = Column(Float, nullable=True)

    # One-to-Many Relationship for Batch Items
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)

    # "frame_only", "upload_prescription", "manual_prescription", "book_appointment"
    order_type = Column(String, nullable=False)

    # Item Pricing
    frame_price = Column(Float, nullable=False, default=0.0)
    lens_fee = Column(Float, nullable=False, default=0.0)

    # Item-Level Prescription Parameters
    prescription_file_url = Column(String, nullable=True)
    right_sph = Column(Float, nullable=True)
    right_cyl = Column(Float, nullable=True)
    right_axis = Column(Integer, nullable=True)
    left_sph = Column(Float, nullable=True)
    left_cyl = Column(Float, nullable=True)
    left_axis = Column(Integer, nullable=True)
    pd_mm = Column(Float, nullable=True)

    order = relationship("Order", back_populates="items")