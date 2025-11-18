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
    """Advanced element finding with AI-powered reasoning and smart filtering."""
    
    def __init__(self, llm=None):
        # Convert api_key to SecretStr if it exists
        api_key = settings.GROQ_API_KEY
        if api_key is None:
            raise ValueError("GROQ_API_KEY is not set in environment variables")
        
        self.llm = llm or ChatGroq(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=SecretStr(api_key) if isinstance(api_key, str) else api_key
        )
    
    async def find_element_intelligently(self, page: Page, description: str, 
                                       context: str = "") -> Dict[str, Any]:
        """Find an element using AI-powered analysis with smart filtering."""
        try:
            # Get all interactive elements
            all_elements = await self._get_interactive_elements(page)
            
            if not all_elements:
                return {"success": False, "error": "No interactive elements found"}
            
            logger.info(f"Found {len(all_elements)} total interactive elements")
            
            # Strategy 1: Try viewport-visible elements first (most common case)
            viewport_elements = self._filter_by_viewport(all_elements)
            logger.info(f"Filtered to {len(viewport_elements)} viewport-visible elements")
            
            if viewport_elements:
                match_result = await self._ai_powered_element_matching(
                    description, viewport_elements, context, strategy="viewport"
                )
                if match_result['success']:
                    logger.info("Found element using viewport strategy")
                    return match_result
            
            # Strategy 2: Try relevance-filtered elements (smart pre-filtering)
            relevant_elements = self._filter_by_relevance(all_elements, description)
            logger.info(f"Filtered to {len(relevant_elements)} relevant elements")
            
            if relevant_elements and relevant_elements != viewport_elements:
                match_result = await self._ai_powered_element_matching(
                    description, relevant_elements, context, strategy="relevance"
                )
                if match_result['success']:
                    logger.info("Found element using relevance strategy")
                    return match_result
            
            # Strategy 3: Try all elements (up to 200) as last resort
            logger.info("Trying full element scan as fallback")
            match_result = await self._ai_powered_element_matching(
                description, all_elements[:200], context, strategy="full"
            )
            
            return match_result
            
        except Exception as e:
            logger.error(f"Intelligent element finding failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _filter_by_viewport(self, elements: List[Dict]) -> List[Dict]:
        """
        Filter elements that are currently visible in the viewport.
        
        Args:
            elements: List of all elements
            
        Returns:
            List of viewport-visible elements
        """
        viewport_elements = []
        
        for elem in elements:
            pos = elem.get('position', {})
            y = pos.get('y', 0)
            height = pos.get('height', 0)
            
            # Consider elements within reasonable viewport range
            # Typical viewport height is 600-1080px
            # Include elements slightly below fold for scrolling scenarios
            if y >= 0 and y < 1500 and height > 0:
                viewport_elements.append(elem)
        
        return viewport_elements
    
    def _filter_by_relevance(self, elements: List[Dict], description: str) -> List[Dict]:
        """
        Smart pre-filter elements based on description relevance.
        Keeps elements that are likely matches based on keywords.
        
        Args:
            elements: List of all elements
            description: User's description of target element
            
        Returns:
            List of potentially relevant elements (max 150)
        """
        description_lower = description.lower()
        description_words = set(description_lower.split())
        
        # Extract keywords from description
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
                # Exact phrase match
                if description_lower in text:
                    relevance_score += 50
                # Word overlap
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
            
            # Score based on element type matching description
            tag_name = elem.get('tagName', '')
            elem_type = elem.get('type', '')
            
            if action_hints:
                if 'button' in action_hints and tag_name == 'button':
                    relevance_score += 20
                if 'link' in action_hints and tag_name == 'a':
                    relevance_score += 20
                if 'input' in action_hints and tag_name == 'input':
                    relevance_score += 20
                if 'field' in action_hints and tag_name in ['input', 'textarea']:
                    relevance_score += 20
            
            # Score based on position hints
            y_pos = elem.get('position', {}).get('y', 0)
            if position_hints:
                if 'top' in position_hints and y_pos < 200:
                    relevance_score += 15
                if 'bottom' in position_hints and y_pos > 600:
                    relevance_score += 15
                if 'header' in position_hints and y_pos < 150:
                    relevance_score += 15
                if 'footer' in position_hints and y_pos > 800:
                    relevance_score += 15
            
            # Always include elements with any relevance
            if relevance_score > 0:
                scored_elements.append((relevance_score, elem))
        
        # If no relevance matches, return all elements (let AI decide)
        if not scored_elements:
            logger.warning("No relevant elements found by pre-filter, using all elements")
            return elements[:150]
        
        # Sort by relevance score and return top 150
        scored_elements.sort(key=lambda x: x[0], reverse=True)
        relevant = [elem for score, elem in scored_elements[:150]]
        
        logger.info(f"Relevance filter: Top score={scored_elements[0][0]}, kept {len(relevant)} elements")
        
        return relevant
    
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
                
                function generateBestSelector(element) {
                    if (element.id) return `#${element.id}`;
                    if (element.name) return `[name="${element.name}"]`;
                    
                    if (element.className && typeof element.className === 'string') {
                        const classes = element.className.trim().split(/\\s+/);
                        for (const cls of classes) {
                            if (cls && document.querySelectorAll(`.${CSS.escape(cls)}`).length === 1) {
                                return `.${CSS.escape(cls)}`;
                            }
                        }
                    }
                    
                    const ariaLabel = element.getAttribute('aria-label');
                    if (ariaLabel) {
                        return `[aria-label="${ariaLabel}"]`;
                    }
                    
                    const path = [];
                    let current = element;
                    
                    while (current && current !== document.body) {
                        let selector = current.tagName.toLowerCase();
                        
                        if (current.id) {
                            selector += `#${current.id}`;
                            path.unshift(selector);
                            break;
                        }
                        
                        if (current.className && typeof current.className === 'string') {
                            const classes = current.className.trim().split(/\\s+/);
                            if (classes.length > 0 && classes[0]) {
                                selector += `.${CSS.escape(classes[0])}`;
                            }
                        }
                        
                        const siblings = Array.from(current.parentNode?.children || [])
                            .filter(sibling => sibling.tagName === current.tagName);
                        
                        if (siblings.length > 1) {
                            const index = siblings.indexOf(current) + 1;
                            selector += `:nth-child(${index})`;
                        }
                        
                        path.unshift(selector);
                        current = current.parentElement;
                    }
                    
                    return path.join(' > ');
                }
                
                return elements.sort((a, b) => {
                    if (Math.abs(a.position.y - b.position.y) > 50) {
                        return a.position.y - b.position.y;
                    }
                    return a.position.x - b.position.x;
                });
            }
        """)
        
        return elements_data
    
    async def _ai_powered_element_matching(self, description: str, elements: List[Dict], 
                                         context: str = "", strategy: str = "viewport") -> Dict[str, Any]:
        """
        Use AI to intelligently match description to page elements.
        
        Args:
            description: User's description of target element
            elements: Filtered list of elements to consider
            context: Additional context about the task
            strategy: Which filtering strategy was used
        """
        
        # Limit to top 100 elements for AI analysis (token limit consideration)
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
            
            # Handle response content which can be a string or a list of content blocks
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
            
            # Position bonus for common patterns
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