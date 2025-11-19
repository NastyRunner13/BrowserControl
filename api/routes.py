from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Depends
from api.schemas import TaskRequest, TaskSubmissionResponse, TaskResult, TaskStatus
from api.manager import job_manager
from core.planner import AutomationAgent
from core.browser_pool import BrowserPool
from tools.automation_tools import execute_intelligent_parallel_tasks
import json
import traceback

router = APIRouter()

async def process_automation_task(job_id: str, request: TaskRequest, pool: BrowserPool):
    """
    Background worker function.
    """
    job_manager.update_status(job_id, TaskStatus.PROCESSING)
    
    try:
        # 1. Plan the task (if prompt provided)
        tasks_json = None
        
        if request.structured_steps:
             tasks_json = json.dumps(request.structured_steps)
        else:
            # Initialize Agent (Planner)
            agent = AutomationAgent()
            # Generate the plan
            plan = await agent._plan_task(request.prompt)
            if not plan:
                raise ValueError("Failed to generate execution plan from prompt")
            tasks_json = json.dumps(plan)

        # 2. Execute the task using the tool logic
        # We invoke the executor manually here instead of via LangChain tool wrapper 
        # to have better control over the pool and results
        from tools.automation_tools import _execute_intelligent_tasks_parallel, _generate_execution_summary
        from models.task import IntelligentParallelTask
        from utils.validators import validate_tasks_json
        
        # Reuse validation logic
        tasks_data = validate_tasks_json(tasks_json)
        intelligent_tasks = [
            IntelligentParallelTask.from_dict(td) for td in tasks_data
        ]
        
        # Execute
        results_dict = await _execute_intelligent_tasks_parallel(intelligent_tasks, pool)
        
        # Generate summary
        summary_text = _generate_execution_summary(intelligent_tasks, results_dict)
        
        # 3. Update Job Store
        # We store both the raw structured results and the text summary
        final_output = {
            "summary": summary_text,
            "details": results_dict
        }
        
        # Check if overall success (if any task failed, mark job as failed or partial)
        has_failure = any(not r.get('success', False) for r in results_dict.values())
        final_status = TaskStatus.FAILED if has_failure else TaskStatus.COMPLETED
        
        job_manager.update_status(job_id, final_status, result=final_output)

    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        job_manager.update_status(job_id, TaskStatus.FAILED, error=error_msg)

@router.post("/tasks/submit", response_model=TaskSubmissionResponse)
async def submit_task(
    task_request: TaskRequest, 
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Submit a new browser automation task.
    """
    # Create Job ID
    job_id = job_manager.create_job()
    
    # Get BrowserPool from app state (initialized in server.py)
    pool: BrowserPool = request.app.state.browser_pool
    
    # Add to background processing
    background_tasks.add_task(
        process_automation_task, 
        job_id, 
        task_request,
        pool
    )
    
    return TaskSubmissionResponse(
        job_id=job_id,
        status=TaskStatus.PENDING,
        message="Task submitted successfully"
    )

@router.get("/tasks/{job_id}", response_model=TaskResult)
async def get_task_status(job_id: str):
    """
    Get the status and results of a specific job.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job