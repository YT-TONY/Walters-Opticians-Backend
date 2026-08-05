from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)

    # Selected options stored prior to checkout
    order_type = Column(String, default="frame_only", nullable=False)  # frame_only, upload_prescription, manual_prescription, book_appointment
    appointment_date = Column(DateTime, nullable=True)

    # Prescription fields
    prescription_file_url = Column(String, nullable=True)
    right_sph = Column(Float, nullable=True)
    right_cyl = Column(Float, nullable=True)
    right_axis = Column(Integer, nullable=True)
    left_sph = Column(Float, nullable=True)
    left_cyl = Column(Float, nullable=True)
    left_axis = Column(Integer, nullable=True)
    pd_mm = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to access product metadata (title, price, image) directly
    product = relationship("Product")