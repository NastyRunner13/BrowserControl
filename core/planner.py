import json
import os
import time
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