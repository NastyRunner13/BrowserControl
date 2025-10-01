import asyncio
import os
from typing import Dict, Any
from playwright.async_api import Page
from core.browser_pool import BrowserPool
from core.element_finder import IntelligentElementFinder
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)

class IntelligentParallelExecutor:
    """Enhanced parallel executor with AI-powered step execution."""
    
    def __init__(self, browser_pool: BrowserPool):
        self.browser_pool = browser_pool
        self.element_finder = IntelligentElementFinder()
        
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
        """Intelligently find and click an element."""
        description = step['description']
        
        find_result = await self.element_finder.find_element_intelligently(
            page, description, context
        )
        
        if not find_result['success']:
            raise Exception(f"Could not find element: {description}")
        
        selector = find_result['selector']
        
        try:
            await page.locator(selector).scroll_into_view_if_needed(timeout=5000)
            await page.wait_for_timeout(500)
            await page.click(selector, timeout=10000)
            await page.wait_for_timeout(1000)
            
            return f"Clicked '{description}' using {selector}"
            
        except Exception as e:
            try:
                await page.locator(selector).click(force=True, timeout=5000)
                return f"Force-clicked '{description}'"
            except:
                raise Exception(f"Failed to click '{description}': {str(e)}")
    
    async def _intelligent_type(self, page: Page, step: Dict[str, Any], context: str) -> str:
        """Intelligently find and type into an element."""
        description = step['description']
        text = step['text']
        
        find_result = await self.element_finder.find_element_intelligently(
            page, description, context
        )
        
        if not find_result['success']:
            raise Exception(f"Could not find input: {description}")
        
        selector = find_result['selector']
        
        try:
            await page.locator(selector).scroll_into_view_if_needed(timeout=5000)
            await page.wait_for_timeout(500)
            await page.fill(selector, text, timeout=10000)
            
            return f"Typed '{text}' into '{description}'"
            
        except Exception as e:
            raise Exception(f"Failed to type into '{description}': {str(e)}")
    
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