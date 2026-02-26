# AI Boomi Mentora - Backend Setup

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Up MongoDB Atlas

Follow the detailed guide in [MONGODB_SETUP.md](./MONGODB_SETUP.md)

**Quick steps:**
1. Create free MongoDB Atlas account at https://cloud.mongodb.com
2. Create a cluster (M0 Free tier)
3. Create database user
4. Whitelist your IP address
5. Get connection string

### 3. Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your MongoDB connection string
```

Required variables:
- `MONGODB_URL` - Your MongoDB Atlas connection string
- `DATABASE_NAME` - Database name (default: aiboomi_mentora)
- `SECRET_KEY` - Random secret key for JWT tokens
- `FASTROUTER_API_KEY` - Your FastRouter API key

### 4. Test Database Connection

```bash
python test_db.py
```

You should see:
```
✅ Connected to MongoDB successfully!
✅ Test user created successfully!
```

### 5. Run the Server

```bash
uvicorn main:app --reload
```

Server will start at: http://localhost:8000

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔐 Authentication Flow

### 1. Register a New User

```bash
POST /api/auth/register
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword",
  "display_name": "John Doe"
}
```

### 2. Login

```bash
POST /api/auth/login
{
  "username": "johndoe",
  "password": "securepassword"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "...",
    "username": "johndoe",
    "email": "john@example.com",
    "display_name": "John Doe",
    "avatar_icon": "👨‍🚀",
    "stats": {
      "streak_days": 0,
      "total_xp": 0,
      "total_hours": 0.0
    }
  }
}
```

### 3. Use Protected Endpoints

Add the token to your requests:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 🛣️ API Endpoints

### Authentication (`/api/auth`)
- `POST /register` - Register new user
- `POST /login` - Login and get access token
- `POST /logout` - Logout (client-side token deletion)

### Users (`/api/users`)
- `GET /me` - Get current user info
- `GET /stats` - Get user statistics (for home page)
- `GET /daily-progress` - Get today's progress (for sidebar)
- `PUT /profile` - Update user profile

### Tracks (`/api/tracks`)
- `GET /enrolled` - Get all enrolled tracks
- `GET /{track_slug}/progress` - Get progress for specific track
- `POST /{track_slug}/enroll` - Enroll in a track
- `PUT /{track_slug}/progress` - Update track progress
- `GET /{track_slug}/tasks/completed` - Get completed tasks
- `POST /tasks/{task_id}/complete` - Mark task as complete

### Legacy Endpoints
- `GET /lessons/{track}` - Get lessons for a track
- `GET /tasks/{track}` - Get tasks for a track
- `POST /generate-task` - Generate AI task
- `POST /evaluate` - Evaluate task submission

## 📊 Database Schema

### Collections

#### `users`
- User accounts with embedded stats
- Indexed on: username, email

#### `track_progress`
- Track enrollment and progress per user
- Indexed on: (user_id, track_slug), user_id, track_slug

#### `task_completions`
- Individual task completion records
- Indexed on: (user_id, track_slug, task_id), user_id, track_slug

#### `daily_activities`
- Daily progress tracking
- Indexed on: (user_id, activity_date), user_id

## 🧪 Testing with Test User

A test user is created automatically when you run `test_db.py`:

```
Username: testuser
Password: password123
Email: test@example.com
```

Use this for testing the frontend integration!

## 🔧 Development

### Project Structure

```
backend/
├── main.py              # FastAPI app and legacy endpoints
├── database.py          # MongoDB connection
├── models.py            # Pydantic models
├── auth.py              # Authentication utilities
├── dependencies.py      # FastAPI dependencies
├── routers/
│   ├── auth_router.py   # Auth endpoints
│   ├── users_router.py  # User endpoints
│   └── tracks_router.py # Track/task endpoints
├── curriculum/          # Course content
├── test_db.py          # Database test script
├── requirements.txt    # Python dependencies
└── .env                # Environment variables (create this)
```

### Adding New Endpoints

1. Create a new router in `routers/`
2. Import and include it in `main.py`
3. Use `get_current_user` dependency for protected routes

Example:
```python
from fastapi import APIRouter, Depends
from dependencies import get_current_user
from models import UserInDB

router = APIRouter(prefix="/api/myroute", tags=["MyRoute"])

@router.get("/protected")
async def protected_route(current_user: UserInDB = Depends(get_current_user)):
    return {"message": f"Hello {current_user.username}"}
```

## 🐛 Troubleshooting

### "Could not connect to MongoDB"
- Check your `.env` file has correct `MONGODB_URL`
- Verify your IP is whitelisted in MongoDB Atlas
- Check your database user credentials

### "Could not validate credentials"
- Make sure you're sending the token in Authorization header
- Token format: `Bearer <token>`
- Check if token has expired (24 hour expiry)

### "Collection not found"
- Run `test_db.py` to create indexes
- Indexes are created automatically on first connection

## 📝 Next Steps

1. ✅ Database setup complete
2. 🔄 Next: Frontend authentication integration
3. 🔄 Then: Connect UI components to API
4. 🔄 Finally: Real-time progress updates

See the main implementation plan for the full roadmap!
