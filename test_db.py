"""
Test script to verify MongoDB connection and create a test user
Run this after setting up your .env file
"""
import asyncio
from database import connect_to_mongo, close_mongo_connection, get_database
from auth import get_password_hash
from datetime import datetime


async def test_connection():
    """Test MongoDB connection and create a test user"""
    
    print("🔄 Testing MongoDB connection...")
    
    try:
        # Connect to MongoDB
        await connect_to_mongo()
        db = get_database()
        
        print("✅ Connected to MongoDB successfully!")
        
        # Check if test user exists
        test_user = await db.users.find_one({"username": "testuser"})
        
        if test_user:
            print("✅ Test user already exists")
            print(f"   Username: {test_user['username']}")
            print(f"   Email: {test_user['email']}")
        else:
            # Create test user
            print("🔄 Creating test user...")
            
            test_user_data = {
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
            
            result = await db.users.insert_one(test_user_data)
            print("✅ Test user created successfully!")
            print(f"   Username: testuser")
            print(f"   Password: test123")
            print(f"   Email: test@example.com")
            print(f"   User ID: {result.inserted_id}")
        
        # Test collections
        print("\n📊 Database Collections:")
        collections = await db.list_collection_names()
        for collection in collections:
            count = await db[collection].count_documents({})
            print(f"   - {collection}: {count} documents")
        
        print("\n✅ All tests passed!")
        print("\n🚀 You can now:")
        print("   1. Start the server: uvicorn main:app --reload")
        print("   2. Visit API docs: http://localhost:8000/docs")
        print("   3. Login with: testuser / test123")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure:")
        print("   1. You've created a .env file (copy from .env.example)")
        print("   2. Your MONGODB_URL is correct")
        print("   3. Your MongoDB Atlas IP whitelist includes your IP")
    
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(test_connection())
