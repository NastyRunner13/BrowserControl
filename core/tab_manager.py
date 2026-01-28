"""
Tab Manager for multi-tab browser automation.

Provides functionality to create, switch, close, and manage multiple browser tabs
within a browser context.
"""

import asyncio
from typing import Dict, List, Optional, Any
from playwright.async_api import BrowserContext, Page
from utils.logger import setup_logger

logger = setup_logger(__name__)


class TabManager:
    """
    Manages multiple browser tabs within a browser context.
    
    Provides methods to create, switch, close, and list tabs.
    """
    
    def __init__(self, context: BrowserContext, initial_page: Optional[Page] = None):
        """
        Initialize TabManager with a browser context.
        
        Args:
            context: Playwright browser context
            initial_page: Optional initial page (if already created)
        """
        self.context = context
        self.tabs: Dict[int, Page] = {}
        self.active_tab_index: int = 0
        self._tab_counter: int = 0
        
        if initial_page:
            self._register_tab(initial_page)
    
    def _register_tab(self, page: Page) -> int:
        """Register a page as a tab and return its index."""
        tab_index = self._tab_counter
        self.tabs[tab_index] = page
        self._tab_counter += 1
        self.active_tab_index = tab_index
        
        # Set up close handler to remove tab when closed externally
        page.on("close", lambda: self._on_tab_closed(tab_index))
        
        logger.debug(f"Registered tab {tab_index} (total: {len(self.tabs)})")
        return tab_index
    
    def _on_tab_closed(self, tab_index: int):
        """Handle tab close event."""
        if tab_index in self.tabs:
            del self.tabs[tab_index]
            logger.debug(f"Tab {tab_index} closed externally")
    
    @property
    def active_page(self) -> Optional[Page]:
        """Get the currently active page/tab."""
        return self.tabs.get(self.active_tab_index)
    
    @property
    def tab_count(self) -> int:
        """Get the number of open tabs."""
        return len(self.tabs)
    
    async def new_tab(self, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new tab, optionally navigating to a URL.
        
        Args:
            url: Optional URL to navigate to in the new tab
            
        Returns:
            Dictionary with new tab info
        """
        try:
            page = await self.context.new_page()
            tab_index = self._register_tab(page)
            
            result = {
                "success": True,
                "tab_index": tab_index,
                "total_tabs": self.tab_count
            }
            
            if url:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                result["url"] = url
            
            logger.info(f"Created new tab {tab_index}" + (f" at {url}" if url else ""))
            return result
            
        except Exception as e:
            logger.error(f"Failed to create new tab: {e}")
            return {"success": False, "error": str(e)}
    
    async def switch_tab(self, tab_index: int) -> Dict[str, Any]:
        """
        Switch to a specific tab by index.
        
        Args:
            tab_index: Index of the tab to switch to
            
        Returns:
            Dictionary with switch result
        """
        if tab_index not in self.tabs:
            return {
                "success": False,
                "error": f"Tab {tab_index} not found. Available: {list(self.tabs.keys())}"
            }
        
        try:
            page = self.tabs[tab_index]
            
            # Bring tab to front
            await page.bring_to_front()
            self.active_tab_index = tab_index
            
            url = page.url
            title = await page.title()
            
            logger.info(f"Switched to tab {tab_index}: {title}")
            return {
                "success": True,
                "tab_index": tab_index,
                "url": url,
                "title": title
            }
            
        except Exception as e:
            logger.error(f"Failed to switch to tab {tab_index}: {e}")
            return {"success": False, "error": str(e)}
    
    async def close_tab(self, tab_index: Optional[int] = None) -> Dict[str, Any]:
        """
        Close a specific tab or the current tab.
        
        Args:
            tab_index: Index of tab to close. If None, closes current tab.
            
        Returns:
            Dictionary with close result
        """
        if tab_index is None:
            tab_index = self.active_tab_index
        
        if tab_index not in self.tabs:
            return {
                "success": False,
                "error": f"Tab {tab_index} not found"
            }
        
        if len(self.tabs) == 1:
            return {
                "success": False,
                "error": "Cannot close the last remaining tab"
            }
        
        try:
            page = self.tabs[tab_index]
            await page.close()
            
            # Tab should be removed by the close handler, but ensure cleanup
            if tab_index in self.tabs:
                del self.tabs[tab_index]
            
            # Switch to another tab if we closed the active one
            if self.active_tab_index == tab_index:
                remaining_indices = list(self.tabs.keys())
                if remaining_indices:
                    self.active_tab_index = remaining_indices[0]
                    await self.tabs[self.active_tab_index].bring_to_front()
            
            logger.info(f"Closed tab {tab_index} (remaining: {self.tab_count})")
            return {
                "success": True,
                "closed_tab": tab_index,
                "active_tab": self.active_tab_index,
                "remaining_tabs": self.tab_count
            }
            
        except Exception as e:
            logger.error(f"Failed to close tab {tab_index}: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_tabs(self) -> Dict[str, Any]:
        """
        List all open tabs with their info.
        
        Returns:
            Dictionary with all tab information
        """
        tabs_info = []
        
        for idx, page in self.tabs.items():
            try:
                title = await page.title()
                url = page.url
                tabs_info.append({
                    "index": idx,
                    "title": title,
                    "url": url,
                    "is_active": idx == self.active_tab_index
                })
            except Exception as e:
                tabs_info.append({
                    "index": idx,
                    "error": str(e),
                    "is_active": idx == self.active_tab_index
                })
        
        logger.debug(f"Listed {len(tabs_info)} tabs")
        return {
            "success": True,
            "active_tab": self.active_tab_index,
            "total_tabs": self.tab_count,
            "tabs": tabs_info
        }
    
    async def close_all_except_active(self) -> Dict[str, Any]:
        """Close all tabs except the currently active one."""
        tabs_to_close = [idx for idx in self.tabs.keys() if idx != self.active_tab_index]
        closed_count = 0
        
        for idx in tabs_to_close:
            result = await self.close_tab(idx)
            if result["success"]:
                closed_count += 1
        
        return {
            "success": True,
            "closed_count": closed_count,
            "remaining_tabs": self.tab_count
        }
