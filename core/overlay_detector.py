"""
Overlay Detector - Detects and dismisses common web overlays.

Handles modals, popups, cookie banners, login prompts, and other
elements that can intercept pointer events during automation.
"""

import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import Page, Locator
from utils.logger import setup_logger

logger = setup_logger(__name__)


class OverlayDetector:
    """Detects and dismisses common web overlays that block interactions."""
    
    # Common overlay selectors
    OVERLAY_SELECTORS = [
        # Modal dialogs
        '[role="dialog"]',
        '[aria-modal="true"]',
        '[class*="modal"]',
        '[class*="Modal"]',
        '[class*="popup"]',
        '[class*="Popup"]',
        '[class*="overlay"]',
        '[class*="Overlay"]',
        
        # Cookie consent
        '[class*="cookie"]',
        '[class*="Cookie"]',
        '[id*="cookie"]',
        '[id*="consent"]',
        '[class*="consent"]',
        '[class*="gdpr"]',
        '[class*="GDPR"]',
        
        # Newsletter/login popups
        '[class*="newsletter"]',
        '[class*="subscribe"]',
        '[class*="signin"]',
        '[class*="login-popup"]',
        
        # Notification banners
        '[class*="notification"]',
        '[class*="banner"]',
        '[class*="toast"]',
        
        # Common popup containers
        '.ReactModal__Overlay',
        '.MuiDialog-root',
        '.chakra-modal__overlay',
    ]
    
    # Common close button selectors
    CLOSE_BUTTON_SELECTORS = [
        '[aria-label="Close"]',
        '[aria-label="close"]',
        '[aria-label="Dismiss"]',
        '[title="Close"]',
        '[class*="close"]',
        '[class*="Close"]',
        '[class*="dismiss"]',
        '[class*="Dismiss"]',
        'button[class*="close"]',
        '.modal-close',
        '.popup-close',
        '[data-dismiss="modal"]',
        '[data-testid="close-button"]',
        # X button patterns
        'button:has-text("×")',
        'button:has-text("✕")',
        'button:has-text("X")',
    ]
    
    # Accept/dismiss buttons for cookie banners
    ACCEPT_BUTTON_SELECTORS = [
        '[class*="accept"]',
        '[class*="Accept"]',
        'button:has-text("Accept")',
        'button:has-text("Got it")',
        'button:has-text("I agree")',
        'button:has-text("OK")',
        'button:has-text("Continue")',
        'button:has-text("Agree")',
        '[id*="accept"]',
    ]
    
    def __init__(self, page: Page):
        self.page = page
    
    async def detect_overlays(self) -> List[Dict[str, Any]]:
        """
        Detect visible overlays on the page.
        
        Returns:
            List of detected overlay info dicts with selector and type
        """
        detected = []
        
        for selector in self.OVERLAY_SELECTORS:
            try:
                elements = await self.page.locator(selector).all()
                for elem in elements:
                    if await elem.is_visible():
                        # Get bounding box to check if it's actually covering content
                        box = await elem.bounding_box()
                        if box and box['width'] > 100 and box['height'] > 100:
                            detected.append({
                                'selector': selector,
                                'element': elem,
                                'box': box,
                                'type': self._classify_overlay(selector)
                            })
            except Exception:
                continue
        
        if detected:
            logger.info(f"Detected {len(detected)} overlays on page")
        
        return detected
    
    def _classify_overlay(self, selector: str) -> str:
        """Classify overlay type based on selector."""
        selector_lower = selector.lower()
        if 'cookie' in selector_lower or 'consent' in selector_lower or 'gdpr' in selector_lower:
            return 'cookie_banner'
        elif 'modal' in selector_lower or 'dialog' in selector_lower:
            return 'modal'
        elif 'popup' in selector_lower:
            return 'popup'
        elif 'newsletter' in selector_lower or 'subscribe' in selector_lower:
            return 'newsletter'
        elif 'login' in selector_lower or 'signin' in selector_lower:
            return 'login'
        else:
            return 'overlay'
    
    async def dismiss_overlays(self) -> int:
        """
        Attempt to dismiss all detected overlays.
        
        Returns:
            Number of overlays dismissed
        """
        dismissed_count = 0
        overlays = await self.detect_overlays()
        
        for overlay in overlays:
            try:
                success = await self._dismiss_overlay(overlay)
                if success:
                    dismissed_count += 1
                    logger.info(f"Dismissed {overlay['type']} overlay")
                    await asyncio.sleep(0.3)  # Wait for animation
            except Exception as e:
                logger.debug(f"Failed to dismiss overlay: {e}")
        
        return dismissed_count
    
    async def _dismiss_overlay(self, overlay: Dict[str, Any]) -> bool:
        """Attempt to dismiss a single overlay."""
        overlay_type = overlay['type']
        element = overlay['element']
        
        # For cookie banners, try accept button first
        if overlay_type == 'cookie_banner':
            for selector in self.ACCEPT_BUTTON_SELECTORS:
                try:
                    btn = element.locator(selector).first
                    if await btn.is_visible():
                        await btn.click(timeout=2000)
                        return True
                except Exception:
                    continue
        
        # Try close buttons
        for selector in self.CLOSE_BUTTON_SELECTORS:
            try:
                btn = element.locator(selector).first
                if await btn.is_visible():
                    await btn.click(timeout=2000)
                    return True
            except Exception:
                continue
        
        # Try clicking outside (for modals)
        try:
            box = overlay['box']
            # Click in top-left corner of viewport (outside modal)
            await self.page.mouse.click(5, 5)
            await asyncio.sleep(0.2)
            
            # Check if overlay is gone
            if not await element.is_visible():
                return True
        except Exception:
            pass
        
        # Try pressing Escape
        try:
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(0.2)
            if not await element.is_visible():
                return True
        except Exception:
            pass
        
        return False
    
    async def is_element_blocked(self, selector: str) -> bool:
        """
        Check if an element is blocked by an overlay.
        
        Args:
            selector: CSS selector of the target element
            
        Returns:
            True if element is blocked, False otherwise
        """
        try:
            element = self.page.locator(selector).first
            if not await element.is_visible():
                return False
            
            box = await element.bounding_box()
            if not box:
                return False
            
            # Get center point of element
            center_x = box['x'] + box['width'] / 2
            center_y = box['y'] + box['height'] / 2
            
            # Check what element is at that point
            element_at_point = await self.page.evaluate(
                """([x, y]) => {
                    const el = document.elementFromPoint(x, y);
                    return el ? el.outerHTML.substring(0, 200) : null;
                }""",
                [center_x, center_y]
            )
            
            if not element_at_point:
                return False
            
            # Check if blocking element is an overlay
            blocking_indicators = ['modal', 'overlay', 'popup', 'dialog', 'backdrop']
            return any(ind in element_at_point.lower() for ind in blocking_indicators)
            
        except Exception as e:
            logger.debug(f"Error checking if element blocked: {e}")
            return False
    
    async def ensure_clickable(self, selector: str, max_attempts: int = 3) -> bool:
        """
        Ensure an element is clickable by dismissing any blocking overlays.
        
        Args:
            selector: CSS selector of target element
            max_attempts: Maximum dismiss attempts
            
        Returns:
            True if element is now clickable, False otherwise
        """
        for attempt in range(max_attempts):
            if not await self.is_element_blocked(selector):
                return True
            
            dismissed = await self.dismiss_overlays()
            if dismissed == 0:
                # No overlays found but element still blocked
                # Try escape key
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(0.3)
        
        return not await self.is_element_blocked(selector)
