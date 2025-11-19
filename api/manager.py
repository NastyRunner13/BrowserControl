import uuid
import asyncio
from datetime import datetime
from typing import Dict, Optional, Any
from api.schemas import TaskResult, TaskStatus
from utils.logger import setup_logger

logger = setup_logger(__name__)

class JobManager:
    """
    Manages the state of asynchronous tasks.
    In production, replace the self._jobs dict with Redis or a Database.
    """
    def __init__(self):
        self._jobs: Dict[str, TaskResult] = {}

    def create_job(self) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = TaskResult(
            task_id=job_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )
        return job_id

    def get_job(self, job_id: str) -> Optional[TaskResult]:
        return self._jobs.get(job_id)

    def update_status(self, job_id: str, status: TaskStatus, result: Any = None, error: Optional[str] = None):
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.status = status
            if result:
                job.result = result
            if error:
                job.error = error
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                job.completed_at = datetime.now()
            
            logger.info(f"Job {job_id} updated to {status}")

# Global singleton for memory-based storage
job_manager = JobManager()