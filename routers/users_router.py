from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from datetime import datetime, date
from typing import List

import database
import dependencies
import models

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/me", response_model=models.UserResponse)
async def get_current_user_info(current_user: models.UserInDB = Depends(dependencies.get_current_user)):
    """Get current user information"""
    return models.UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_icon=current_user.avatar_icon,
        stats=current_user.stats
    )


@router.get("/stats")
async def get_user_stats(current_user: models.UserInDB = Depends(dependencies.get_current_user)):
    """Get user statistics for home page"""
    db = database.get_database()
    
    # Get enrolled tracks count
    enrolled_tracks = await db.track_progress.count_documents({
        "user_id": current_user.id,
        "is_enrolled": True
    })
    
    return {
        "streak_days": current_user.stats.streak_days,
        "total_xp": current_user.stats.total_xp,
        "courses_started": enrolled_tracks,
        "total_hours": current_user.stats.total_hours
    }


@router.get("/daily-progress", response_model=models.DailyActivityResponse)
async def get_daily_progress(current_user: models.UserInDB = Depends(dependencies.get_current_user)):
    """Get today's progress for sidebar"""
    db = database.get_database()
    
    # Get today's date (without time)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Find today's activity
    activity = await db.daily_activities.find_one({
        "user_id": current_user.id,
        "activity_date": today
    })
    
    if not activity:
        return models.DailyActivityResponse(
            activity_date=today,
            tasks_completed=0,
            xp_earned=0,
            time_spent_minutes=0.0,
            percentage=0.0
        )
    
    # Calculate percentage (assuming 5 tasks per day as target)
    target_tasks = 5
    percentage = min((activity["tasks_completed"] / target_tasks) * 100, 100)
    
    return models.DailyActivityResponse(
        activity_date=activity["activity_date"],
        tasks_completed=activity["tasks_completed"],
        xp_earned=activity["xp_earned"],
        time_spent_minutes=activity["time_spent_minutes"],
        percentage=percentage
    )


@router.put("/profile")
async def update_profile(
    display_name: str = None,
    avatar_icon: str = None,
    current_user: models.UserInDB = Depends(dependencies.get_current_user)
):
    """Update user profile"""
    db = database.get_database()
    
    update_data = {}
    if display_name is not None:
        update_data["display_name"] = display_name
    if avatar_icon is not None:
        update_data["avatar_icon"] = avatar_icon
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update data provided"
        )
    
    await db.users.update_one(
        {"_id": current_user.id},
        {"$set": update_data}
    )
    
    return {"message": "Profile updated successfully"}
