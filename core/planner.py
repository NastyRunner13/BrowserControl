import json
import os
import time
import asyncio
from typing import List, Dict, Any, Optional, Union
from langchain_groq import ChatGroq
from pydantic import SecretStr  
from config.settings import settings
from utils.logger import setup_logger
from utils.helpers import parse_json_safely
from tools.automation_tools import execute_intelligent_parallel_tasks
from models.actions import AgentOutput, parse_agent_output
from models.plan import AgentPlan

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
        
        self._fallback_llm = self._create_fallback_llm()
        self._using_fallback = False
    
    def _create_fallback_llm(self):
        """Create fallback LLM if configured."""
        if not settings.ENABLE_LLM_FALLBACK or not settings.FALLBACK_LLM_MODEL:
            return None
        
        try:
            fallback_key = settings.FALLBACK_LLM_API_KEY or settings.GROQ_API_KEY
            secret_key = SecretStr(fallback_key) if isinstance(fallback_key, str) else fallback_key
            return ChatGroq(
                model=settings.FALLBACK_LLM_MODEL,
                temperature=0.1,
                api_key=secret_key
            )
        except Exception as e:
            logger.warning(f"Failed to create fallback LLM: {e}")
            return None
    
    async def _invoke_with_fallback(self, messages: list) -> object:
        """
        Invoke LLM with automatic fallback on provider errors.
        
        Catches rate limits (429), auth errors (401/402), and server errors (500-504)
        and retries with fallback LLM if available.
        """
        try:
            response = await self.llm.ainvoke(messages)
            # If we were using fallback and primary works again, switch back
            if self._using_fallback:
                logger.info("Primary LLM recovered, switching back")
                self._using_fallback = False
            return response
        except Exception as e:
            error_str = str(e).lower()
            is_provider_error = any(code in error_str for code in [
                '429', '401', '402', '500', '502', '503', '504',
                'rate limit', 'rate_limit', 'quota', 'too many requests',
                'server error', 'internal server error', 'service unavailable'
            ])
            
            if is_provider_error and self._fallback_llm:
                logger.warning(f"Primary LLM failed ({e}), switching to fallback")
                self._using_fallback = True
                try:
                    return await self._fallback_llm.ainvoke(messages)
                except Exception as fallback_err:
                    logger.error(f"Fallback LLM also failed: {fallback_err}")
                    raise  # Re-raise fallback error
            
            raise  # Re-raise original error if not a provider error or no fallback

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
        2. "intelligent_type": {"action": "intelligent_type", "description": "...", "text": "...", "press_enter": true} 
        (Set press_enter to true ONLY if you want to submit a search immediately)
        3. "intelligent_click": {"action": "intelligent_click", "description": "element visual description"}
        4. "intelligent_wait": {"action": "intelligent_wait", "condition": "element", "description": "what to wait for", "timeout": 10000}
        5. "intelligent_extract": {"action": "intelligent_extract", "description": "element to read", "data_type": "text", "store_as": "variable_name"}
        6. "screenshot": {"action": "screenshot", "filename": "result_context.png"}
        7. "wait": {"action": "wait", "seconds": 2}
        8. "scroll": {"action": "scroll", "direction": "down|up|left|right", "amount": 500}
        9. "final_answer": {"action": "final_answer", "answer": "The answer to user's question with extracted data"}
        10. "hover": {"action": "hover", "description": "element to hover over"}
        11. "select_option": {"action": "select_option", "description": "dropdown element", "value": "option value", "by": "value|label|index"}
        
        TAB MANAGEMENT:
        12. "new_tab": {"action": "new_tab", "url": "https://..."} - Open a new tab
        13. "switch_tab": {"action": "switch_tab", "tab_index": 0} - Switch to tab by index
        14. "close_tab": {"action": "close_tab", "tab_index": 0} - Close a tab (optional index)
        15. "list_tabs": {"action": "list_tabs"} - List all open tabs

        RULES:
        - Return ONLY a JSON list of task objects. No markdown, no explanations.
        - "task_id" should be short, snake_case, and unique.
        - Always start with "navigate".
        - Use "intelligent_extract" to get data from pages, then "final_answer" to respond to user questions.
        - Use tab actions when user needs to work across multiple sites/pages.
        
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
            response = await self._invoke_with_fallback([
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
        
        self._fallback_llm = self._create_fallback_llm()
        self._using_fallback = False
        
        self.max_steps = max_steps or settings.MAX_AGENT_STEPS
        self.enable_self_correction = enable_self_correction if enable_self_correction is not None else settings.ENABLE_SELF_CORRECTION
        self.action_history: List[Dict[str, Any]] = []
        self.plan: Optional[AgentPlan] = None
        self.consecutive_failures: int = 0
    
    def _create_fallback_llm(self):
        """Create fallback LLM if configured."""
        if not settings.ENABLE_LLM_FALLBACK or not settings.FALLBACK_LLM_MODEL:
            return None
        
        try:
            fallback_key = settings.FALLBACK_LLM_API_KEY or settings.GROQ_API_KEY
            secret_key = SecretStr(fallback_key) if isinstance(fallback_key, str) else fallback_key
            return ChatGroq(
                model=settings.FALLBACK_LLM_MODEL,
                temperature=0.1,
                api_key=secret_key
            )
        except Exception as e:
            logger.warning(f"Failed to create fallback LLM: {e}")
            return None
    
    async def _invoke_with_fallback(self, messages: list) -> object:
        """
        Invoke LLM with automatic fallback on provider errors.
        
        Catches rate limits (429), auth errors (401/402), and server errors (500-504)
        and retries with fallback LLM if available.
        """
        try:
            response = await self.llm.ainvoke(messages)
            if self._using_fallback:
                logger.info("Primary LLM recovered, switching back")
                self._using_fallback = False
            return response
        except Exception as e:
            error_str = str(e).lower()
            is_provider_error = any(code in error_str for code in [
                '429', '401', '402', '500', '502', '503', '504',
                'rate limit', 'rate_limit', 'quota', 'too many requests',
                'server error', 'internal server error', 'service unavailable'
            ])
            
            if is_provider_error and self._fallback_llm:
                logger.warning(f"Primary LLM failed ({e}), switching to fallback")
                self._using_fallback = True
                try:
                    return await self._fallback_llm.ainvoke(messages)
                except Exception as fallback_err:
                    logger.error(f"Fallback LLM also failed: {fallback_err}")
                    raise
            
            raise
    
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
        task_context = None
        tab_manager = None
        
        try:
            # Initialize browser pool and context
            from core.browser_pool import BrowserPool
            from core.executor import IntelligentParallelExecutor
            from core.tab_manager import TabManager
            from core.task_context import TaskContext
            
            pool = BrowserPool(max_browsers=1, headless=headless)
            await pool.initialize()
            
            # Get browser instance
            browser_instance = await pool.get_browser_instance("dynamic_agent")
            page = browser_instance.page
            executor = IntelligentParallelExecutor(pool)
            
            # Initialize TabManager and TaskContext
            tab_manager = TabManager(browser_instance.context, initial_page=page)
            task_context = TaskContext(original_goal=user_goal)
            self._task_context = task_context  # Store for access in _decide_next_action
            
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
                
                # 2. Decide next action (now with TaskContext for memory)
                next_action = await self._decide_next_action(
                    user_goal, 
                    state, 
                    self.action_history,
                    task_context=task_context
                )
                
                if not next_action:
                    logger.error("❌ Agent failed to decide next action")
                    print("❌ Failed to decide next action")
                    break
                
                # Update plan from LLM response (if it provided one)
                plan_items = next_action.get('plan')
                if plan_items and isinstance(plan_items, list):
                    str_items = [str(item) for item in plan_items if item]
                    if str_items:
                        if self.plan is None:
                            self.plan = AgentPlan.from_text_list(str_items, step_number=step_count)
                            logger.info(f"📋 Plan created with {len(str_items)} steps")
                            print(f"📋 Plan created ({len(str_items)} steps)")
                        else:
                            self.plan.update_plan(str_items, step_number=step_count)
                            logger.info(f"📋 Plan revised (revision #{self.plan.revision_count})")
                            print(f"📋 Plan revised (revision #{self.plan.revision_count})")
                
                # Loop detection: if the same action+description repeats 3+ times, force final_answer
                action_key = f"{next_action.get('action')}:{next_action.get('description', '')}"
                recent_actions = [
                    f"{h['action'].get('action')}:{h['action'].get('description', '')}" 
                    for h in self.action_history[-4:]
                ]
                repeat_count = sum(1 for a in recent_actions if a == action_key)
                if repeat_count >= 2:
                    logger.warning(f"⚠️ Loop detected: '{action_key}' repeated {repeat_count + 1} times. Forcing final_answer.")
                    print(f"⚠️ Loop detected, generating final answer with collected data...")
                    # Use whatever data we have
                    if task_context and task_context.has_data_for_answer():
                        summary = task_context.build_summary()
                        extracted = summary.get('extracted_data', {})
                        answer_parts = []
                        for key, value in extracted.items():
                            answer_parts.append(f"{key}: {value}")
                        answer = "Based on the data I extracted:\n" + "\n".join(answer_parts) if answer_parts else "I was unable to extract the requested information."
                    else:
                        answer = "I was unable to fully complete the task after multiple attempts."
                    print(f"\n✅ FINAL ANSWER: {answer}\n")
                    task_context.set_final_answer(answer)
                    goal_achieved = True
                    break
                
                # Check if goal is achieved
                if next_action.get('action') == 'goal_achieved':
                    print(f"✅ Goal achieved!")
                    if next_action.get('reasoning'):
                        print(f"   Reason: {next_action['reasoning']}")
                    goal_achieved = True
                    break
                
                # Check if final_answer - this also ends execution
                if next_action.get('action') == 'final_answer':
                    answer = next_action.get('answer', 'Task completed.')
                    print(f"\n✅ FINAL ANSWER: {answer}\n")
                    if task_context:
                        task_context.set_final_answer(answer)
                    goal_achieved = True
                    break
                
                print(f"🎬 Action: {next_action.get('action')}")
                if next_action.get('description'):
                    print(f"   Target: {next_action['description']}")
                if next_action.get('url'):
                    print(f"   URL: {next_action['url']}")
                
                # 3. Execute action with self-correction (pass context and tab manager)
                execution_result = await self._execute_with_correction(
                    page, 
                    executor, 
                    next_action,
                    state,
                    context_obj=task_context,
                    tab_manager=tab_manager
                )
                
                # Update page reference if tab was switched
                if tab_manager and next_action.get('action') in ['switch_tab', 'new_tab']:
                    page = tab_manager.active_page
                
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
                    self.consecutive_failures = 0
                    # Advance plan on success
                    if self.plan and not self.plan.is_complete:
                        self.plan.advance()
                elif status == 'failed':
                    print(f"✗ Failed: {execution_result.get('error', 'Unknown error')}")
                    self.consecutive_failures += 1
                    if self.plan and not self.plan.is_complete:
                        self.plan.mark_current_failed()
                
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
            
            # Show extracted data and final answer
            if task_context:
                if task_context.final_answer:
                    print(f"\n📝 FINAL ANSWER: {task_context.final_answer}")
                if task_context.extracted_data:
                    print(f"📊 Extracted Data: {task_context.extracted_data}")
            
            print(f"{'='*60}\n")
            
            # Build result with TaskContext data
            result = {
                'success': goal_achieved,
                'steps_taken': step_count,
                'history': self.action_history
            }
            
            if task_context:
                result['final_answer'] = task_context.final_answer
                result['extracted_data'] = task_context.extracted_data
                result['visited_urls'] = task_context.visited_urls
                result['screenshots'] = task_context.screenshots
            
            return result
            
        except Exception as e:
            logger.error(f"Dynamic agent failed: {e}")
            print(f"\n❌ Agent Error: {e}")
            result = {
                'success': False,
                'error': str(e),
                'steps_taken': step_count if 'step_count' in locals() else 0,
                'history': self.action_history
            }
            if task_context:
                result['extracted_data'] = task_context.extracted_data
            return result
            
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
            
            # Get more visible text for better reasoning (1500 chars with smart sampling)
            visible_text = await page.evaluate("""
                () => {
                    const body = document.body;
                    const text = body.innerText;
                    if (text.length > 2000) {
                        return text.substring(0, 1200) + ' ... ' + text.substring(text.length - 300);
                    }
                    return text.substring(0, 1500);
                }
            """)
            
            # Get summary of interactive elements on page
            input_fields = await page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('input, textarea, [role="search"], select'))
                        .slice(0, 8)
                        .map(el => ({
                            type: el.type || el.tagName.toLowerCase(),
                            placeholder: el.placeholder || '',
                            ariaLabel: el.getAttribute('aria-label') || '',
                            name: el.name || '',
                            id: el.id || ''
                        }))
                        .filter(el => el.placeholder || el.ariaLabel || el.name || el.id);
                }
            """)
            
            return {
                'url': url,
                'title': title,
                'visible_text': visible_text,
                'input_fields': input_fields
            }
            
        except Exception as e:
            logger.error(f"Failed to capture state: {e}")
            return {
                'url': 'unknown',
                'title': 'unknown',
                'visible_text': '',
                'input_fields': []
            }
    
    async def _decide_next_action(
        self, 
        user_goal: str, 
        current_state: Dict[str, Any],
        history: List[Dict[str, Any]],
        task_context: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to decide the next single action based on current state."""
        # Format recent history - INCLUDE RESULTS so LLM knows what data it has
        recent_history = history[-settings.AGENT_HISTORY_LENGTH:] if len(history) > settings.AGENT_HISTORY_LENGTH else history
        history_lines = []
        for h in recent_history:
            action = h['action'].get('action', 'unknown')
            status = h['result'].get('status', 'unknown')
            result_data = h['result'].get('result', '')
            
            # Longer truncation for extract actions (300 chars) vs others (150 chars)
            max_len = 300 if action == 'intelligent_extract' else 150
            if result_data and len(str(result_data)) > max_len:
                result_data = str(result_data)[:max_len] + "..."
            
            line = f"  {h['step']}. {action}"
            if h['action'].get('description'):
                line += f" → '{h['action']['description']}'"
            if h['action'].get('url'):
                line += f" → {h['action']['url']}"
            line += f" → {status}"
            if result_data and action in ['intelligent_extract', 'navigate', 'intelligent_click']:
                line += f" | Data: {result_data}"
            history_lines.append(line)
        
        history_text = "\n".join(history_lines)
        
        # Build extracted data context from TaskContext
        extracted_data_text = ""
        if task_context and hasattr(task_context, 'get_context_for_llm'):
            ctx_text = task_context.get_context_for_llm()
            if ctx_text:
                extracted_data_text = f"\n{ctx_text}\n"
        
        # Format input fields info
        input_fields_text = ""
        input_fields = current_state.get('input_fields', [])
        if input_fields:
            fields_desc = ", ".join(
                f"{f.get('type', '?')}" + 
                (f"('{f['placeholder']}'" if f.get('placeholder') else 
                 f"('{f['ariaLabel']}'" if f.get('ariaLabel') else 
                 f"('{f['name']}'" if f.get('name') else "(") + ")"
                for f in input_fields[:5]
            )
            input_fields_text = f"\n- Input Fields on Page: {fields_desc}"
        
        prompt = f"""You are an autonomous web automation agent that completes tasks step by step.

GOAL: {user_goal}

CURRENT STATE:
- URL: {current_state['url']}
- Page Title: {current_state['title']}{input_fields_text}
- Visible Page Content:
{current_state['visible_text'][:1200]}

HISTORY (Recent Actions):
{history_text if history_text else 'No actions yet'}
{extracted_data_text}
{self.plan.format_for_prompt() if self.plan else 'No plan yet — create one with your first action.'}
{('⚠️ You have failed ' + str(self.consecutive_failures) + ' consecutive actions. Consider replanning.') if self.consecutive_failures >= 2 else ''}
AVAILABLE ACTIONS:
- navigate: Go to URL {{"action": "navigate", "url": "https://..."}}
- intelligent_click: Click element {{"action": "intelligent_click", "description": "what to click"}}
- intelligent_type: Type text {{"action": "intelligent_type", "description": "input field", "text": "...", "press_enter": true/false}}
- intelligent_extract: Get data {{"action": "intelligent_extract", "description": "what to extract"}}
- scroll: Scroll page {{"action": "scroll", "direction": "down", "amount": 500}}
- wait: Wait {{"action": "wait", "seconds": 2}}
- new_tab: New tab {{"action": "new_tab", "url": "https://..."}}
- switch_tab: Switch tab {{"action": "switch_tab", "tab_index": 0}}
- final_answer: END execution {{"action": "final_answer", "answer": "Your complete response with ALL extracted data"}}

RULES:
1. Return exactly ONE action per response as JSON
2. Infer URLs from site names (e.g., "Amazon" → https://www.amazon.in, "Flipkart" → https://www.flipkart.com)
3. Use SCROLL when you need to see more content on the page
4. Use CLICK to navigate deeper (e.g., click a link to see full details)
5. Check HISTORY - don't repeat the same action or revisit completed sites
6. Use FINAL_ANSWER when you have all info needed to answer the user - this ENDS execution
7. When using FINAL_ANSWER, include ALL previously extracted data in your answer
8. For extraction, be SPECIFIC about what you want (e.g., "product prices" not just "data")
9. After typing in a search box, set press_enter to true to submit the search

Respond with ONLY a JSON object (no markdown):
{{
  "action": "action_name",
  "url": "..." (for navigate/new_tab),
  "description": "..." (for click/type/extract),
  "text": "..." (for type),
  "press_enter": true/false (for type),
  "direction": "down" (for scroll),
  "amount": 500 (for scroll),
  "answer": "..." (for final_answer),
  "reasoning": "why this action",
  "plan": ["step 1 description", "step 2 description", ...] (ONLY include on first action or when replanning)
}}

"""

        try:
            response = await self._invoke_with_fallback([{"role": "user", "content": prompt}])
            
            # Parse response
            content = response.content if isinstance(response.content, str) else str(response.content)
            
            # Try to extract JSON
            raw_action = parse_json_safely(content)
            
            if not raw_action or 'action' not in raw_action:
                logger.error(f"Invalid action format from LLM: {content}")
                return None
            
            # Validate with Pydantic model (graceful fallback to raw dict)
            try:
                agent_output = parse_agent_output(raw_action)
                logger.debug(f"Validated action: {agent_output.action} (params validated: {agent_output.params is not None})")
                return agent_output
            except Exception as validation_err:
                logger.warning(f"Action validation warning (using raw dict): {validation_err}")
                return raw_action
            
        except Exception as e:
            logger.error(f"Failed to decide next action: {e}")
            return None
    
    async def _execute_with_correction(
        self,
        page,
        executor,
        action: Dict[str, Any],
        state: Dict[str, Any],
        max_retries: Optional[int] = None,
        context_obj: Optional[Any] = None,
        tab_manager: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute action with self-correction on failure."""
        max_retries = max_retries or settings.MAX_CORRECTION_ATTEMPTS
        attempt = 0
        last_error = None
        
        while attempt <= max_retries:
            try:
                # Execute the action with context and tab manager
                result = await executor.execute_intelligent_step(
                    page, 
                    action, 
                    task_context="",
                    context_obj=context_obj,
                    tab_manager=tab_manager
                )
                
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
            response = await self._invoke_with_fallback([{"role": "user", "content": prompt}])
            content = response.content if isinstance(response.content, str) else str(response.content)
            
            corrected = parse_json_safely(content)
            
            if not corrected or corrected.get('action') == 'give_up':
                return None
            
            # Validate corrected action with Pydantic
            try:
                agent_output = parse_agent_output(corrected)
                logger.info(f"Agent suggested correction: {agent_output.action}")
                return agent_output
            except Exception:
                logger.info(f"Agent suggested correction: {corrected.get('action')} (raw)")
                return corrected
            
        except Exception as e:
            logger.error(f"Failed to get correction: {e}")
            return None