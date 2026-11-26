import os
import uuid
import datetime
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

app = FastAPI(title="Mock Kanvaro MCP Server", version="1.0.0")

BOT_USER = os.getenv("BOT_USER", "triage-bot")
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "mock_kanvaro_secure_pass")

# In-memory store for mock sessions and tasks
active_sessions: Dict[str, datetime.datetime] = {}
tasks_db: Dict[str, Dict[str, Any]] = {}

class LoginRequest(BaseModel):
    username: str
    password: str

class CreateTaskRequest(BaseModel):
    title: str
    description: str
    assignee: Optional[str] = None
    priority: str = "High"
    metadata: Dict[str, Any] = {}

class UpdateTaskStatusRequest(BaseModel):
    status: str
    comment: Optional[str] = None

@app.post("/auth/login")
def login(creds: LoginRequest):
    """Simulates Kanvaro bot user sign-in with ~7-day session renewal."""
    if creds.username == BOT_USER and creds.password == BOT_PASSWORD:
        session_token = f"kanvaro_sess_{uuid.uuid4().hex}"
        active_sessions[session_token] = datetime.datetime.utcnow() + datetime.timedelta(days=7)
        return {
            "token": session_token,
            "expires_in_days": 7,
            "message": "Authenticated as bot user"
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")

def verify_session(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization.split(" ")[1]
    expiry = active_sessions.get(token)
    if not expiry or datetime.datetime.utcnow() > expiry:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return token

@app.post("/tasks")
def create_task(req: CreateTaskRequest, token: str = Depends(verify_session)):
    task_id = f"KAN-{len(tasks_db) + 101}"
    task = {
        "id": task_id,
        "title": req.title,
        "description": req.description,
        "assignee": req.assignee,
        "priority": req.priority,
        "status": "TODO",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "metadata": req.metadata,
        "comments": []
    }
    tasks_db[task_id] = task
    return {"task_id": task_id, "url": f"http://localhost:8080/tasks/{task_id}", "task": task}

@app.get("/tasks/{task_id}")
def get_task(task_id: str, token: str = Depends(verify_session)):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]

@app.patch("/tasks/{task_id}/status")
def update_status(task_id: str, req: UpdateTaskStatusRequest, token: str = Depends(verify_session)):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks_db[task_id]
    task["status"] = req.status
    if req.comment:
        task["comments"].append({
            "text": req.comment,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "author": "Pipeline Triage Sync"
        })
    return {"task_id": task_id, "status": req.status}

@app.get("/health")
def health():
    return {"status": "ok", "service": "mock-kanvaro"}
