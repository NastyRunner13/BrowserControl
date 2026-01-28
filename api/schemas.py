from pydantic import BaseModel, Field, field_validator
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
    
    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate and sanitize prompt input."""
        # Import settings here to avoid circular import
        from config.settings import settings
        
        if not v or not v.strip():
            raise ValueError("Prompt cannot be empty")
        
        # Check length
        max_length = settings.MAX_PROMPT_LENGTH
        if len(v) > max_length:
            raise ValueError(f"Prompt exceeds maximum length of {max_length} characters")
        
        # Basic sanitization if enabled
        if settings.ENABLE_PROMPT_SANITIZATION:
            # Remove null bytes
            v = v.replace('\x00', '')
            # Strip leading/trailing whitespace
            v = v.strip()
        
        return v

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