import json
import os
import time
import asyncio
from typing import List, Dict, Any, Optional
from langchain_groq import ChatGroq
from pydantic import SecretStr  
from config.settings import settings
from utils.logger import setup_logger
from utils.helpers import parse_json_safely
from tools.automation_tools import execute_intelligent_parallel_tasks

logger = setup_logger(__name__)

class AutomationAgent:
    """
    The 'Brain' of the operation. 
    Translates Natural Language -> Structured JSON -> Execution.
    """
    def __init__(self):
        api_key_value = settings.GROQ_API_KEY
        if not api_key_value:
            raise ValueError("GROQ_API_KEY not found in settings")
            
        secret_api_key = SecretStr(api_key_value) if isinstance(api_key_value, str) else api_key_value

        self.llm = ChatGroq(
            model=settings.LLM_MODEL,
            temperature=0.1,
            api_key=secret_api_key 
        )

    async def run(self, user_request: str, headless: bool = False):
        """Main entry point: Plan and Execute."""
        logger.info(f"Agent received request: {user_request}")
        print(f"\n🤖 Agent: Analyzing request: '{user_request}'...")

        # 1. Generate Plan
        task_schema = await self._plan_task(user_request)
        
        if not task_schema:
            logger.error("Failed to generate plan")
            print("❌ Agent: I couldn't figure out how to do that. Please try again.")
            return

        # 2. Save Plan
        self._save_plan_to_disk(task_schema, user_request)

        # 3. Execute Plan
        print(f"📋 Agent: Generated {len(task_schema[0]['steps'])} steps. Executing...")
        try:
            result = await execute_intelligent_parallel_tasks.ainvoke({
                "tasks_json": json.dumps(task_schema),
                "headless": headless
            })
            print(result)
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            print(f"❌ Execution Error: {e}")

    async def _plan_task(self, user_request: str) -> Optional[List[Dict[str, Any]]]:
        """Uses LLM to convert natural language to BrowserControl JSON format."""
        
        system_prompt = """
        You are an expert browser automation architect. 
        Convert the user's natural language request into a strictly formatted JSON task list for the BrowserControl framework.

        AVAILABLE ACTIONS:
        1. "navigate": {"action": "navigate", "url": "https://..."}
        2. "intelligent_type": {"action": "intelligent_type", "description": "element visual description", "text": "what to type"}
        3. "intelligent_click": {"action": "intelligent_click", "description": "element visual description"}
        4. "intelligent_wait": {"action": "intelligent_wait", "condition": "element", "description": "what to wait for", "timeout": 10000}
        5. "intelligent_extract": {"action": "intelligent_extract", "description": "element to read", "data_type": "text"}
        6. "screenshot": {"action": "screenshot", "filename": "result_context.png"}
        7. "wait": {"action": "wait", "seconds": 2}

        RULES:
        - Return ONLY a JSON list of task objects. No markdown, no explanations.
        - "task_id" should be short, snake_case, and unique.
        - Always start with "navigate".
        
        EXAMPLE OUTPUT STRUCTURE:
        [
            {
                "task_id": "example_task",
                "name": "Example",
                "steps": [...]
            }
        ]
        """
        
        try:
            response = await self.llm.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_request}
            ])
            
            content = response.content if isinstance(response.content, str) else str(response.content)
            parsed_content = parse_json_safely(content)

            # Fix 3: Ensure return type is always a List[Dict]
            if isinstance(parsed_content, dict):
                return [parsed_content]
            elif isinstance(parsed_content, list):
                return parsed_content
            return None
            
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return None

    def _save_plan_to_disk(self, plan: List[Dict], request: str):
        """Saves the generated plan to logs for debugging/auditing."""
        try:
            timestamp = int(time.time())
            filename = f"plan_{timestamp}.json"
            filepath = os.path.join(settings.LOG_DIR, filename)
            
            data = {
                "timestamp": timestamp,
                "user_request": request,
                "plan": plan
            }
            
            # Ensure directory exists
            os.makedirs(settings.LOG_DIR, exist_ok=True)
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Plan saved to {filepath}")
        except Exception as e:
            logger.warning(f"Could not save plan to disk: {e}")


class DynamicAutomationAgent:
    """
    Dynamic agent with self-correction and replanning capabilities.
    
    Unlike the linear planner, this agent:
    1. Observes current state (screenshot + DOM snapshot)
    2. Decides ONE next action based on current state
    3. Executes and observes result
    4. Self-corrects if action fails
    5. Loops until goal achieved or max steps reached
    """
    
    def __init__(self, max_steps: Optional[int] = None, enable_self_correction: Optional[bool] = None):
        api_key_value = settings.GROQ_API_KEY
        if not api_key_value:
            raise ValueError("GROQ_API_KEY not found")
        
        secret_api_key = SecretStr(api_key_value) if isinstance(api_key_value, str) else api_key_value
        
        self.llm = ChatGroq(
            model=settings.LLM_MODEL,
            temperature=0.1,
            api_key=secret_api_key
        )
        
        self.max_steps = max_steps or settings.MAX_AGENT_STEPS
        self.enable_self_correction = enable_self_correction if enable_self_correction is not None else settings.ENABLE_SELF_CORRECTION
        self.action_history: List[Dict[str, Any]] = []
    
    async def run_dynamic(self, user_goal: str, headless: bool = False):
        """
        Main agent loop with dynamic replanning.
        
        Args:
            user_goal: Natural language goal
            headless: Run browser in headless mode
        """
        logger.info(f"🤖 Dynamic agent starting for goal: {user_goal}")
        print(f"\n{'='*60}")
        print(f"🎯 Goal: {user_goal}")
        print(f"🔄 Max Steps: {self.max_steps}")
        print(f"🔧 Self-Correction: {'Enabled' if self.enable_self_correction else 'Disabled'}")
        print(f"{'='*60}\n")
        
        pool = None
        browser_instance = None
        step_count = 0
        
        try:
            # Initialize browser pool
            from core.browser_pool import BrowserPool
            from core.executor import IntelligentParallelExecutor
            
            pool = BrowserPool(max_browsers=1, headless=headless)
            await pool.initialize()
            
            # Get browser instance
            browser_instance = await pool.get_browser_instance("dynamic_agent")
            page = browser_instance.page
            executor = IntelligentParallelExecutor(pool)
            
            # Agent loop
            step_count = 0
            goal_achieved = False
            
            while step_count < self.max_steps and not goal_achieved:
                step_count += 1
                print(f"\n{'─'*60}")
                print(f"📍 Step {step_count}/{self.max_steps}")
                print(f"{'─'*60}")
                
                # 1. Observe current state
                state = await self._capture_state(page)
                
                # 2. Decide next action
                next_action = await self._decide_next_action(
                    user_goal, 
                    state, 
                    self.action_history
                )
                
                if not next_action:
                    logger.error("❌ Agent failed to decide next action")
                    print("❌ Failed to decide next action")
                    break
                
                # Check if goal is achieved
                if next_action.get('action') == 'goal_achieved':
                    print(f"✅ Goal achieved!")
                    if next_action.get('reasoning'):
                        print(f"   Reason: {next_action['reasoning']}")
                    goal_achieved = True
                    break
                
                print(f"🎬 Action: {next_action.get('action')}")
                if next_action.get('description'):
                    print(f"   Target: {next_action['description']}")
                if next_action.get('url'):
                    print(f"   URL: {next_action['url']}")
                
                # 3. Execute action with self-correction
                execution_result = await self._execute_with_correction(
                    page, 
                    executor, 
                    next_action,
                    state
                )
                
                # 4. Record history
                self.action_history.append({
                    'step': step_count,
                    'action': next_action,
                    'result': execution_result,
                    'timestamp': asyncio.get_event_loop().time()
                })
                
                # 5. Short delay for page stabilization
                await asyncio.sleep(1)
                
                # Display result
                status = execution_result.get('status', 'unknown')
                if status == 'success':
                    print(f"✓ Success")
                elif status == 'failed':
                    print(f"✗ Failed: {execution_result.get('error', 'Unknown error')}")
                
                # Check if we should abort
                if execution_result.get('status') == 'critical_failure':
                    logger.error("Critical failure detected, aborting")
                    print("❌ Critical failure - aborting")
                    break
            
            # Summary
            print(f"\n{'='*60}")
            if goal_achieved:
                print("✅ SUCCESS: Goal was achieved!")
            elif step_count >= self.max_steps:
                print(f"⚠️  Reached maximum steps ({self.max_steps})")
            else:
                print("❌ FAILED: Agent could not complete the goal")
            
            print(f"📊 Total steps executed: {step_count}")
            print(f"{'='*60}\n")
            
            return {
                'success': goal_achieved,
                'steps_taken': step_count,
                'history': self.action_history
            }
            
        except Exception as e:
            logger.error(f"Dynamic agent failed: {e}")
            print(f"\n❌ Agent Error: {e}")
            return {
                'success': False,
                'error': str(e),
                'steps_taken': step_count if 'step_count' in locals() else 0,
                'history': self.action_history
            }
            
        finally:
            if browser_instance and pool:
                await pool.release_browser_instance(browser_instance)
            if pool:
                await pool.cleanup()
    
    async def _capture_state(self, page) -> Dict[str, Any]:
        """Capture current page state for agent decision-making."""
        try:
            url = page.url
            title = await page.title()
            
            # Get snippet of visible text
            visible_text = await page.evaluate("""
                () => {
                    const body = document.body;
                    return body.innerText.substring(0, 500);
                }
            """)
            
            return {
                'url': url,
                'title': title,
                'visible_text': visible_text
            }
            
        except Exception as e:
            logger.error(f"Failed to capture state: {e}")
            return {
                'url': 'unknown',
                'title': 'unknown',
                'visible_text': ''
            }
    
    async def _decide_next_action(
        self, 
        user_goal: str, 
        current_state: Dict[str, Any],
        history: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to decide the next single action based on current state."""
        # Format recent history (last 5 actions)
        recent_history = history[-settings.AGENT_HISTORY_LENGTH:] if len(history) > settings.AGENT_HISTORY_LENGTH else history
        history_text = "\n".join([
            f"  {h['step']}. {h['action'].get('action')} - {h['result'].get('status', 'unknown')}"
            for h in recent_history
        ])
        
        prompt = f"""You are an autonomous web automation agent.

GOAL: {user_goal}

CURRENT STATE:
- URL: {current_state['url']}
- Page Title: {current_state['title']}
- Visible Text (first 500 chars): {current_state['visible_text'][:500]}

HISTORY (Recent Actions):
{history_text if history_text else 'No actions yet'}

TASK: Decide the ONE next action to take toward the goal.

AVAILABLE ACTIONS:
- navigate: Go to a URL
- intelligent_click: Click an element (by description)
- intelligent_type: Type into an element (by description)
- intelligent_wait: Wait for an element to appear
- wait: Wait N seconds
- screenshot: Take a screenshot
- goal_achieved: Goal is complete

IMPORTANT RULES:
1. If the goal is already achieved, return {{"action": "goal_achieved", "reasoning": "why"}}
2. If stuck after multiple failed attempts, try a different approach
3. Handle popups, cookie banners, and navigation carefully
4. Always navigate to a URL first if not already there

Respond with ONLY a JSON object (no markdown, no backticks):
{{
  "action": "action_name",
  "url": "https://..." (if navigate),
  "description": "element description" (if intelligent action),
  "text": "text to type" (if intelligent_type),
  "seconds": 3 (if wait),
  "reasoning": "brief explanation of why this action"
}}"""

        try:
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            
            # Parse response
            content = response.content if isinstance(response.content, str) else str(response.content)
            
            # Try to extract JSON
            action = parse_json_safely(content)
            
            if action and 'action' in action:
                return action
            
            logger.error(f"Invalid action format from LLM: {content}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to decide next action: {e}")
            return None
    
    async def _execute_with_correction(
        self,
        page,
        executor,
        action: Dict[str, Any],
        state: Dict[str, Any],
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute action with self-correction on failure."""
        max_retries = max_retries or settings.MAX_CORRECTION_ATTEMPTS
        attempt = 0
        last_error = None
        
        while attempt <= max_retries:
            try:
                # Execute the action
                result = await executor.execute_intelligent_step(page, action, context="")
                
                return {
                    'status': 'success',
                    'result': result,
                    'attempts': attempt + 1
                }
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Action failed (attempt {attempt + 1}): {e}")
                
                # If self-correction disabled or last attempt, fail
                if not self.enable_self_correction or attempt >= max_retries:
                    return {
                        'status': 'failed',
                        'error': last_error,
                        'attempts': attempt + 1
                    }
                
                # Ask agent to correct the action
                print(f"  ⚠️  Failed: {str(e)[:100]}")
                print(f"  🔧 Attempting self-correction...")
                
                corrected_action = await self._ask_for_correction(
                    action, 
                    last_error, 
                    state
                )
                
                if corrected_action:
                    action = corrected_action
                    attempt += 1
                else:
                    return {
                        'status': 'correction_failed',
                        'error': last_error,
                        'attempts': attempt + 1
                    }
        
        return {
            'status': 'failed_after_retries',
            'error': last_error,
            'attempts': max_retries + 1
        }
    
    async def _ask_for_correction(
        self,
        failed_action: Dict[str, Any],
        error_message: str,
        state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Ask agent to correct a failed action."""
        prompt = f"""The following action FAILED:

ACTION: {json.dumps(failed_action, indent=2)}
ERROR: {error_message}

CURRENT PAGE STATE:
- URL: {state['url']}
- Title: {state['title']}

TASK: Suggest a CORRECTED action that might work better.
For example:
- Try a different element description (more specific, different wording)
- Add a wait before the action
- Use a different approach entirely

Respond with ONLY a JSON object (no markdown, no backticks):
{{
  "action": "corrected_action",
  "description": "new description if needed",
  ...
}}

Or return {{"action": "give_up"}} if no correction is possible."""

        try:
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            content = response.content if isinstance(response.content, str) else str(response.content)
            
            corrected = parse_json_safely(content)
            
            if corrected and corrected.get('action') != 'give_up':
                logger.info(f"Agent suggested correction: {corrected.get('action')}")
                return corrected
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get correction: {e}")
            return None