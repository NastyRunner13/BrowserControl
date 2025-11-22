import base64
import difflib
from typing import Dict, List, Any, Optional
from playwright.async_api import Page
from langchain_groq import ChatGroq
from pydantic import SecretStr
from utils.logger import setup_logger
from utils.helpers import extract_number
from config.settings import settings

logger = setup_logger(__name__)

class IntelligentElementFinder:
    """
    Advanced element finding with Vision AI (Set-of-Marks) and fallback strategies.
    
    Now implements a 3-tier approach:
    1. DOM-based AI matching (fast, existing approach)
    2. Vision AI with visual markers (most reliable, fallback)
    3. Rule-based fallback (last resort)
    
    Backward compatible with existing code - same interface as before,
    but with enhanced capabilities when vision is enabled.
    """
    
    def __init__(self, llm=None):
        api_key = settings.GROQ_API_KEY
        if api_key is None:
            raise ValueError("GROQ_API_KEY is not set")
        
        # Main LLM for text-based reasoning
        self.llm = llm or ChatGroq(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=SecretStr(api_key) if isinstance(api_key, str) else api_key
        )
        
        # Vision model for multimodal tasks (only if enabled)
        self.vision_llm = None
        if settings.VISION_ENABLED or settings.ENABLE_VISION_FALLBACK:
            try:
                self.vision_llm = ChatGroq(
                    model=settings.VISION_MODEL,
                    temperature=0.1,
                    api_key=SecretStr(api_key) if isinstance(api_key, str) else api_key
                )
                logger.info("Vision model initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize vision model: {e}")
                logger.warning("Vision features will be disabled")
        
        self._vision_cache = {}
    
    async def find_element_intelligently(
        self, 
        page: Page, 
        description: str,
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Find element using multi-tier strategy with vision fallback.
        
        Args:
            page: Playwright page object
            description: Natural language description of element
            context: Additional context about the task
            
        Returns:
            Dictionary with success status, element data, and selector
        """
        try:
            # Get all interactive elements first
            all_elements = await self._get_interactive_elements(page)
            
            if not all_elements:
                logger.warning("No interactive elements found on page")
                return {"success": False, "error": "No interactive elements found"}
            
            logger.info(f"Found {len(all_elements)} total interactive elements")
            
            # === TIER 1: DOM-BASED AI MATCHING (Fast) ===
            logger.debug("Attempting DOM-based element finding...")
            
            # Try viewport elements first
            viewport_elements = self._filter_by_viewport(all_elements)
            if viewport_elements:
                match_result = await self._ai_powered_element_matching(
                    description, viewport_elements, context, strategy="viewport"
                )
                if match_result['success']:
                    logger.info("✓ Found element using DOM-based viewport strategy")
                    return match_result
            
            # Try relevance-filtered elements
            relevant_elements = self._filter_by_relevance(all_elements, description)
            if relevant_elements:
                match_result = await self._ai_powered_element_matching(
                    description, relevant_elements, context, strategy="relevance"
                )
                if match_result['success']:
                    logger.info("✓ Found element using DOM-based relevance strategy")
                    return match_result
            
            # === TIER 2: VISION AI FALLBACK (If enabled) ===
            if settings.ENABLE_VISION_FALLBACK and self.vision_llm:
                logger.info("DOM-based finding failed, trying Vision AI fallback...")
                vision_result = await self._find_with_vision(page, description, context)
                
                if vision_result['success']:
                    logger.info(f"✓ Found element using Vision AI")
                    return vision_result
                else:
                    logger.warning(f"Vision AI also failed: {vision_result.get('error', 'Unknown')}")
            
            # === TIER 3: RULE-BASED FALLBACK ===
            logger.info("Falling back to rule-based matching...")
            return await self._fallback_element_matching(description, all_elements)
            
        except Exception as e:
            logger.error(f"All element finding strategies failed: {e}")
            return {"success": False, "error": str(e)}
    
    # ========================================
    # VISION AI METHODS (NEW)
    # ========================================
    
    async def _find_with_vision(
        self, 
        page: Page, 
        description: str, 
        context: str
    ) -> Dict[str, Any]:
        """
        Use Vision AI with Set-of-Marks to find elements.
        
        Process:
        1. Inject numbered red boxes over interactive elements
        2. Take screenshot with markers
        3. Send to vision LLM with description
        4. Parse response to get element ID
        """
        try:
            # Inject visual markers and get element map
            logger.debug("Injecting visual markers...")
            element_map = await self._inject_visual_markers(page)
            
            if not element_map:
                return {"success": False, "error": "No markable elements found"}
            
            logger.info(f"Marked {len(element_map)} elements for vision analysis")
            
            # Take screenshot with markers visible
            screenshot_bytes = await page.screenshot(full_page=False)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            # Build vision prompt
            vision_prompt = f"""You are analyzing a webpage screenshot with numbered RED BOXES over interactive elements.

USER WANTS TO: "{description}"
{f"CONTEXT: {context}" if context else ""}

The red numbers correspond to these elements:
{self._format_element_map(element_map)}

TASK: Which numbered element best matches what the user wants to interact with?

Respond with ONLY the number (e.g., "5") or -1 if no good match exists."""

            if not self.vision_llm:
                return {"success": False, "error": "Vision model not available"}
            
            # Send to vision model
            message_content = [
                {"type": "text", "text": vision_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}
                }
            ]

            response = await self.vision_llm.ainvoke([{
                "role": "user",
                "content": message_content
            }])
            
            # Parse response
            response_text = response.content if isinstance(response.content, str) else str(response.content)
            element_id = extract_number(response_text)
            
            # Clean up markers
            await self._remove_visual_markers(page)
            
            if element_id is not None and element_id in element_map:
                selected = element_map[element_id]
                logger.info(f"Vision AI selected element {element_id}")
                
                return {
                    "success": True,
                    "element": selected,
                    "selector": selected['selector'],
                    "confidence": "high",
                    "reasoning": f"Vision AI identified element {element_id}",
                    "method": "vision_ai"
                }
            
            return {"success": False, "error": f"Vision AI returned invalid ID: {element_id}"}
            
        except Exception as e:
            logger.error(f"Vision-based finding failed: {e}")
            # Clean up markers in case of error
            try:
                await self._remove_visual_markers(page)
            except:
                pass
            return {"success": False, "error": f"Vision AI error: {str(e)}"}
    
    async def _inject_visual_markers(self, page: Page) -> Dict[int, Dict[str, Any]]:
        """Inject numbered visual markers over interactive elements."""
        element_map = await page.evaluate("""
            () => {
                const map = {};
                const selectors = [
                    'button', 'a[href]', 'input', 'textarea', 'select',
                    '[role="button"]', '[onclick]', '[tabindex]'
                ];
                
                const elements = new Set();
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => elements.add(el));
                });
                
                let index = 0;
                elements.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    const isVisible = rect.width > 0 && rect.height > 0 &&
                                    window.getComputedStyle(el).visibility !== 'hidden';
                    
                    // Only mark elements in viewport
                    if (isVisible && rect.top < window.innerHeight && rect.left < window.innerWidth) {
                        // Create marker overlay
                        const marker = document.createElement('div');
                        marker.className = 'som-marker';
                        marker.style.cssText = `
                            position: fixed;
                            left: ${rect.left}px;
                            top: ${rect.top}px;
                            width: ${rect.width}px;
                            height: ${rect.height}px;
                            background: rgba(255, 0, 0, 0.3);
                            border: 2px solid red;
                            color: white;
                            font-weight: bold;
                            font-size: 16px;
                            z-index: 999999;
                            pointer-events: none;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                        `;
                        marker.textContent = index;
                        document.body.appendChild(marker);
                        
                        // Generate selector
                        let selector = '';
                        if (el.id) {
                            selector = `#${el.id}`;
                        } else if (el.name) {
                            selector = `[name="${el.name}"]`;
                        } else {
                            const tagName = el.tagName.toLowerCase();
                            const siblings = Array.from(el.parentNode?.children || [])
                                .filter(sib => sib.tagName === el.tagName);
                            const position = siblings.indexOf(el) + 1;
                            selector = `${tagName}:nth-child(${position})`;
                        }
                        
                        // Store element data
                        map[index] = {
                            tagName: el.tagName.toLowerCase(),
                            text: el.textContent?.trim().substring(0, 50) || '',
                            type: el.type || '',
                            placeholder: el.placeholder || '',
                            ariaLabel: el.getAttribute('aria-label') || '',
                            id: el.id || '',
                            selector: selector
                        };
                        
                        index++;
                    }
                });
                
                return map;
            }
        """)
        
        return element_map
    
    async def _remove_visual_markers(self, page: Page):
        """Remove injected visual markers."""
        await page.evaluate("() => { document.querySelectorAll('.som-marker').forEach(el => el.remove()); }")
    
    def _format_element_map(self, element_map: Dict[int, Dict]) -> str:
        """Format element map for vision prompt."""
        lines = []
        max_elements = min(len(element_map), settings.VISION_MAX_MARKERS)
        
        for idx in sorted(element_map.keys())[:max_elements]:
            elem = element_map[idx]
            desc = f"[{idx}] {elem['tagName'].upper()}"
            if elem['text']:
                desc += f" '{elem['text'][:30]}'"
            elif elem['placeholder']:
                desc += f" (placeholder: '{elem['placeholder']}')"
            elif elem['ariaLabel']:
                desc += f" (aria: '{elem['ariaLabel']}')"
            lines.append(desc)
        
        return "\n".join(lines)
    
    # ========================================
    # DOM-BASED METHODS (EXISTING)
    # ========================================
    
    async def _get_interactive_elements(self, page: Page) -> List[Dict]:
        """Extract and analyze interactive elements from the page."""
        elements_data = await page.evaluate("""
            () => {
                const elements = [];
                const selectors = [
                    'a[href]', 'button', 'input', 'textarea', 'select', 
                    '[role="button"]', '[onclick]', '[tabindex]', 'form',
                    '[class*="button"]', '[class*="btn"]', '[class*="search"]',
                    '[class*="submit"]', '[class*="login"]', '[class*="sign"]',
                    '[type="submit"]', '[type="button"]', 'label'
                ];
                
                const seenElements = new Set();
                
                selectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach((el) => {
                        const rect = el.getBoundingClientRect();
                        const isVisible = rect.width > 0 && rect.height > 0 && 
                                        window.getComputedStyle(el).visibility !== 'hidden' &&
                                        window.getComputedStyle(el).display !== 'none';
                        
                        if (isVisible) {
                            const elementKey = el.outerHTML;
                            if (!seenElements.has(elementKey)) {
                                seenElements.add(elementKey);
                                
                                const text = el.textContent || el.innerText || '';
                                const cleanText = text.trim().replace(/\\s+/g, ' ');
                                
                                function generateBestSelector(element) {
                                    if (element.id) return `#${element.id}`;
                                    if (element.name) return `[name="${element.name}"]`;
                                    
                                    const ariaLabel = element.getAttribute('aria-label');
                                    if (ariaLabel) return `[aria-label="${ariaLabel}"]`;
                                    
                                    const tagName = element.tagName.toLowerCase();
                                    const parent = element.parentNode;
                                    if (parent) {
                                        const siblings = Array.from(parent.children)
                                            .filter(sib => sib.tagName === element.tagName);
                                        const index = siblings.indexOf(element) + 1;
                                        return `${tagName}:nth-child(${index})`;
                                    }
                                    return tagName;
                                }
                                
                                elements.push({
                                    tagName: el.tagName.toLowerCase(),
                                    text: cleanText.substring(0, 100),
                                    type: el.type || '',
                                    placeholder: el.placeholder || '',
                                    value: el.value || '',
                                    id: el.id || '',
                                    className: el.className || '',
                                    ariaLabel: el.getAttribute('aria-label') || '',
                                    title: el.title || '',
                                    name: el.name || '',
                                    href: el.href || '',
                                    selector: generateBestSelector(el),
                                    position: {
                                        x: Math.round(rect.x),
                                        y: Math.round(rect.y),
                                        width: Math.round(rect.width),
                                        height: Math.round(rect.height)
                                    }
                                });
                            }
                        }
                    });
                });
                
                return elements.sort((a, b) => {
                    if (Math.abs(a.position.y - b.position.y) > 50) {
                        return a.position.y - b.position.y;
                    }
                    return a.position.x - b.position.x;
                });
            }
        """)
        
        return elements_data
    
    def _filter_by_viewport(self, elements: List[Dict]) -> List[Dict]:
        """Filter elements that are currently visible in the viewport."""
        viewport_elements = []
        for elem in elements:
            pos = elem.get('position', {})
            y = pos.get('y', 0)
            height = pos.get('height', 0)
            if y >= 0 and y < 1500 and height > 0:
                viewport_elements.append(elem)
        return viewport_elements
    
    def _filter_by_relevance(self, elements: List[Dict], description: str) -> List[Dict]:
        """Smart pre-filter elements based on description relevance."""
        description_lower = description.lower()
        description_words = set(description_lower.split())
        
        action_keywords = {'button', 'link', 'input', 'field', 'box', 'dropdown', 'select', 'menu'}
        position_keywords = {'top', 'bottom', 'left', 'right', 'main', 'sidebar', 'header', 'footer'}
        
        action_hints = action_keywords & description_words
        position_hints = position_keywords & description_words
        
        scored_elements = []
        
        for elem in elements:
            relevance_score = 0
            
            # Score based on text content
            text = elem.get('text', '').lower()
            if text:
                if description_lower in text:
                    relevance_score += 50
                text_words = set(text.split())
                overlap = len(description_words & text_words)
                relevance_score += overlap * 10
            
            # Score based on placeholder/aria-label
            placeholder = elem.get('placeholder', '').lower()
            aria_label = elem.get('ariaLabel', '').lower()
            
            if description_lower in placeholder:
                relevance_score += 40
            if description_lower in aria_label:
                relevance_score += 40
            
            # Score based on element type
            tag_name = elem.get('tagName', '')
            if action_hints:
                if 'button' in action_hints and tag_name == 'button':
                    relevance_score += 20
                if 'link' in action_hints and tag_name == 'a':
                    relevance_score += 20
                if 'input' in action_hints and tag_name == 'input':
                    relevance_score += 20
            
            # Score based on position
            y_pos = elem.get('position', {}).get('y', 0)
            if position_hints:
                if 'top' in position_hints and y_pos < 200:
                    relevance_score += 15
                if 'bottom' in position_hints and y_pos > 600:
                    relevance_score += 15
            
            if relevance_score > 0:
                scored_elements.append((relevance_score, elem))
        
        if not scored_elements:
            return elements[:150]
        
        scored_elements.sort(key=lambda x: x[0], reverse=True)
        return [elem for score, elem in scored_elements[:150]]
    
    async def _ai_powered_element_matching(
        self, 
        description: str, 
        elements: List[Dict],
        context: str = "",
        strategy: str = "viewport"
    ) -> Dict[str, Any]:
        """Use AI to intelligently match description to page elements."""
        elements_to_analyze = elements[:100]
        
        element_summaries = []
        for i, elem in enumerate(elements_to_analyze):
            summary = f"[{i}] {elem['tagName'].upper()}"
            
            if elem['text']:
                summary += f" '{elem['text'][:40]}'"
            elif elem['placeholder']:
                summary += f" (placeholder: '{elem['placeholder']}')"
            elif elem['ariaLabel']:
                summary += f" (aria-label: '{elem['ariaLabel']}')"
            elif elem['title']:
                summary += f" (title: '{elem['title']}')"
            
            if elem['type']:
                summary += f" [{elem['type']}]"
            
            y_pos = elem['position']['y']
            if y_pos < 150:
                summary += " (top)"
            elif y_pos > 600:
                summary += " (bottom)"
            
            element_summaries.append(summary)
        
        prompt = f"""Find the best matching element for the user's description.

USER REQUEST: "{description}"
{f"CONTEXT: {context}" if context else ""}
SEARCH STRATEGY: {strategy}
TOTAL ELEMENTS SCANNED: {len(elements)}

ELEMENTS TO CONSIDER:
{chr(10).join(element_summaries)}

Respond with ONLY the number (0-{len(element_summaries)-1}) of the best match, or -1 if no good match."""

        try:
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            
            # Handle response content
            if isinstance(response.content, str):
                response_text = response.content.strip()
            elif isinstance(response.content, list):
                response_text = ""
                for item in response.content:
                    if isinstance(item, dict) and "text" in item:
                        response_text += item["text"]
                    elif isinstance(item, str):
                        response_text += item
                response_text = response_text.strip()
            else:
                response_text = str(response.content).strip()
            
            index = extract_number(response_text)
            
            if index is not None and 0 <= index < len(elements_to_analyze):
                selected_element = elements_to_analyze[index]
                logger.info(f"AI selected element {index} from {len(elements_to_analyze)} candidates")
                return {
                    "success": True,
                    "element": selected_element,
                    "selector": selected_element['selector'],
                    "confidence": "high",
                    "reasoning": f"AI selected element {index} using {strategy} strategy",
                    "total_scanned": len(elements)
                }
            
            logger.warning(f"AI returned invalid index: {index}")
            return await self._fallback_element_matching(description, elements)
            
        except Exception as e:
            logger.error(f"AI element matching failed: {e}")
            return await self._fallback_element_matching(description, elements)
    
    async def _fallback_element_matching(self, description: str, elements: List[Dict]) -> Dict[str, Any]:
        """Fallback rule-based element matching with improved scoring."""
        description_lower = description.lower()
        matches = []
        
        for elem in elements:
            score = 0
            reasons = []
            
            # Text matching
            if elem['text']:
                text_lower = elem['text'].lower()
                if description_lower in text_lower:
                    score += 30
                    reasons.append("exact text match")
                else:
                    similarity = difflib.SequenceMatcher(None, description_lower, text_lower).ratio()
                    if similarity > 0.6:
                        score += int(similarity * 25)
                        reasons.append(f"text similarity ({similarity:.2f})")
            
            # Attribute matching
            if elem.get('placeholder') and description_lower in elem['placeholder'].lower():
                score += 20
                reasons.append("placeholder match")
            
            if elem.get('ariaLabel') and description_lower in elem['ariaLabel'].lower():
                score += 20
                reasons.append("aria-label match")
            
            if elem.get('title') and description_lower in elem['title'].lower():
                score += 15
                reasons.append("title match")
            
            # Type-based matching
            type_keywords = {
                'button': ['button', 'click', 'submit', 'send'],
                'input': ['input', 'field', 'textbox', 'enter', 'type'],
                'a': ['link', 'url', 'navigate'],
                'select': ['dropdown', 'select', 'choose']
            }
            
            element_type = elem['tagName']
            if element_type in type_keywords:
                if any(kw in description_lower for kw in type_keywords[element_type]):
                    score += 15
                    reasons.append("type match")
            
            # Position bonus
            y_pos = elem['position']['y']
            if 'top' in description_lower and y_pos < 200:
                score += 10
            elif 'bottom' in description_lower and y_pos > 600:
                score += 10
            
            if score > 0:
                matches.append({
                    'element': elem,
                    'score': score,
                    'reasons': reasons
                })
        
        if matches:
            matches.sort(key=lambda x: x['score'], reverse=True)
            best_match = matches[0]
            
            logger.info(
                f"Fallback matching found element with score {best_match['score']}: "
                f"{best_match['reasons']}"
            )
            
            return {
                "success": True,
                "element": best_match['element'],
                "selector": best_match['element']['selector'],
                "confidence": "medium" if best_match['score'] > 20 else "low",
                "reasoning": f"Rule-based match (score: {best_match['score']}, {', '.join(best_match['reasons'])})",
                "total_scanned": len(elements)
            }
        
        logger.error(f"No suitable element found for: '{description}' in {len(elements)} elements")
        return {
            "success": False,
            "error": f"No suitable element found for: '{description}'",
            "available_elements_count": len(elements),
            "searched_strategies": ["viewport", "relevance", "full scan"]
        }