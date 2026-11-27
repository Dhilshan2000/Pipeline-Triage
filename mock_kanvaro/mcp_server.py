"""
Official Python MCP SDK Server Implementation for Mock Kanvaro.
Can be run via FastMCP over SSE or stdio transport.
"""
from mcp.server.fastmcp import FastMCP
from typing import Optional, Dict, Any

mcp = FastMCP("Kanvaro Task Tracker")

# In-memory storage for Kanvaro tasks
KANVARO_TASKS: Dict[str, Dict[str, Any]] = {}

@mcp.tool()
def create_task(title: str, description: str, assignee: str, priority: str = "High") -> Dict[str, Any]:
    """
    Creates a new task in Kanvaro assigned to a developer or DevOps engineer.
    Returns the created task ID and URL.
    """
    task_id = f"KAN-{len(KANVARO_TASKS) + 101}"
    task = {
        "task_id": task_id,
        "title": title,
        "description": description,
        "assignee": assignee,
        "priority": priority,
        "status": "TODO",
        "url": f"http://localhost:8080/tasks/{task_id}"
    }
    KANVARO_TASKS[task_id] = task
    return task

@mcp.tool()
def update_task_status(task_id: str, status: str, resolution_comment: Optional[str] = None) -> Dict[str, Any]:
    """
    Updates the status of an existing Kanvaro task (e.g. IN_PROGRESS, RESOLVED, WONT_FIX).
    """
    if task_id not in KANVARO_TASKS:
        return {"error": f"Task {task_id} not found"}
    task = KANVARO_TASKS[task_id]
    task["status"] = status
    if resolution_comment:
        task.setdefault("comments", []).append(resolution_comment)
    return {"task_id": task_id, "status": status, "updated": True}

@mcp.tool()
def get_task(task_id: str) -> Dict[str, Any]:
    """
    Retrieves full details of a Kanvaro task by ID.
    """
    return KANVARO_TASKS.get(task_id, {"error": "Task not found"})

if __name__ == "__main__":
    mcp.run()
