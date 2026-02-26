from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from datetime import datetime
from typing import List
import logging

import database
import dependencies
import models

# Setup debug logging
logging.basicConfig(
    filename='debug_tracks.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    force=True
)

def calculate_progress_percentage(track_slug: str, tasks_completed: int) -> float:
    try:
        import json, os
        curr_path = f"curriculum/{track_slug}.json"
        if os.path.exists(curr_path):
            with open(curr_path) as f:
                curr_data = json.load(f)
                total_lessons = len(curr_data.get("lessons", []))
                if total_lessons > 0:
                    # 3 tasks per lesson logic
                    return min(100.0, (tasks_completed / (total_lessons * 3)) * 100)
    except Exception as e:
        print(f"Error calculating progress: {e}")
    # Fallback
    return min(100.0, tasks_completed * 6.6)

router = APIRouter(prefix="/api/tracks", tags=["Tracks"])


@router.get("/enrolled", response_model=List[models.TrackProgressResponse])
async def get_enrolled_tracks(current_user: models.UserInDB = Depends(dependencies.get_current_user)):
    """Get all tracks the user is enrolled in"""
    db = database.get_database()
    
    cursor = db.track_progress.find({
        "user_id": current_user.id,
        "is_enrolled": True
    })
    
    tracks = []
    async for track in cursor:
        logging.info(f"TRACK: {track.get('track_slug')} - Tasks: {track.get('tasks_completed')} - Percent: {track.get('percent_complete')}")
        
        # Self-healing: Fix 0% progress for existing users
        if track.get("percent_complete", 0) == 0 and track.get("tasks_completed", 0) > 0:
            percent = calculate_progress_percentage(track["track_slug"], track["tasks_completed"])
            track["percent_complete"] = percent
            # Update DB asynchronously
            await db.track_progress.update_one(
                {"_id": track["_id"]},
                {"$set": {"percent_complete": percent}}
            )
            logging.info(f"HEALED: Updated {track['track_slug']} to {percent}%")

        tracks.append(models.TrackProgressResponse(
            id=str(track["_id"]),
            user_id=str(track["user_id"]), 
            track_slug=track["track_slug"],
            track_name=track["track_name"],
            current_lesson_index=track["current_lesson_index"],
            current_task_index=track["current_task_index"],
            percent_complete=track["percent_complete"],
            lessons_completed=track["lessons_completed"],
            tasks_completed=track["tasks_completed"],
            is_enrolled=track["is_enrolled"],
            started_at=track.get("started_at"),
            last_accessed=track.get("last_accessed")
        ))
    
    return tracks


@router.get("/{track_slug}/progress", response_model=models.TrackProgressResponse)
async def get_track_progress(
    track_slug: str,
    current_user: models.UserInDB = Depends(dependencies.get_current_user)
):
    """Get progress for a specific track"""
    db = database.get_database()
    
    track = await db.track_progress.find_one({
        "user_id": current_user.id,
        "track_slug": track_slug
    })
    
    if not track:
        # Return default progress if not enrolled
        return models.TrackProgressResponse(
            id="",
            user_id=str(current_user.id),
            track_slug=track_slug,
            track_name=track_slug.replace("-", " ").title(),
            current_lesson_index=0,
            current_task_index=0,
            percent_complete=0.0,
            lessons_completed=0,
            tasks_completed=0,
            is_enrolled=False,
            started_at=None,
            last_accessed=None
        )
    
    # Update last accessed
    await db.track_progress.update_one(
        {"_id": track["_id"]},
        {"$set": {"last_accessed": datetime.utcnow()}}
    )
    
    return models.TrackProgressResponse(
        id=str(track["_id"]),
        user_id=str(track["user_id"]), 
        track_slug=track["track_slug"],
        track_name=track["track_name"],
        current_lesson_index=track["current_lesson_index"],
        current_task_index=track["current_task_index"],
        percent_complete=track["percent_complete"],
        lessons_completed=track["lessons_completed"],
        tasks_completed=track["tasks_completed"],
        is_enrolled=track["is_enrolled"],
        started_at=track.get("started_at"),
        last_accessed=track.get("last_accessed")
    )


@router.post("/{track_slug}/enroll", response_model=models.TrackProgressResponse)
async def enroll_in_track(
    track_slug: str,
    track_data: models.TrackProgressCreate, 
    current_user: models.UserInDB = Depends(dependencies.get_current_user)
):
    print(f"DEBUG IN ROUTER: models is {models}")
    print(f"DEBUG DIR: {dir(models)}")
    """Enroll user in a track"""
    db = database.get_database()
    
    # Check if already enrolled
    existing = await db.track_progress.find_one({
        "user_id": current_user.id,
        "track_slug": track_slug
    })
    
    if existing:
        # If already enrolled, just update preferences if provided
        if track_data.preferences:
            await db.track_progress.update_one(
                {"user_id": current_user.id, "track_slug": track_slug},
                {"$set": {"preferences": track_data.preferences}}
            )
            existing["preferences"] = track_data.preferences
            return existing

        # Check if we should allow "re-enrollment" reset? No, better to return existing.
        # Previously we raised error, but for idempotency returning success is better.
        return existing
    
    # Create track progress
    track_dict = {
        "user_id": current_user.id,
        "track_slug": track_slug,
        "track_name": track_data.track_name,
        "current_lesson_index": 0,
        "current_task_index": 0,
        "percent_complete": 0.0,
        "lessons_completed": 0,
        "tasks_completed": 0,
        "is_enrolled": True,
        "started_at": datetime.utcnow(),
        "last_accessed": datetime.utcnow()
    }
    
    result = await db.track_progress.insert_one(track_dict)
    
    # Update user stats - increment courses started
    await db.users.update_one(
        {"_id": current_user.id},
        {"$inc": {"stats.courses_started": 1}}
    )
    
    return models.TrackProgressResponse(
        id=str(result.inserted_id),
        user_id=str(current_user.id), 
        track_slug=track_slug,
        track_name=track_data.track_name,
        current_lesson_index=0,
        current_task_index=0,
        percent_complete=0.0,
        lessons_completed=0,
        tasks_completed=0,
        is_enrolled=True,
        started_at=track_dict["started_at"],
        last_accessed=track_dict["last_accessed"]
    )


@router.put("/{track_slug}/progress")
async def update_track_progress(
    track_slug: str,
    progress_update: models.TrackProgressUpdate,
    current_user: models.UserInDB = Depends(dependencies.get_current_user)
):
    """Update track progress"""
    db = database.get_database()
    
    # Build update dict
    update_data = {}
    if progress_update.current_lesson_index is not None:
        update_data["current_lesson_index"] = progress_update.current_lesson_index
    if progress_update.current_task_index is not None:
        update_data["current_task_index"] = progress_update.current_task_index
    if progress_update.percent_complete is not None:
        update_data["percent_complete"] = progress_update.percent_complete
    if progress_update.lessons_completed is not None:
        update_data["lessons_completed"] = progress_update.lessons_completed
    if progress_update.tasks_completed is not None:
        update_data["tasks_completed"] = progress_update.tasks_completed
    
    update_data["last_accessed"] = datetime.utcnow()
    
    result = await db.track_progress.update_one(
        {
            "user_id": current_user.id,
            "track_slug": track_slug
        },
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track progress not found"
        )
    
    return {"message": "Progress updated successfully"}


@router.get("/{track_slug}/tasks/completed", response_model=List[models.TaskCompletionResponse])
async def get_completed_tasks(
    track_slug: str,
    current_user: models.UserInDB = Depends(dependencies.get_current_user)
):
    """Get all completed tasks for a track"""
    db = database.get_database()
    
    cursor = db.task_completions.find({
        "user_id": current_user.id,
        "track_slug": track_slug
    }).sort("completed_at", 1)
    
    tasks = []
    async for task in cursor:
        tasks.append(models.TaskCompletionResponse(
            id=str(task["_id"]),
            task_id=task["task_id"],
            user_id=task.get("user_id", str(current_user.id)),
            track_slug=task["track_slug"],
            lesson_index=task["lesson_index"],
            task_index=task.get("task_index", 1), # Default to 1 if missing
            prompt=task.get("prompt", ""),
            user_output=task.get("user_output", ""),
            ai_evaluation=task.get("ai_evaluation", ""),
            completed_at=task["completed_at"],
            score=task.get("score"),
            xp_earned=task["xp_earned"]
        ))
    
    return tasks


from typing import Dict, Any

@router.post("/tasks/{task_id}/complete", response_model=models.TaskCompletionResponse)
async def complete_task(
    task_id: str,
    completion_data: Dict[str, Any], # Bypassing Pydantic validation
    current_user: models.UserInDB = Depends(dependencies.get_current_user)
):
    """Mark a task as completed"""
    try:
        db = database.get_database()
    
        # Check if already completed
        existing = await db.task_completions.find_one({
            "user_id": current_user.id,
            "track_slug": completion_data.get("track_slug"),
            "task_id": task_id
        })
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task already completed"
            )
        
        # Create task completion
        task_dict = {
            "user_id": current_user.id,
            "track_slug": completion_data.get("track_slug"),
            "task_id": task_id,
            "lesson_index": completion_data.get("lesson_index"),
            "task_index": completion_data.get("task_index"), # Succesfully added
            "prompt": completion_data.get("prompt", ""),
            "user_output": completion_data.get("user_output", ""),
            "ai_evaluation": completion_data.get("ai_evaluation", ""),
            "completed_at": datetime.utcnow(),
            "score": completion_data.get("score"),
            "xp_earned": completion_data.get("xp_earned", 10),
            "time_spent_minutes": completion_data.get("time_spent_minutes", 0)
        }
        
        result = await db.task_completions.insert_one(task_dict)
        
        # Update user stats
        await db.users.update_one(
            {"_id": current_user.id},
            {
                "$inc": {
                    "stats.total_xp": completion_data.get("xp_earned", 10),
                    "stats.total_hours": (completion_data.get("time_spent_minutes", 0) or 0) / 60
                },
                "$set": {
                    "stats.last_activity_date": datetime.utcnow()
                }
            }
        )
        
        # Update track progress
        track = await db.track_progress.find_one({
            "user_id": current_user.id,
            "track_slug": completion_data.get("track_slug")
        })
        
        if track:
            # Determine updates based on task progress
            new_tasks_completed = track["tasks_completed"] + 1
            
            current_task_idx = completion_data.get("task_index", 1)
            current_lesson_idx = completion_data.get("lesson_index", 0)
            
            update_fields = {
                "$inc": {"tasks_completed": 1},
                "$set": {
                    "last_accessed": datetime.utcnow(),
                    "current_task_index": current_task_idx
                }
            }
            
            # Check if lesson is completed (3 tasks per lesson logic)
            if current_task_idx >= 3:
                 update_fields["$inc"]["lessons_completed"] = 1
                 update_fields["$set"]["current_lesson_index"] = current_lesson_idx + 1
                 update_fields["$set"]["current_task_index"] = 0 # Reset for next lesson
            
            # Calculate progress using shared helper
            percent = calculate_progress_percentage(completion_data.get('track_slug'), new_tasks_completed)
            update_fields["$set"]["percent_complete"] = percent
            
            logging.info(f"COMPLETED TASK: percent={percent}")
            
            await db.track_progress.update_one(
                {"_id": track["_id"]},
                update_fields
            )
        
        # Update daily activity
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        await db.daily_activities.update_one(
            {
                "user_id": current_user.id,
                "activity_date": today
            },
            {
                "$inc": {
                    "tasks_completed": 1,
                    "xp_earned": completion_data.get("xp_earned", 10),
                    "time_spent_minutes": completion_data.get("time_spent_minutes", 0) or 0
                }
            },
            upsert=True
        )
        
        return models.TaskCompletionResponse(
            id=str(result.inserted_id),
            task_id=task_id,
            user_id=current_user.id,
            track_slug=completion_data.get("track_slug"),
            lesson_index=completion_data.get("lesson_index"),
            task_index=completion_data.get("task_index"),
            prompt=completion_data.get("prompt", ""),
            user_output=completion_data.get("user_output", ""),
            ai_evaluation=completion_data.get("ai_evaluation", ""),
            completed_at=task_dict["completed_at"],
            score=completion_data.get("score"),
            xp_earned=completion_data.get("xp_earned", 10)
        )
    except Exception as e:
        print(f"CRITICAL ERROR IN COMPLETE_TASK: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )
