import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

# Connect to the same DB as the app
# Assuming MongoDB is local default port
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "ai_boomi_mentora" 

async def check():
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Get the most recent user (likely the one logged in)
        users = await db.users.find().sort("created_at", -1).to_list(1)
        
        if not users:
            print("No users found!")
            return

        user = users[0]
        uid = str(user["_id"])
        print(f"Checking User: {user.get('username')} (ID: {uid})")
        
        # Check Track Progress
        tracks = await db.track_progress.find({"user_id": uid}).to_list(100)
        print(f"Found {len(tracks)} enrolled tracks:")
        for t in tracks:
            print("-" * 30)
            print(f"Slug: {t.get('track_slug')}")
            print(f"Tasks Completed: {t.get('tasks_completed')}")
            print(f"Percent Complete: {t.get('percent_complete')}")
            print(f"Lessons Completed: {t.get('lessons_completed')}")
            print(f"Last Accessed: {t.get('last_accessed')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
