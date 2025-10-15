import json
import asyncio
from typing import List, Dict, Any
from langchain_core.tools import tool
from models.task import IntelligentParallelTask
from core.browser_pool import BrowserPool
from core.executor import IntelligentParallelExecutor
from utils.logger import setup_logger
from utils.validators import validate_tasks_json, TaskValidator
from utils.exceptions import (
    BrowserAutomationError,
    TaskExecutionError,
    TaskTimeoutError,
    ValidationError
)
from utils.retry import RetryConfig, retry_async
from config.settings import settings

logger = setup_logger(__name__)

async def _execute_single_task(
    task: IntelligentParallelTask,
    pool: BrowserPool,
    executor: IntelligentParallelExecutor
) -> Dict[str, Any]:
    """
    Execute a single task with error handling and retry logic.
    
    Args:
        task: Task to execute
        pool: Browser pool
        executor: Task executor
        
    Returns:
        Execution result dictionary
    """
    browser_instance = None
    step_results = []
    intelligent_actions_count = 0
    current_step_index = 0
    
    try:
        # Get browser instance with timeout
        browser_instance = await pool.get_browser_instance(
            task.task_id,
            timeout=30.0
        )
        page = browser_instance.page
        
        logger.info(f"Starting task {task.task_id}: {task.name}")
        
        # Execute each step with retry
        for step_index, step in enumerate(task.steps):
            current_step_index = step_index
            
            try:
                # Execute step with retry logic
                result = await retry_async(
                    executor.execute_intelligent_step,
                    page,
                    step,
                    task.context,
                    config=RetryConfig(
                        max_attempts=task.retry_count,
                        initial_delay=1.0,
                        exceptions=(Exception,)
                    )
                )
                
                if step['action'].startswith('intelligent_'):
                    intelligent_actions_count += 1
                
                step_results.append({
                    'step_index': step_index,
                    'action': step['action'],
                    'result': result,
                    'success': True
                })
                
                logger.info(f"Task {task.task_id} step {step_index}: {result}")
                
            except Exception as step_error:
                logger.error(
                    f"Task {task.task_id} step {step_index} failed: {step_error}"
                )
                step_results.append({
                    'step_index': step_index,
                    'action': step['action'],
                    'error': str(step_error),
                    'success': False
                })
                
                # Fail the entire task if a step fails
                raise TaskExecutionError(
                    task.task_id,
                    step_index,
                    str(step_error)
                )
        
        logger.info(f"Task {task.task_id} completed successfully")
        
        return {
            'success': True,
            'task_id': task.task_id,
            'name': task.name,
            'steps_completed': len(step_results),
            'intelligent_actions_used': intelligent_actions_count,
            'results': step_results
        }
        
    except asyncio.TimeoutError:
        error_msg = f"Task timed out after {task.timeout}s"
        logger.error(f"Task {task.task_id}: {error_msg}")
        
        return {
            'success': False,
            'task_id': task.task_id,
            'name': task.name,
            'error': error_msg,
            'error_type': 'timeout',
            'steps_completed': len(step_results),
            'failed_at_step': current_step_index,
            'results': step_results
        }
        
    except TaskExecutionError as e:
        return {
            'success': False,
            'task_id': task.task_id,
            'name': task.name,
            'error': str(e),
            'error_type': 'execution_error',
            'steps_completed': len(step_results),
            'failed_at_step': e.step_index,
            'results': step_results
        }
        
    except Exception as e:
        logger.error(f"Task {task.task_id} failed with unexpected error: {e}")
        
        return {
            'success': False,
            'task_id': task.task_id,
            'name': task.name,
            'error': str(e),
            'error_type': 'unexpected_error',
            'steps_completed': len(step_results),
            'failed_at_step': current_step_index,
            'results': step_results
        }
        
    finally:
        if browser_instance:
            had_error = len(step_results) == 0 or not step_results[-1].get('success', False)
            await pool.release_browser_instance(browser_instance, had_error=had_error)

async def _execute_intelligent_tasks_parallel(
    tasks: List[IntelligentParallelTask],
    pool: BrowserPool
) -> Dict[str, Any]:
    """
    Execute intelligent tasks in parallel with error handling.
    
    Args:
        tasks: List of tasks to execute
        pool: Browser pool for execution
        
    Returns:
        Dictionary of results by task_id
    """
    executor = IntelligentParallelExecutor(pool)
    
    # Execute all tasks in parallel with timeouts
    task_coroutines = []
    for task in tasks:
        # Wrap each task execution with timeout
        coro = asyncio.wait_for(
            _execute_single_task(task, pool, executor),
            timeout=task.timeout
        )
        task_coroutines.append(coro)
    
    # Gather all results, capturing exceptions
    results = await asyncio.gather(*task_coroutines, return_exceptions=True)
    
    # Process results
    results_dict = {}
    for i, result in enumerate(results):
        task = tasks[i]
        
        if isinstance(result, asyncio.TimeoutError):
            results_dict[task.task_id] = {
                'success': False,
                'task_id': task.task_id,
                'name': task.name,
                'error': f'Task timed out after {task.timeout}s',
                'error_type': 'timeout'
            }
        elif isinstance(result, Exception):
            results_dict[task.task_id] = {
                'success': False,
                'task_id': task.task_id,
                'name': task.name,
                'error': str(result),
                'error_type': 'exception'
            }
        else:
            results_dict[task.task_id] = result
    
    return results_dict

@tool
async def execute_intelligent_parallel_tasks(
    tasks_json: str,
    headless: bool = True
) -> str:
    """
    Execute parallel tasks with intelligent, adaptive actions and comprehensive error handling.
    
    Args:
        tasks_json: JSON string containing array of task definitions
        headless: Whether to run browsers in headless mode
        
    Returns:
        Formatted summary of execution results
        
    Raises:
        ValidationError: If input validation fails
        BrowserAutomationError: If execution fails critically
    """
    pool = None
    
    try:
        # Validate and parse input
        logger.info("Validating tasks JSON")
        tasks_data = validate_tasks_json(tasks_json)
        
        logger.info(f"Creating {len(tasks_data)} tasks")
        intelligent_tasks = [
            IntelligentParallelTask.from_dict(task_data)
            for task_data in tasks_data
        ]
        
        # Sort by priority (higher first)
        intelligent_tasks.sort(key=lambda t: t.priority, reverse=True)
        
        # Initialize browser pool
        logger.info("Initializing browser pool")
        pool = BrowserPool(
            max_browsers=min(len(intelligent_tasks), settings.MAX_BROWSERS),
            headless=headless
        )
        await pool.initialize()
        
        # Execute tasks
        logger.info(f"Executing {len(intelligent_tasks)} tasks in parallel")
        results = await _execute_intelligent_tasks_parallel(intelligent_tasks, pool)
        
        # Generate summary
        summary = _generate_execution_summary(intelligent_tasks, results)
        
        logger.info("Task execution completed")
        return summary
        
    except ValidationError as e:
        error_msg = f"Validation failed: {str(e)}"
        logger.error(error_msg)
        return f"ERROR: {error_msg}"
        
    except BrowserAutomationError as e:
        error_msg = f"Browser automation failed: {str(e)}"
        logger.error(error_msg)
        return f"ERROR: {error_msg}"
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception("Unexpected error during task execution")
        return f"ERROR: {error_msg}"
        
    finally:
        if pool:
            logger.info("Cleaning up browser pool")
            try:
                await pool.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

def _generate_execution_summary(
    tasks: List[IntelligentParallelTask],
    results: Dict[str, Any]
) -> str:
    """
    Generate a formatted summary of execution results.
    
    Args:
        tasks: List of executed tasks
        results: Dictionary of results by task_id
        
    Returns:
        Formatted summary string
    """
    summary_lines = [
        "=" * 60,
        "INTELLIGENT PARALLEL EXECUTION COMPLETED",
        "=" * 60,
        f"Total Tasks: {len(tasks)}",
        ""
    ]
    
    # Count results
    successful = sum(1 for r in results.values() if r.get('success', False))
    failed = len(results) - successful
    total_intelligent_actions = sum(
        r.get('intelligent_actions_used', 0)
        for r in results.values()
        if r.get('success', False)
    )
    
    summary_lines.extend([
        f"✓ Successful: {successful}",
        f"✗ Failed: {failed}",
        f"🤖 AI Actions Used: {total_intelligent_actions}",
        "",
        "Task Results:",
        "-" * 60
    ])
    
    # Individual task results
    for task in tasks:
        result = results.get(task.task_id, {})
        status = "✓ SUCCESS" if result.get('success', False) else "✗ FAILED"
        
        summary_lines.append(f"\n{status} - {result.get('name', task.name)}")
        summary_lines.append(f"  Task ID: {task.task_id}")
        
        if result.get('success', False):
            summary_lines.append(f"  Steps Completed: {result.get('steps_completed', 0)}")
            if result.get('intelligent_actions_used'):
                summary_lines.append(f"  AI Actions: {result['intelligent_actions_used']}")
        else:
            error_type = result.get('error_type', 'unknown')
            summary_lines.append(f"  Error Type: {error_type}")
            summary_lines.append(f"  Error: {result.get('error', 'Unknown error')}")
            if 'failed_at_step' in result:
                summary_lines.append(f"  Failed at Step: {result['failed_at_step']}")
    
    summary_lines.extend([
        "",
        "=" * 60
    ])
    
    return "\n".join(summary_lines)