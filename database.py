from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection settings
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "aiboomi_mentora")

# Global MongoDB client and database
client = None
database = None


async def connect_to_mongo():
    """Connect to MongoDB Atlas"""
    global client, database
    
    try:
        client = AsyncIOMotorClient(
            MONGODB_URL,
            server_api=ServerApi('1')
        )
        
        # Test the connection
        await client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas!")
        
        database = client[DATABASE_NAME]
        
        # Create indexes
        await create_indexes()
        
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()
        print("✅ MongoDB connection closed")


async def create_indexes():
    """Create database indexes for optimal performance"""
    global database
    
    try:
        # Users collection indexes
        await database.users.create_index("username", unique=True)
        await database.users.create_index("email", unique=True)
        
        # Track progress indexes
        await database.track_progress.create_index([("user_id", 1), ("track_slug", 1)], unique=True)
        await database.track_progress.create_index("user_id")
        await database.track_progress.create_index("track_slug")
        
        # Task completions indexes
        await database.task_completions.create_index([("user_id", 1), ("track_slug", 1), ("task_id", 1)], unique=True)
        await database.task_completions.create_index("user_id")
        await database.task_completions.create_index("track_slug")
        
        # Daily activities indexes
        await database.daily_activities.create_index([("user_id", 1), ("activity_date", 1)], unique=True)
        await database.daily_activities.create_index("user_id")
        
        print("✅ Database indexes created successfully")
        
    except Exception as e:
        print(f"⚠️ Error creating indexes: {e}")


def get_database():
    """Get database instance"""
    return database
