import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
import structlog
from cryptography.fernet import Fernet
from jose import jwt, JWTError
from app.core.config import settings

logger = structlog.get_logger()

# Attempt to initialize Fernet with settings encryption key.
# If invalid or using the default placeholder, initialize a session fallback key.
try:
    # Key must be 32-bytes url-safe base64 encoded.
    key_bytes = settings.CREDENTIALS_ENCRYPTION_KEY.encode()
    fernet = Fernet(key_bytes)
except Exception as e:
    logger.error(
        "Invalid CREDENTIALS_ENCRYPTION_KEY. Initializing runtime session fallback key. "
        "Credentials stored in DB will not persist across restarts until a stable key is configured.",
        error=str(e)
    )
    # Generate a temporary key for the active process runtime
    session_key = Fernet.generate_key()
    fernet = Fernet(session_key)

def encrypt_token(token: str) -> str:
    """
    Encrypt a credential token using Fernet symmetric encryption.
    """
    if not token:
        return ""
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(token_hash: str) -> str:
    """
    Decrypt an encrypted credential token back to plaintext.
    """
    if not token_hash:
        return ""
    return fernet.decrypt(token_hash.encode()).decode()

def get_password_hash(password: str) -> str:
    """
    Hash password securely using PBKDF2-HMAC-SHA256 with a salt.
    """
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plain password against hashed password.
    """
    if not hashed_password:
        return False
    try:
        salt_hex, key_hex = hashed_password.split("$")
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100000)
        return key.hex() == key_hex
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT access token.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

