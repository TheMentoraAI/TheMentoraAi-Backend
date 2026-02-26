import asyncio
from database import connect_to_mongo, close_mongo_connection, get_database
from auth import get_password_hash
from datetime import datetime

async def create_test_user():
    try:
        # Connect to MongoDB
        await connect_to_mongo()
        db = get_database()
        
        # Check if user already exists
        existing = await db.users.find_one({"username": "testuser"})
        if existing:
            print("✅ Test user already exists!")
            print(f"   Username: testuser")
            print(f"   Email: {existing.get('email')}")
            return
        
        # Create test user
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": get_password_hash("test123"),
            "display_name": "Test User",
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
        
        result = await db.users.insert_one(user_data)
        print("✅ Test user created successfully!")
        print(f"   Username: testuser")
        print(f"   Password: test123")
        print(f"   Email: test@example.com")
        print(f"   User ID: {result.inserted_id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(create_test_user())
