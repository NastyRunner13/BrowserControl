import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from api.schemas import TaskResult, TaskStatus
from utils.logger import setup_logger

logger = setup_logger(__name__)

class JobManager:
    """
    Manages the state of asynchronous tasks with automatic cleanup.
    
    Features:
    - Automatic cleanup of old jobs (prevents memory leak)
    - Background cleanup task
    - Configurable TTL
    - Statistics tracking
    """
    
    def __init__(self, ttl_hours: int = 24, cleanup_interval_seconds: int = 3600):
        self._jobs: Dict[str, TaskResult] = {}
        self.ttl = timedelta(hours=ttl_hours)
        self.cleanup_interval = cleanup_interval_seconds
        self._cleanup_task: Optional[asyncio.Task] = None
        self.stats = {
            'total_created': 0,
            'total_cleaned': 0,
            'current_count': 0
        }
    
    async def start_cleanup_loop(self):
        """Start background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info(f"Job cleanup loop started (TTL: {self.ttl.total_seconds()/3600}h)")
    
    async def stop_cleanup_loop(self):
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Job cleanup loop stopped")
    
    async def _periodic_cleanup(self):
        """Periodically clean old jobs."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                cleaned = self._cleanup_old_jobs()
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} expired jobs")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def _cleanup_old_jobs(self) -> int:
        """Remove jobs older than TTL."""
        now = datetime.now()
        expired = [
            job_id for job_id, result in self._jobs.items()
            if result.created_at < now - self.ttl
        ]
        
        for job_id in expired:
            del self._jobs[job_id]
        
        self.stats['total_cleaned'] += len(expired)
        self.stats['current_count'] = len(self._jobs)
        
        return len(expired)
    
    def create_job(self) -> str:
        """Create new job with automatic cleanup check."""
        # Force cleanup if too many jobs (emergency brake)
        if len(self._jobs) > 1000:
            logger.warning(f"Job count exceeded 1000, forcing cleanup")
            self._cleanup_old_jobs()
        
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = TaskResult(
            task_id=job_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )
        
        self.stats['total_created'] += 1
        self.stats['current_count'] = len(self._jobs)
        
        logger.debug(f"Created job {job_id} (total: {len(self._jobs)})")
        
        return job_id

    def get_job(self, job_id: str) -> Optional[TaskResult]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    def update_status(
        self, 
        job_id: str, 
        status: TaskStatus, 
        result: Any = None, 
        error: Optional[str] = None
    ):
        """Update job status."""
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
    
    def get_stats(self) -> Dict:
        """Get manager statistics."""
        return {
            **self.stats,
            'ttl_hours': self.ttl.total_seconds() / 3600,
            'cleanup_interval_seconds': self.cleanup_interval
        }

# Global singleton
job_manager = JobManager()