#app/models/enums.py
import enum

class ProductCategory(str, enum.Enum):
    OPTICAL_FRAMES = "optical_frames"
    SUNGLASSES = "sunglasses"
    CONTACT_LENSES = "contact_lenses"
    LENS_CARE = "lens_care"

class ReplacementFrequency(str, enum.Enum):
    DAILY = "daily"
    BI_WEEKLY = "bi_weekly"
    MONTHLY = "monthly"
    ORTHO_K = "ortho_k"

class LensDesign(str, enum.Enum):
    SPHERICAL = "spherical"
    TORIC = "toric"
    MULTIFOCAL = "multifocal"
    COLORED = "colored"

class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"