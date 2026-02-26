from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from datetime import datetime

import database
import auth
import dependencies
import models

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=models.UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: models.UserCreate):
    """Register a new user"""
    db = database.get_database()
    
    # Check if username already exists
    existing_user = await db.users.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = await db.users.find_one({"email": user_data.email})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user_dict = {
        "username": user_data.username,
        "email": user_data.email,
        "password_hash": auth.get_password_hash(user_data.password),
        "display_name": user_data.display_name or user_data.username,
        "avatar_icon": "👨‍🚀",
        "created_at": datetime.utcnow(),
        "last_login": None,
        "stats": {
            "streak_days": 0,
            "total_xp": 0,
            "total_hours": 0.0,
            "last_activity_date": None
        }
    }
    
    result = await db.users.insert_one(user_dict)
    user_dict["_id"] = result.inserted_id
    
    # Convert to response format
    user_response = models.UserResponse(
        id=str(result.inserted_id),
        username=user_dict["username"],
        email=user_dict["email"],
        display_name=user_dict["display_name"],
        avatar_icon=user_dict["avatar_icon"],
        stats=models.UserStats(**user_dict["stats"])
    )
    
    return user_response


@router.post("/login")
async def login(credentials: models.UserLogin):
    """Login user and return access token"""
    db = database.get_database()
    
    # Find user by username
    user_data = await db.users.find_one({"username": credentials.username})
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Verify password
    if not auth.verify_password(credentials.password, user_data["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Update last login
    await db.users.update_one(
        {"_id": user_data["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Create access token
    access_token = auth.create_access_token(data={"sub": str(user_data["_id"])})
    
    # Return token and user info
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user_data["_id"]),
            "username": user_data["username"],
            "email": user_data["email"],
            "display_name": user_data.get("display_name"),
            "avatar_icon": user_data.get("avatar_icon", "👨‍🚀"),
            "stats": user_data.get("stats", {
                "streak_days": 0,
                "total_xp": 0,
                "total_hours": 0.0,
                "last_activity_date": None
            })
        }
    }


@router.post("/logout")
async def logout():
    """Logout user (client should delete token)"""
    return {"message": "Successfully logged out"}
