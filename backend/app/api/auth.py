import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from passlib.hash import argon2
from jose import jwt, JWTError

from app.config import settings
from app.database import get_async_db

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

SECRET_KEY = settings.APP_SECRET_KEY
ALGORITHM = "HS256"

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    email: str

def create_access_token(data: dict, expires_delta: datetime.timedelta = datetime.timedelta(days=7)):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    db = get_async_db()
    user = await db.users.find_one({"email": req.email.lower()})

    # Default dev bootstrap user if database is empty
    if not user and req.email.lower() == "admin@example.com" and req.password == "admin123":
        user = {
            "name": "System Administrator",
            "email": "admin@example.com",
            "role": "admin",
            "password_hash": argon2.hash("admin123"),
            "git_emails": ["admin@example.com"]
        }
        await db.users.insert_one(user)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not argon2.verify(req.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "sub": user["email"],
        "name": user["name"],
        "role": user["role"]
    })

    return TokenResponse(
        access_token=token,
        role=user["role"],
        name=user["name"],
        email=user["email"]
    )
