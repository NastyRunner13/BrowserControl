import json
import asyncio
from typing import List, Dict, Any
from langchain_core.tools import tool
from models.task import IntelligentParallelTask
from core.browser_pool import BrowserPool
from core.executor import IntelligentParallelExecutor
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)

async def _execute_intelligent_tasks_parallel(tasks: List[IntelligentParallelTask], 
                                             pool: BrowserPool) -> Dict[str, Any]:
    """Execute intelligent tasks in parallel."""
    
    executor = IntelligentParallelExecutor(pool)
    results = {}
    
    async def execute_task(task: IntelligentParallelTask):
        """Execute a single task."""
        browser_instance = None
        try:
            browser_instance = await pool.get_browser_instance(task.task_id)
            page = browser_instance.page
            
            step_results = []
            intelligent_actions_count = 0
            
            for step in task.steps:
                result = await executor.execute_intelligent_step(page, step, task.context)
                
                if step['action'].startswith('intelligent_'):
                    intelligent_actions_count += 1
                
                step_results.append(result)
                logger.info(f"Task {task.task_id}: {result}")
            
            results[task.task_id] = {
                'success': True,
                'name': task.name,
                'steps_completed': len(step_results),
                'intelligent_actions_used': intelligent_actions_count,
                'results': step_results
            }
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            results[task.task_id] = {
                'success': False,
                'name': task.name,
                'error': str(e)
            }
        finally:
            if browser_instance:
                await pool.release_browser_instance(browser_instance)
    
    await asyncio.gather(*[execute_task(task) for task in tasks])
    
    return results

@tool
async def execute_intelligent_parallel_tasks(tasks_json: str, headless: bool = True) -> str:
    """
    Execute parallel tasks with intelligent, adaptive actions.
    
    Args:
        tasks_json: JSON string containing array of task definitions
        headless: Whether to run browsers in headless mode
    """
    pool = None
    try:
        tasks_data = json.loads(tasks_json)
        
        intelligent_tasks = [
            IntelligentParallelTask.from_dict(task_data)
            for task_data in tasks_data
        ]
        
        pool = BrowserPool(
            max_browsers=min(len(intelligent_tasks), settings.MAX_BROWSERS),
            headless=headless
        )
        await pool.initialize()
        
        results = await _execute_intelligent_tasks_parallel(intelligent_tasks, pool)
        
        summary = "INTELLIGENT PARALLEL EXECUTION COMPLETED\n"
        summary += f"Tasks: {len(intelligent_tasks)} total\n"
        
        successful = sum(1 for r in results.values() if isinstance(r, dict) and r.get('success', False))
        failed = len(results) - successful
        
        summary += f"Successful: {successful}\n"
        summary += f"Failed: {failed}\n\n"
        
        for task_id, result in results.items():
            if isinstance(result, dict):
                status = "SUCCESS" if result.get('success', False) else "FAILED"
                summary += f"{status} - {result.get('name', task_id)}\n"
                
                if result.get('intelligent_actions_used'):
                    summary += f"  AI Actions: {result['intelligent_actions_used']}\n"
                
                if not result.get('success', False) and 'error' in result:
                    summary += f"  Error: {result['error']}\n"
        
        return summary
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return f"Execution failed: {str(e)}"
    finally:
        if pool:
            await pool.cleanup()