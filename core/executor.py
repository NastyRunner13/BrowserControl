import asyncio
import os
from typing import Dict, Any, Optional
from playwright.async_api import Page
from core.browser_pool import BrowserPool
from core.element_finder import IntelligentElementFinder
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)

class IntelligentParallelExecutor:
    """Enhanced parallel executor with AI-powered step execution and self-correction."""
    
    def __init__(self, browser_pool: BrowserPool):
        self.browser_pool = browser_pool
        self.element_finder = IntelligentElementFinder()
        
        # Initialize LLM for self-correction
        if settings.ENABLE_SELF_CORRECTION:
            from langchain_groq import ChatGroq
            from pydantic import SecretStr
            api_key = settings.GROQ_API_KEY
            self.correction_llm = ChatGroq(
                model=settings.LLM_MODEL,
                temperature=0.1,
                api_key=SecretStr(api_key) if isinstance(api_key, str) else api_key
            )
            logger.info("Self-correction enabled")
        else:
            self.correction_llm = None
    
    async def _ask_for_correction(
        self, 
        page: Page,
        failed_description: str, 
        error: str
    ) -> Optional[str]:
        """
        Ask LLM to suggest a better element description.
        
        Args:
            page: The current page
            failed_description: The description that failed
            error: The error message
            
        Returns:
            Corrected description or None if correction not possible
        """
        if not settings.ENABLE_SELF_CORRECTION or not self.correction_llm:
            return None
        
        try:
            # Get current page state
            visible_text = await page.evaluate("""
                () => document.body.innerText.substring(0, 500)
            """)
            
            prompt = f'''The element description "{failed_description}" failed to find a match.
Error: {error}

Current page text (first 500 chars):
{visible_text}

Your task: Suggest a BETTER, more specific description for the same element.
Consider:
- Synonyms or alternative wording
- Position clues (top, bottom, left, right)
- Nearby text or labels
- Element type (button, link, input, etc.)

Respond with ONLY the new description (one line, no explanation).
If correction is not possible, respond with "CANNOT_CORRECT".'''

            response = await self.correction_llm.ainvoke([{
                "role": "user", 
                "content": prompt
            }])
            
            corrected = response.content.strip() if isinstance(response.content, str) else str(response.content).strip()
            
            if corrected and corrected != failed_description and corrected != "CANNOT_CORRECT":
                logger.info(f"🔧 Correction suggested: '{failed_description}' → '{corrected}'")
                return corrected
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get correction: {e}")
            return None
    
    async def execute_intelligent_step(self, page: Page, step: Dict[str, Any], 
                                     task_context: str = "") -> str:
        """Execute a step with intelligent reasoning capabilities."""
        action = step['action']
        
        if action == 'intelligent_click':
            return await self._intelligent_click(page, step, task_context)
        elif action == 'intelligent_type':
            return await self._intelligent_type(page, step, task_context)
        elif action == 'intelligent_extract':
            return await self._intelligent_extract(page, step, task_context)
        elif action == 'intelligent_wait':
            return await self._intelligent_wait(page, step, task_context)
        elif action == 'navigate':
            await page.goto(step['url'], wait_until='domcontentloaded', timeout=settings.BROWSER_TIMEOUT)
            return f"Navigated to {step['url']}"
        elif action == 'click':
            await page.click(step['selector'], timeout=10000)
            return f"Clicked {step['selector']}"
        elif action == 'type':
            await page.fill(step['selector'], step['text'], timeout=10000)
            return f"Typed into {step['selector']}"
        elif action == 'wait':
            seconds = step.get('seconds', 1)
            await asyncio.sleep(seconds)
            return f"Waited {seconds} seconds"
        elif action == 'screenshot':
            filename = step.get('filename', f"screenshot_{int(asyncio.get_event_loop().time())}.png")
            os.makedirs(settings.SCREENSHOT_DIR, exist_ok=True)
            await page.screenshot(path=f"{settings.SCREENSHOT_DIR}/{filename}")
            return f"Screenshot saved: {filename}"
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _intelligent_click(self, page: Page, step: Dict[str, Any], context: str) -> str:
        """Intelligently find and click an element with self-correction."""
        description = step['description']
        original_description = description  # Keep original for logging
        max_attempts = settings.MAX_CORRECTION_ATTEMPTS + 1 if settings.ENABLE_SELF_CORRECTION else 1
        
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                # Try to find element
                find_result = await self.element_finder.find_element_intelligently(
                    page, description, context
                )
                
                if not find_result['success']:
                    last_error = find_result.get('error', 'Element not found')
                    
                    # Try correction if not last attempt
                    if attempt < max_attempts - 1:
                        logger.warning(f"❌ Attempt {attempt + 1}/{max_attempts} failed: {last_error}")
                        corrected_desc = await self._ask_for_correction(page, description, last_error)
                        
                        if corrected_desc:
                            description = corrected_desc
                            continue  # Retry with corrected description
                        else:
                            logger.info("No correction available, proceeding to next attempt...")
                    
                    # No correction or last attempt
                    raise Exception(f"Could not find element: {original_description}")
                
                selector = find_result['selector']
                
                # Try to click
                try:
                    # 1. Scroll into view
                    locator = page.locator(selector).first
                    await locator.scroll_into_view_if_needed(timeout=5000)
                    
                    # 2. Scroll back up slightly (avoid sticky headers)
                    await page.evaluate("window.scrollBy(0, -100)")
                    await asyncio.sleep(0.5)
                    
                    # 3. Click
                    await locator.click(timeout=10000)
                    
                    success_msg = f"✓ Clicked '{original_description}'"
                    if description != original_description:
                        success_msg += f" (corrected to: '{description}')"
                    return success_msg
                    
                except Exception as click_error:
                    # Try force click as fallback
                    try:
                        await page.locator(selector).first.click(force=True, timeout=5000)
                        return f"✓ Force-clicked '{original_description}'"
                    except:
                        raise Exception(f"Failed to click '{description}': {str(click_error)}")
                
            except Exception as e:
                last_error = str(e)
                if attempt < max_attempts - 1:
                    logger.warning(f"Click attempt {attempt + 1}/{max_attempts} failed: {last_error}")
                    logger.info("Retrying with correction...")
                    # Try to get correction for next attempt
                    corrected_desc = await self._ask_for_correction(page, description, last_error)
                    if corrected_desc:
                        description = corrected_desc
                    continue
                else:
                    # Last attempt failed
                    raise
        
        # Should not reach here, but just in case
        raise Exception(f"Failed after {max_attempts} attempts: {last_error}")
    
    async def _intelligent_type(self, page: Page, step: Dict[str, Any], context: str) -> str:
        """Intelligently find and type into an element with self-correction."""
        description = step['description']
        text = step['text']
        original_description = description
        max_attempts = settings.MAX_CORRECTION_ATTEMPTS + 1 if settings.ENABLE_SELF_CORRECTION else 1
        
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                find_result = await self.element_finder.find_element_intelligently(
                    page, description, context
                )
                
                if not find_result['success']:
                    last_error = find_result.get('error', 'Element not found')
                    
                    if attempt < max_attempts - 1:
                        logger.warning(f"❌ Attempt {attempt + 1}/{max_attempts} failed: {last_error}")
                        corrected_desc = await self._ask_for_correction(page, description, last_error)
                        
                        if corrected_desc:
                            description = corrected_desc
                            continue
                    
                    raise Exception(f"Could not find input: {original_description}")
                
                selector = find_result['selector']
                
                await page.locator(selector).scroll_into_view_if_needed(timeout=5000)
                await page.wait_for_timeout(500)
                await page.fill(selector, text, timeout=10000)
                
                success_msg = f"✓ Typed '{text}' into '{original_description}'"
                if description != original_description:
                    success_msg += f" (corrected to: '{description}')"
                return success_msg
                
            except Exception as e:
                last_error = str(e)
                if attempt < max_attempts - 1:
                    logger.warning(f"Type attempt {attempt + 1}/{max_attempts} failed: {last_error}")
                    corrected_desc = await self._ask_for_correction(page, description, last_error)
                    if corrected_desc:
                        description = corrected_desc
                    continue
                else:
                    raise Exception(f"Failed to type into '{original_description}': {str(e)}")
        
        raise Exception(f"Failed after {max_attempts} attempts: {last_error}")
    
    async def _intelligent_extract(self, page: Page, step: Dict[str, Any], context: str) -> str:
        """Intelligently extract data from elements."""
        description = step['description']
        data_type = step.get('data_type', 'text')
        
        find_result = await self.element_finder.find_element_intelligently(
            page, description, context
        )
        
        if not find_result['success']:
            return f"Could not find element for extraction: {description}"
        
        selector = find_result['selector']
        
        try:
            if data_type == 'text':
                data = await page.text_content(selector, timeout=5000)
            elif data_type == 'html':
                data = await page.inner_html(selector, timeout=5000)
            elif data_type == 'value':
                data = await page.input_value(selector, timeout=5000)
            else:
                data = await page.text_content(selector, timeout=5000)
            
            return f"Extracted from '{description}': {str(data)[:200]}"
            
        except Exception as e:
            return f"Failed to extract from '{description}': {str(e)}"
    
    async def _intelligent_wait(self, page: Page, step: Dict[str, Any], context: str) -> str:
        """Intelligently wait for conditions."""
        condition = step.get('condition', 'time')
        
        if condition == 'element':
            description = step['description']
            timeout = step.get('timeout', 30000)
            
            find_result = await self.element_finder.find_element_intelligently(
                page, description, context
            )
            
            if find_result['success']:
                selector = find_result['selector']
                try:
                    await page.wait_for_selector(selector, timeout=timeout)
                    return f"Successfully waited for element: {description}"
                except:
                    return f"Timeout waiting for element: {description}"
            else:
                return f"Could not identify element to wait for: {description}"
        else:
            seconds = step.get('seconds', 1)
            await asyncio.sleep(seconds)
            return f"Waited {seconds} seconds"