import difflib
from typing import Dict, List, Any
from playwright.async_api import Page
from langchain_groq import ChatGroq
from utils.logger import setup_logger
from utils.helpers import extract_number
from config.settings import settings

logger = setup_logger(__name__)

class IntelligentElementFinder:
    """Advanced element finding with AI-powered reasoning."""
    
    def __init__(self, llm=None):
        self.llm = llm or ChatGroq(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.GROQ_API_KEY
        )
    
    async def find_element_intelligently(self, page: Page, description: str, 
                                       context: str = "") -> Dict[str, Any]:
        """Find an element using AI-powered analysis of the page structure."""
        try:
            dom_elements = await self._get_interactive_elements(page)
            
            if not dom_elements:
                return {"success": False, "error": "No interactive elements found"}
            
            match_result = await self._ai_powered_element_matching(
                description, dom_elements, context
            )
            
            return match_result
            
        except Exception as e:
            logger.error(f"Intelligent element finding failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_interactive_elements(self, page: Page) -> List[Dict]:
        """Extract and analyze interactive elements from the page."""
        elements_data = await page.evaluate("""
            () => {
                const elements = [];
                const selectors = [
                    'a[href]', 'button', 'input', 'textarea', 'select', 
                    '[role="button"]', '[onclick]', '[tabindex]', 'form',
                    '[class*="button"]', '[class*="btn"]', '[class*="search"]',
                    '[class*="submit"]', '[class*="login"]', '[class*="sign"]'
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
                                         context: str = "") -> Dict[str, Any]:
        """Use AI to intelligently match description to page elements."""
        
        element_summaries = []
        for i, elem in enumerate(elements[:20]):
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

ELEMENTS:
{chr(10).join(element_summaries)}

Respond with ONLY the number (0-{len(element_summaries)-1}) of the best match, or -1 if no good match."""

        try:
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            response_text = response.content.strip()
            
            index = extract_number(response_text)
            
            if index is not None and 0 <= index < len(elements):
                selected_element = elements[index]
                return {
                    "success": True,
                    "element": selected_element,
                    "selector": selected_element['selector'],
                    "confidence": "high",
                    "reasoning": f"AI selected element {index}"
                }
            
            return await self._fallback_element_matching(description, elements)
            
        except Exception as e:
            logger.error(f"AI element matching failed: {e}")
            return await self._fallback_element_matching(description, elements)
    
    async def _fallback_element_matching(self, description: str, elements: List[Dict]) -> Dict[str, Any]:
        """Fallback rule-based element matching."""
        description_lower = description.lower()
        matches = []
        
        for elem in elements:
            score = 0
            reasons = []
            
            if elem['text']:
                text_lower = elem['text'].lower()
                if description_lower in text_lower:
                    score += 25
                    reasons.append("exact text match")
                else:
                    similarity = difflib.SequenceMatcher(None, description_lower, text_lower).ratio()
                    if similarity > 0.6:
                        score += int(similarity * 20)
                        reasons.append("text similarity")
            
            if elem.get('placeholder') and description_lower in elem['placeholder'].lower():
                score += 15
                reasons.append("placeholder match")
            
            if elem.get('ariaLabel') and description_lower in elem['ariaLabel'].lower():
                score += 15
                reasons.append("aria-label match")
            
            type_keywords = {
                'button': ['button', 'click', 'submit'],
                'input': ['input', 'field', 'textbox', 'enter'],
                'a': ['link', 'url'],
                'select': ['dropdown', 'select']
            }
            
            element_type = elem['tagName']
            if element_type in type_keywords:
                if any(kw in description_lower for kw in type_keywords[element_type]):
                    score += 10
                    reasons.append("type match")
            
            if score > 0:
                matches.append({
                    'element': elem,
                    'score': score,
                    'reasons': reasons
                })
        
        if matches:
            matches.sort(key=lambda x: x['score'], reverse=True)
            best_match = matches[0]
            
            return {
                "success": True,
                "element": best_match['element'],
                "selector": best_match['element']['selector'],
                "confidence": "medium" if best_match['score'] > 15 else "low",
                "reasoning": f"Rule-based match (score: {best_match['score']})"
            }
        
        return {
            "success": False,
            "error": f"No suitable element found for: '{description}'",
            "available_elements_count": len(elements)
        }
