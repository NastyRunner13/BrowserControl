import asyncio
import os
from typing import Dict, Any, Optional, TYPE_CHECKING
from playwright.async_api import Page
from core.browser_pool import BrowserPool
from core.element_finder import IntelligentElementFinder
from core.overlay_detector import OverlayDetector
from utils.logger import setup_logger
from config.settings import settings

if TYPE_CHECKING:
    from core.tab_manager import TabManager
    from core.task_context import TaskContext

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
    
    async def execute_intelligent_step(
        self, 
        page: Page, 
        step: Dict[str, Any], 
        task_context: str = "",
        context_obj: Optional['TaskContext'] = None,
        tab_manager: Optional['TabManager'] = None
    ) -> str:
        """
        Execute a step with intelligent reasoning capabilities.
        
        Args:
            page: Playwright page object
            step: Step definition with action and parameters
            task_context: String context for element finding
            context_obj: Optional TaskContext for storing extracted data
            tab_manager: Optional TabManager for multi-tab operations
        """
        action = step['action']
        
        if action == 'intelligent_click':
            return await self._intelligent_click(page, step, task_context)
        elif action == 'intelligent_type':
            return await self._intelligent_type(page, step, task_context)
        elif action == 'intelligent_extract':
            return await self._intelligent_extract(page, step, task_context, context_obj)
        elif action == 'intelligent_wait':
            return await self._intelligent_wait(page, step, task_context)
        elif action == 'navigate':
            await page.goto(step['url'], wait_until='domcontentloaded', timeout=settings.BROWSER_TIMEOUT)
            # Wait for JS-heavy SPAs to finish loading
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                await asyncio.sleep(1)  # Fallback: just wait a second
            if context_obj:
                context_obj.add_visited_url(step['url'])
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
        elif action == 'scroll':
            direction = step.get('direction', 'down')
            amount = step.get('amount', 500)
            if direction == 'down':
                await page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == 'up':
                await page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == 'left':
                await page.evaluate(f"window.scrollBy(-{amount}, 0)")
            elif direction == 'right':
                await page.evaluate(f"window.scrollBy({amount}, 0)")
            return f"Scrolled {direction} by {amount} pixels"
        elif action == 'final_answer':
            answer = step.get('answer', 'Goal completed.')
            print(f"\n✅ FINAL ANSWER: {answer}\n")
            if context_obj:
                context_obj.set_final_answer(answer)
            return f"COMPLETED: {answer}"
        elif action == 'screenshot':
            filename = step.get('filename', f"screenshot_{int(asyncio.get_event_loop().time())}.png")
            os.makedirs(settings.SCREENSHOT_DIR, exist_ok=True)
            filepath = f"{settings.SCREENSHOT_DIR}/{filename}"
            await page.screenshot(path=filepath)
            if context_obj:
                context_obj.add_screenshot(filepath)
            return f"Screenshot saved: {filename}"
        # Hover action
        elif action == 'hover':
            return await self._intelligent_hover(page, step, task_context)
        # Select option action
        elif action == 'select_option':
            return await self._intelligent_select(page, step, task_context)
        # Tab management actions
        elif action == 'new_tab':
            if not tab_manager:
                return "Error: Tab manager not available"
            url = step.get('url')
            result = await tab_manager.new_tab(url)
            if result['success']:
                return f"Created new tab {result['tab_index']}" + (f" at {url}" if url else "")
            return f"Failed to create new tab: {result.get('error', 'Unknown error')}"
        elif action == 'switch_tab':
            if not tab_manager:
                return "Error: Tab manager not available"
            tab_index = step.get('tab_index', 0)
            result = await tab_manager.switch_tab(tab_index)
            if result['success']:
                return f"Switched to tab {tab_index}: {result.get('title', 'Unknown')}"
            return f"Failed to switch tab: {result.get('error', 'Unknown error')}"
        elif action == 'close_tab':
            if not tab_manager:
                return "Error: Tab manager not available"
            tab_index = step.get('tab_index')
            result = await tab_manager.close_tab(tab_index)
            if result['success']:
                return f"Closed tab {result['closed_tab']}, now on tab {result['active_tab']}"
            return f"Failed to close tab: {result.get('error', 'Unknown error')}"
        elif action == 'list_tabs':
            if not tab_manager:
                return "Error: Tab manager not available"
            result = await tab_manager.list_tabs()
            tabs_str = ", ".join([f"[{t['index']}]{' (active)' if t['is_active'] else ''}: {t.get('title', 'Unknown')[:30]}" for t in result['tabs']])
            return f"Open tabs ({result['total_tabs']}): {tabs_str}"
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _intelligent_click(self, page: Page, step: Dict[str, Any], context: str) -> str:
        """Intelligently find and click an element with overlay handling and self-correction."""
        description = step['description']
        original_description = description
        max_attempts = settings.MAX_CORRECTION_ATTEMPTS + 1 if settings.ENABLE_SELF_CORRECTION else 1
        
        overlay_detector = OverlayDetector(page)
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                # Try to find element
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
                        else:
                            logger.info("No correction available, proceeding to next attempt...")
                    
                    raise Exception(f"Could not find element: {original_description}")
                
                selector = find_result['selector']
                locator = page.locator(selector).first
                
                # Try to click with overlay handling
                click_success = False
                
                for click_attempt in range(3):  # Up to 3 click attempts
                    try:
                        # 1. Scroll into view
                        await locator.scroll_into_view_if_needed(timeout=5000)
                        await page.evaluate("window.scrollBy(0, -100)")
                        await asyncio.sleep(0.3)
                        
                        # 2. Try normal click
                        await locator.click(timeout=5000)
                        click_success = True
                        break
                        
                    except Exception as click_error:
                        error_msg = str(click_error).lower()
                        
                        # Check if blocked by overlay
                        if 'intercepts pointer' in error_msg or 'element is not clickable' in error_msg:
                            logger.info(f"Click blocked by overlay, attempting to dismiss...")
                            
                            # Try to dismiss overlays
                            dismissed = await overlay_detector.dismiss_overlays()
                            if dismissed > 0:
                                logger.info(f"Dismissed {dismissed} overlays, retrying click...")
                                await asyncio.sleep(0.5)
                                continue
                            
                            # Try force click
                            try:
                                await locator.click(force=True, timeout=3000)
                                click_success = True
                                break
                            except:
                                pass
                            
                            # Try coordinate-based click as final fallback
                            try:
                                box = await locator.bounding_box()
                                if box:
                                    center_x = box['x'] + box['width'] / 2
                                    center_y = box['y'] + box['height'] / 2
                                    await page.mouse.click(center_x, center_y)
                                    logger.info(f"Clicked at coordinates ({center_x}, {center_y})")
                                    click_success = True
                                    break
                            except Exception as coord_error:
                                logger.debug(f"Coordinate click failed: {coord_error}")
                        
                        # Last click attempt failed
                        if click_attempt == 2:
                            raise Exception(f"Failed to click after overlay handling: {click_error}")
                
                if click_success:
                    # Wait for page to stabilize after click (handles SPA transitions)
                    try:
                        await page.wait_for_load_state('domcontentloaded', timeout=5000)
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)
                    
                    success_msg = f"✓ Clicked '{original_description}'"
                    if description != original_description:
                        success_msg += f" (corrected to: '{description}')"
                    return success_msg
                    
            except Exception as e:
                last_error = str(e)
                if attempt < max_attempts - 1:
                    logger.warning(f"Click attempt {attempt + 1}/{max_attempts} failed: {last_error}")
                    corrected_desc = await self._ask_for_correction(page, description, last_error)
                    if corrected_desc:
                        description = corrected_desc
                    continue
                else:
                    raise
        
        raise Exception(f"Failed after {max_attempts} attempts: {last_error}")
    
    async def _intelligent_type(self, page: Page, step: Dict[str, Any], context: str) -> str:
        """Intelligently find and type into an element with self-correction."""
        description = step['description']
        text = step['text']
        press_enter = step.get('press_enter', False)
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
                
                # Handle strict mode: if selector matches multiple elements, narrow it down
                locator = page.locator(selector)
                element_count = await locator.count()
                
                if element_count > 1:
                    # For input fields, try excluding readonly/disabled elements  
                    narrowed = page.locator(f"{selector}:not([readonly]):not([disabled])")
                    narrowed_count = await narrowed.count()
                    if narrowed_count >= 1:
                        locator = narrowed.first
                    else:
                        locator = locator.first
                    logger.info(f"Selector '{selector}' matched {element_count} elements, narrowed to first non-readonly")
                
                await locator.scroll_into_view_if_needed(timeout=5000)
                await page.wait_for_timeout(500)
                await locator.fill(text, timeout=10000)
                
                result_msg = f"✓ Typed '{text}' into '{description}'"
                        
                if press_enter:
                    await page.keyboard.press("Enter")
                    result_msg += " and pressed Enter"
                    
                return result_msg
                
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
    
    async def _intelligent_extract(
        self, 
        page: Page, 
        step: Dict[str, Any], 
        context: str,
        context_obj: Optional['TaskContext'] = None
    ) -> str:
        """Intelligently extract data from elements and store in context.
        
        Supports both single-element and multi-element extraction.
        For multi-element requests (e.g., 'product prices', 'first 3 results'),
        uses page-level JS extraction as fallback.
        """
        description = step['description']
        data_type = step.get('data_type', 'text')
        store_as = step.get('store_as', description)
        
        # Detect multi-element intent
        multi_keywords = ['prices', 'results', 'items', 'products', 'listings', 
                         'titles', 'names', 'links', 'options', 'all', 'list',
                         'first', 'top', 'multiple']
        is_multi = any(kw in description.lower() for kw in multi_keywords)
        
        # TIER 1: Try standard single-element finder
        find_result = await self.element_finder.find_element_intelligently(
            page, description, context
        )
        
        if find_result['success']:
            selector = find_result['selector']
            try:
                if is_multi:
                    # Try to get multiple matching elements
                    data = await page.evaluate(f"""
                        (selector) => {{
                            const elements = document.querySelectorAll(selector);
                            if (elements.length > 1) {{
                                return Array.from(elements)
                                    .slice(0, 10)
                                    .map((el, i) => `${{i+1}}. ${{el.textContent.trim().substring(0, 150)}}`)
                                    .join('; ');
                            }}
                            // Single element - get its text
                            return elements[0]?.textContent?.trim() || '';
                        }}
                    """, selector)
                elif data_type == 'text':
                    data = await page.text_content(selector, timeout=5000)
                elif data_type == 'html':
                    data = await page.inner_html(selector, timeout=5000)
                elif data_type == 'value':
                    data = await page.input_value(selector, timeout=5000)
                else:
                    data = await page.text_content(selector, timeout=5000)
                
                if context_obj and data:
                    context_obj.store_extracted_data(store_as, data)
                
                return f"Extracted from '{description}': {str(data)[:500]}"
                
            except Exception as e:
                logger.warning(f"Standard extraction failed: {e}, trying page-level fallback")
        
        # TIER 2: Page-level JS extraction fallback for multi-element requests
        if is_multi:
            try:
                data = await page.evaluate("""
                    (description) => {
                        const desc = description.toLowerCase();
                        let results = [];
                        
                        // Try to find price elements
                        if (desc.includes('price')) {
                            const priceSelectors = [
                                '[class*="price"]', '[data-price]', '[itemprop="price"]',
                                '[class*="Price"]', '[class*="cost"]', '[class*="amount"]'
                            ];
                            for (const sel of priceSelectors) {
                                const els = document.querySelectorAll(sel);
                                if (els.length > 0) {
                                    results = Array.from(els)
                                        .slice(0, 10)
                                        .map(el => el.textContent.trim())
                                        .filter(t => t && t.length < 100);
                                    if (results.length > 0) break;
                                }
                            }
                        }
                        
                        // Try to find product/title elements
                        if (results.length === 0 && (desc.includes('title') || desc.includes('product') || desc.includes('name'))) {
                            const titleSelectors = [
                                '[class*="title"]', '[class*="product-name"]', '[class*="productName"]',
                                'h2 a', 'h3 a', '[itemprop="name"]'
                            ];
                            for (const sel of titleSelectors) {
                                const els = document.querySelectorAll(sel);
                                if (els.length > 0) {
                                    results = Array.from(els)
                                        .slice(0, 10)
                                        .map(el => el.textContent.trim())
                                        .filter(t => t && t.length > 3 && t.length < 200);
                                    if (results.length > 0) break;
                                }
                            }
                        }
                        
                        // Generic: try main content area
                        if (results.length === 0) {
                            const mainContent = document.querySelector('main, [role="main"], #content, .content');
                            if (mainContent) {
                                return mainContent.innerText.substring(0, 1000);
                            }
                            return document.body.innerText.substring(0, 800);
                        }
                        
                        return results.map((r, i) => `${i+1}. ${r}`).join('; ');
                    }
                """, description)
                
                if data and context_obj:
                    context_obj.store_extracted_data(store_as, data)
                
                return f"Extracted from '{description}': {str(data)[:500]}"
                
            except Exception as e:
                return f"Failed to extract '{description}': {str(e)}"
        
        return f"Could not find element for extraction: {description}"
    
    async def _intelligent_hover(self, page: Page, step: Dict[str, Any], context: str) -> str:
        """Intelligently find and hover over an element."""
        description = step['description']
        
        find_result = await self.element_finder.find_element_intelligently(
            page, description, context
        )
        
        if not find_result['success']:
            return f"Could not find element to hover: {description}"
        
        selector = find_result['selector']
        
        try:
            locator = page.locator(selector).first
            await locator.scroll_into_view_if_needed(timeout=5000)
            await locator.hover(timeout=5000)
            return f"✓ Hovered over '{description}'"
            
        except Exception as e:
            return f"Failed to hover over '{description}': {str(e)}"
    
    async def _intelligent_select(self, page: Page, step: Dict[str, Any], context: str) -> str:
        """Intelligently select an option from a dropdown."""
        description = step['description']
        value = step.get('value', '')
        by = step.get('by', 'value')  # 'value', 'label', or 'index'
        
        find_result = await self.element_finder.find_element_intelligently(
            page, description, context
        )
        
        if not find_result['success']:
            return f"Could not find dropdown: {description}"
        
        selector = find_result['selector']
        
        try:
            locator = page.locator(selector).first
            await locator.scroll_into_view_if_needed(timeout=5000)
            
            if by == 'value':
                await locator.select_option(value=value, timeout=5000)
            elif by == 'label':
                await locator.select_option(label=value, timeout=5000)
            elif by == 'index':
                await locator.select_option(index=int(value), timeout=5000)
            else:
                await locator.select_option(value=value, timeout=5000)
            
            return f"✓ Selected '{value}' in dropdown '{description}'"
            
        except Exception as e:
            return f"Failed to select in '{description}': {str(e)}"
    
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