import datetime
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.database import get_async_db
from app.rag.knowledge_base import knowledge_base
from app.connectors.kanvaro_mcp import KanvaroMCPConnector
from app.connectors.base import ExternalRef

router = APIRouter(prefix="/api/issues", tags=["Issues"])

class StatusUpdateRequest(BaseModel):
    status: str # 'Open' | 'In progress' | 'Resolved' | 'Won't fix'
    user_email: str
    resolution_notes: Optional[str] = None

class CommentRequest(BaseModel):
    user_email: str
    user_name: str
    text: str

@router.get("")
async def list_issues(
    status: Optional[str] = None,
    category: Optional[str] = None,
    assignee: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50
):
    db = get_async_db()
    query = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    if assignee:
        query["assignee"] = assignee
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"project": {"$regex": search, "$options": "i"}}
        ]

    cursor = db.issues.find(query).sort("last_seen", -1).limit(limit)
    items = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        items.append(doc)
    return {"issues": items, "count": len(items)}

@router.get("/{issue_id}")
async def get_issue(issue_id: str):
    db = get_async_db()
    try:
        obj_id = ObjectId(issue_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid issue ID format")

    doc = await db.issues.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Issue not found")
    doc["id"] = str(doc.pop("_id"))

    # Also fetch the most recent failure event facts if available
    latest_event = None
    if doc.get("latest_failure_id"):
        failure_doc = await db.failures.find_one({"event_key": doc["latest_failure_id"]})
        if failure_doc:
            latest_event = failure_doc.get("masked_event")

    doc["latest_event"] = latest_event
    return doc

@router.patch("/{issue_id}/status")
async def update_issue_status(issue_id: str, req: StatusUpdateRequest):
    db = get_async_db()
    try:
        obj_id = ObjectId(issue_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid issue ID format")

    issue = await db.issues.find_one({"_id": obj_id})
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    old_status = issue.get("status", "Open")
    is_open = req.status in ["Open", "In progress"]

    history_entry = {
        "from_status": old_status,
        "to_status": req.status,
        "changed_by": req.user_email,
        "timestamp": datetime.datetime.utcnow(),
        "comment": req.resolution_notes or f"Status changed to {req.status}"
    }

    update_fields = {
        "status": req.status,
        "is_open": is_open,
    }

    await db.issues.update_one(
        {"_id": obj_id},
        {
            "$set": update_fields,
            "$push": {"status_history": history_entry}
        }
    )

    # Learning: If issue is Resolved, add fix note to Qdrant knowledge base!
    if req.status == "Resolved" and req.resolution_notes:
        knowledge_base.add_resolved_fix(
            issue_id=issue_id,
            title=issue.get("title", ""),
            category=issue.get("category", ""),
            resolution_notes=req.resolution_notes
        )

    # Sync status to Kanvaro task tool if linked
    task_id = issue.get("external_task_ids", {}).get("kanvaro")
    if task_id:
        try:
            kanvaro = KanvaroMCPConnector()
            kanvaro.update_status(ExternalRef(task_id=task_id), req.status)
        except Exception:
            pass

    return {"status": "success", "new_status": req.status}

@router.post("/{issue_id}/comments")
async def add_comment(issue_id: str, req: CommentRequest):
    db = get_async_db()
    try:
        obj_id = ObjectId(issue_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid issue ID format")

    import uuid
    comment = {
        "id": uuid.uuid4().hex[:8],
        "user_email": req.user_email,
        "user_name": req.user_name,
        "text": req.text,
        "created_at": datetime.datetime.utcnow()
    }

    await db.issues.update_one(
        {"_id": obj_id},
        {"$push": {"comments": comment}}
    )
    return {"status": "success", "comment": comment}
