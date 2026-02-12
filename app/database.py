from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config import settings
from app.models.user import User, UserSession
from app.models.analysis import Analysis
from app.models.payment import Subscription

async def init_db():
    """Initialize MongoDB connection and Beanie ODM"""
    try:
        # Create MongoDB client
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        
        # Initialize Beanie with document models
        await init_beanie(
            database=client.powerlit,
            document_models=[
                User,
                UserSession, 
                Analysis,
                Subscription
            ]
        )
        
        print("✅ MongoDB connection established successfully")
        print("✅ Beanie ODM initialized with document models")
        
        # Create indexes for better performance
        await create_indexes()
        
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        raise

async def create_indexes():
    """Create database indexes for better performance"""
    try:
        # User collection indexes
        await User.find({}).limit(1).sort([("email", 1)])  # Ensure email index
        
        # Analysis collection indexes  
        await Analysis.find({}).limit(1).sort([("user_id", 1), ("created_at", -1)])
        
        # Subscription collection indexes
        await Subscription.find({}).limit(1).sort([("reference", 1), ("user_id", 1)])
        
        # Session collection indexes
        await UserSession.find({}).limit(1).sort([("user_id", 1), ("refresh_token", 1)])
        
        print("✅ Database indexes created successfully")
        
    except Exception as e:
        print(f"⚠️  Index creation warning: {str(e)}")

async def get_database():
    """Get database connection (if needed directly)"""
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        return client.powerlit
    except Exception as e:
        print(f"❌ Database connection error: {str(e)}")
        raise

async def test_connection():
    """Test database connection"""
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        
        # Test connection
        await client.admin.command('ping')
        
        print("✅ MongoDB connection test successful")
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection test failed: {str(e)}")
        return False

async def close_connection():
    """Close database connection"""
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        client.close()
        print("✅ Database connection closed")
    except Exception as e:
        print(f"⚠️  Error closing database connection: {str(e)}")