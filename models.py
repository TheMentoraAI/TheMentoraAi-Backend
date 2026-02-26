from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime

# ==================== USER MODELS ====================

class UserStats(BaseModel):
    """Embedded user statistics"""
    streak_days: int = 0
    total_xp: int = 0
    total_hours: float = 0.0
    last_activity_date: Optional[datetime] = None

class UserInDB(BaseModel):
    """User document in MongoDB"""
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
    
    id: Optional[str] = Field(default=None, alias="_id")
    username: str
    email: EmailStr
    password_hash: str
    display_name: Optional[str] = None
    avatar_icon: str = "👨‍🚀"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    stats: UserStats = Field(default_factory=UserStats)

class UserCreate(BaseModel):
    """Schema for user registration"""
    username: str
    email: EmailStr
    password: str
    display_name: Optional[str] = None

class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str

class UserResponse(BaseModel):
    """User response (without password)"""
    model_config = ConfigDict(populate_by_name=True)
    
    id: str
    username: str
    email: str
    display_name: Optional[str] = None
    avatar_icon: str
    stats: UserStats

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


# ==================== TRACK PROGRESS MODELS ====================

class TrackProgress(BaseModel):
    """Track progress document"""
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
    
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    track_slug: str
    track_name: str
    current_lesson_index: int = 0
    current_task_index: int = 0
    percent_complete: float = 0.0
    lessons_completed: int = 0
    tasks_completed: int = 0
    is_enrolled: bool = False
    started_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    preferences: Optional[Dict[str, Any]] = None  # User preferences

class TrackProgressCreate(BaseModel):
    """Schema for enrolling in a track"""
    track_slug: str
    track_name: str
    preferences: Optional[Dict[str, Any]] = None

class TrackProgressUpdate(BaseModel):
    """Schema for updating track progress"""
    current_lesson_index: Optional[int] = None
    current_task_index: Optional[int] = None
    percent_complete: Optional[float] = None
    lessons_completed: Optional[int] = None
    tasks_completed: Optional[int] = None
    preferences: Optional[Dict[str, Any]] = None
    last_accessed: Optional[datetime] = None

class TrackProgressResponse(TrackProgress):
    pass


# ==================== TASK MODELS ====================

class TaskCompletion(BaseModel):
    """Record of a completed task"""
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
    
    id: Optional[str] = Field(default=None, alias="_id")
    task_id: Optional[str] = None # Added
    user_id: str
    track_slug: str
    lesson_index: int
    task_index: int
    prompt: str
    user_output: str
    ai_evaluation: str
    score: int
    xp_earned: int = 10 # Added
    feedback_summary: Optional[str] = None 
    completed_at: datetime = Field(default_factory=datetime.utcnow)

class TaskCompletionCreate(BaseModel):
    track_slug: str
    lesson_index: int
    task_index: int
    prompt: Optional[str] = ""
    user_output: Optional[str] = ""
    ai_evaluation: Optional[str] = ""
    score: int
    xp_earned: int = 10
    time_spent_minutes: int = 0
    feedback_summary: Optional[str] = None

class TaskCompletionResponse(TaskCompletion):
    pass


# ==================== ACTIVITY MODELS ====================

class DailyActivity(BaseModel):
    """Record of daily activity for heatmap"""
    date: str  # YYYY-MM-DD
    count: int = 1

class DailyActivityResponse(BaseModel):
    activity_date: datetime
    tasks_completed: int
    xp_earned: int
    time_spent_minutes: float
    percentage: float
