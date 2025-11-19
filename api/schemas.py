from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class TaskRequest(BaseModel):
    prompt: str = Field(..., description="Natural language description of the automation task")
    headless: bool = Field(True, description="Run browser in headless mode")
    # Optional: Allow passing direct structured steps if bypassing the LLM planner
    structured_steps: Optional[List[Dict[str, Any]]] = None

class TaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: List[str] = []

class TaskSubmissionResponse(BaseModel):
    job_id: str
    status: TaskStatus
    message: str