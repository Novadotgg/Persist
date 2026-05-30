import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.models.models import User
from app.core.security import get_password_hash, verify_password, create_access_token
from app.api.deps import get_current_user

logger = structlog.get_logger()
router = APIRouter()

# Schema definitions
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account with hashed password credentials.
    """
    logger.info("New registration request received", email=request.email)
    
    # Check if user already exists
    query = select(User).where(User.email == request.email)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        logger.warning("Registration failed: email already exists", email=request.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address is already registered."
        )
        
    hashed_password = get_password_hash(request.password)
    new_user = User(
        email=request.email,
        hashed_password=hashed_password,
        name=request.name,
        is_active=True
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    logger.info("Successfully registered new user", email=request.email, user_id=str(new_user.id))
    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate credentials and issue a JWT access token.
    """
    logger.info("Login attempt received", email=request.email)
    
    query = select(User).where(User.email == request.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.hashed_password):
        logger.warning("Authentication failed: invalid credentials", email=request.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": user.email})
    
    logger.info("Authentication successful, token issued", email=request.email)
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get profile details of the currently logged-in user.
    """
    return current_user
