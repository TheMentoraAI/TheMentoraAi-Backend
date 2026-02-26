from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from bson import ObjectId
import auth
import database
import models

security = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(
    token: str = Depends(security)
) -> models.UserInDB:
    """
    Dependency to get the current authenticated user from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # token is already the string
    payload = auth.decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Get user from database
    db = database.get_database()
    user_data = await db.users.find_one({"_id": ObjectId(user_id)})
    
    if user_data is None:
        raise credentials_exception
    
    # Convert ObjectId to string for Pydantic model
    user_data["_id"] = str(user_data["_id"])
    
    return models.UserInDB(**user_data)


async def get_current_user_optional(
    token: str = Depends(security)
) -> models.UserInDB | None:
    """
    Optional authentication - returns None if not authenticated
    """
    try:
        return await get_current_user(token)
    except HTTPException:
        return None
