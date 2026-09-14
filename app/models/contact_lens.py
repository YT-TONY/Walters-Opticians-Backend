#app/models/contact_lens.py

from sqlalchemy import Column, Integer, String, Float, Boolean, Date, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.enums import ReplacementFrequency, LensDesign, VerificationStatus

class ContactLensProductDetail(Base):
    __tablename__ = "contact_lens_product_details"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    replacement_frequency = Column(Enum(ReplacementFrequency), nullable=False)
    lens_design = Column(Enum(LensDesign), nullable=False)
    pack_size = Column(Integer, nullable=False)  # e.g., 30 or 90 pack
    water_content = Column(Float, nullable=True)  # e.g., 55.0 %
    material_type = Column(String(100), nullable=True)  # e.g., Silicone Hydrogel

    # Available parameter ranges stored as comma-separated values
    base_curve_options = Column(String(255), nullable=False)  # e.g., "8.4, 8.8"
    diameter_options = Column(String(255), nullable=False)   # e.g., "14.0, 14.2"
    min_power = Column(Float, nullable=False, default=-12.00)
    max_power = Column(Float, nullable=False, default=+6.00)

    product = relationship("Product", back_populates="contact_lens_detail")


class ContactLensPrescription(Base):
    __tablename__ = "contact_lens_prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    optician_name = Column(String(150), nullable=True)
    prescription_file_url = Column(String(500), nullable=False)
    expiry_date = Column(Date, nullable=False)
    status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING, nullable=False)

    # Left Eye (OS) Parameters
    left_sph = Column(Float, nullable=True)
    left_cyl = Column(Float, nullable=True)
    left_axis = Column(Integer, nullable=True)
    left_add = Column(String(20), nullable=True)
    left_bc = Column(Float, nullable=True)
    left_dia = Column(Float, nullable=True)
    left_boxes_qty = Column(Integer, default=0, nullable=False)

    # Right Eye (OD) Parameters
    right_sph = Column(Float, nullable=True)
    right_cyl = Column(Float, nullable=True)
    right_axis = Column(Integer, nullable=True)
    right_add = Column(String(20), nullable=True)
    right_bc = Column(Float, nullable=True)
    right_dia = Column(Float, nullable=True)
    right_boxes_qty = Column(Integer, default=0, nullable=False)