from fastapi import FastAPI, APIRouter, HTTPException, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import statistics
import hashlib

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Helper function to hash passwords
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# User Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    password_hash: str
    created_date: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    created_date: datetime

# Updated Goal Models (now with user_id)
class Goal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    target_amount: float
    current_amount: float = 0.0
    created_date: datetime = Field(default_factory=datetime.utcnow)
    completed: bool = False
    completion_date: Optional[datetime] = None

class GoalCreate(BaseModel):
    name: str
    target_amount: float

class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal_id: str
    user_id: str
    amount: float
    transaction_date: datetime = Field(default_factory=datetime.utcnow)
    description: Optional[str] = None

class TransactionCreate(BaseModel):
    goal_id: str
    amount: float
    description: Optional[str] = None

class GoalProgress(BaseModel):
    goal: Goal
    progress_percentage: float
    remaining_amount: float
    estimated_days_to_completion: Optional[float]
    estimated_completion_date: Optional[datetime]
    average_daily_savings: Optional[float]

# Auth helper functions
async def get_user_by_username(username: str):
    return await db.users.find_one({"username": username})

async def get_user_by_id(user_id: str):
    return await db.users.find_one({"id": user_id})

# User Authentication Endpoints
@api_router.post("/register", response_model=UserResponse)
async def register(user_input: UserCreate):
    # Check if username already exists
    existing_user = await get_user_by_username(user_input.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Create new user with hashed password
    user_dict = user_input.dict()
    user_dict["password_hash"] = hash_password(user_input.password)
    user_dict.pop("password")  # Remove plain password
    
    user_obj = User(**user_dict)
    await db.users.insert_one(user_obj.dict())
    
    return UserResponse(
        id=user_obj.id,
        username=user_obj.username,
        created_date=user_obj.created_date
    )

@api_router.post("/login", response_model=UserResponse)
async def login(user_input: UserLogin):
    # Find user by username
    user = await get_user_by_username(user_input.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Check password
    if user["password_hash"] != hash_password(user_input.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    return UserResponse(
        id=user["id"],
        username=user["username"],
        created_date=user["created_date"]
    )

# Helper function to calculate goal estimates
async def calculate_goal_estimates(goal: Goal) -> dict:
    # Get all transactions for this goal
    transactions = await db.transactions.find({"goal_id": goal.id, "user_id": goal.user_id}).to_list(1000)
    
    if not transactions:
        return {
            "estimated_days_to_completion": None,
            "estimated_completion_date": None,
            "average_daily_savings": None
        }
    
    # Sort transactions by date
    transactions.sort(key=lambda x: x["transaction_date"])
    
    # Calculate time-based savings rate
    first_transaction_date = transactions[0]["transaction_date"]
    last_transaction_date = transactions[-1]["transaction_date"]
    
    # If all transactions are on the same day, use a different approach
    if first_transaction_date.date() == last_transaction_date.date():
        # Use the total amount from today as daily rate
        total_today = sum(t["amount"] for t in transactions)
        average_daily_savings = total_today
    else:
        # Calculate days between first and last transaction
        days_span = (last_transaction_date - first_transaction_date).days
        if days_span == 0:
            days_span = 1  # Avoid division by zero
        
        # Calculate average daily savings
        total_amount = sum(t["amount"] for t in transactions)
        average_daily_savings = total_amount / days_span
    
    # Calculate remaining amount and estimate days to completion
    remaining_amount = goal.target_amount - goal.current_amount
    
    if remaining_amount <= 0:
        return {
            "estimated_days_to_completion": 0,
            "estimated_completion_date": datetime.utcnow(),
            "average_daily_savings": average_daily_savings
        }
    
    if average_daily_savings <= 0:
        return {
            "estimated_days_to_completion": None,
            "estimated_completion_date": None,
            "average_daily_savings": average_daily_savings
        }
    
    estimated_days = remaining_amount / average_daily_savings
    estimated_completion_date = datetime.utcnow() + timedelta(days=estimated_days)
    
    return {
        "estimated_days_to_completion": estimated_days,
        "estimated_completion_date": estimated_completion_date,
        "average_daily_savings": average_daily_savings
    }

# Goal endpoints (now user-specific)
@api_router.post("/goals", response_model=Goal)
async def create_goal(goal_input: GoalCreate, user_id: str):
    # Verify user exists
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    goal_dict = goal_input.dict()
    goal_dict["user_id"] = user_id
    goal_obj = Goal(**goal_dict)
    await db.goals.insert_one(goal_obj.dict())
    return goal_obj

@api_router.get("/goals", response_model=List[Goal])
async def get_goals(user_id: str):
    # Verify user exists
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    goals = await db.goals.find({"user_id": user_id}).to_list(1000)
    return [Goal(**goal) for goal in goals]

@api_router.get("/goals/{goal_id}", response_model=Goal)
async def get_goal(goal_id: str, user_id: str):
    goal = await db.goals.find_one({"id": goal_id, "user_id": user_id})
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return Goal(**goal)

@api_router.get("/goals/{goal_id}/progress", response_model=GoalProgress)
async def get_goal_progress(goal_id: str, user_id: str):
    goal = await db.goals.find_one({"id": goal_id, "user_id": user_id})
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    goal_obj = Goal(**goal)
    progress_percentage = (goal_obj.current_amount / goal_obj.target_amount) * 100 if goal_obj.target_amount > 0 else 0
    remaining_amount = goal_obj.target_amount - goal_obj.current_amount
    
    estimates = await calculate_goal_estimates(goal_obj)
    
    return GoalProgress(
        goal=goal_obj,
        progress_percentage=progress_percentage,
        remaining_amount=remaining_amount,
        estimated_days_to_completion=estimates["estimated_days_to_completion"],
        estimated_completion_date=estimates["estimated_completion_date"],
        average_daily_savings=estimates["average_daily_savings"]
    )

@api_router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str, user_id: str):
    # Delete the goal (only if it belongs to the user)
    result = await db.goals.delete_one({"id": goal_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Delete all transactions for this goal
    await db.transactions.delete_many({"goal_id": goal_id, "user_id": user_id})
    
    return {"message": "Goal deleted successfully"}

# Transaction endpoints (now user-specific)
@api_router.post("/transactions", response_model=Transaction)
async def add_transaction(transaction_input: TransactionCreate, user_id: str):
    # Check if goal exists and belongs to user
    goal = await db.goals.find_one({"id": transaction_input.goal_id, "user_id": user_id})
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Create transaction
    transaction_dict = transaction_input.dict()
    transaction_dict["user_id"] = user_id
    transaction_obj = Transaction(**transaction_dict)
    await db.transactions.insert_one(transaction_obj.dict())
    
    # Update goal's current amount
    new_amount = goal["current_amount"] + transaction_input.amount
    completed = new_amount >= goal["target_amount"]
    
    update_data = {
        "current_amount": new_amount,
        "completed": completed
    }
    
    if completed and not goal["completed"]:
        update_data["completion_date"] = datetime.utcnow()
    
    await db.goals.update_one(
        {"id": transaction_input.goal_id, "user_id": user_id},
        {"$set": update_data}
    )
    
    return transaction_obj

@api_router.get("/transactions/{goal_id}", response_model=List[Transaction])
async def get_transactions(goal_id: str, user_id: str):
    transactions = await db.transactions.find({"goal_id": goal_id, "user_id": user_id}).to_list(1000)
    return [Transaction(**transaction) for transaction in transactions]

@api_router.get("/")
async def root():
    return {"message": "Financial Goal Tracker API with User Authentication"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()