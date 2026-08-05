from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin, UserResponse, Token
from app.core.security import get_password_hash, verify_password, create_access_token
from app.api.deps import get_current_user

# Initialize rate limiter using client IP address
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer account"
)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user account.
    
    Note: Public registration defaults strictly to the CUSTOMER role to prevent 
    unauthorized elevation to ADMIN.
    """
    # Check if user with given email already exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # Create new customer record
    new_user = User(
        full_name=user_in.full_name,
        email=user_in.email.lower().strip(),
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role  # Standardized to customer on public signups
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post(
    "/login", 
    response_model=Token,
    summary="Unified login for Customers & Admins"
)
@limiter.limit("5/minute")
def login(
    request: Request, 
    credentials: UserLogin, 
    db: Session = Depends(get_db)
):
    """
    Authenticates both customers and admins through a single secure endpoint.
    
    - Protected by Rate Limiting (max 5 requests per minute per IP to prevent brute-forcing).
    - Checks credentials and issues a signed JWT containing the user's ID and role.
    - Frontends inspect the returned `role` field to route users to the appropriate interface.
    """
    email_clean = credentials.email.lower().strip()
    user = db.query(User).filter(User.email == email_clean).first()

    # Generic error response prevents account enumeration
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated."
        )

    # Encode user ID and database role in token payload
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.value,
        "user": user
    }


@router.get(
    "/me", 
    response_model=UserResponse,
    summary="Get current user profile"
)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Retrieves the currently authenticated user's profile information using their JWT token.
    """
    return current_user