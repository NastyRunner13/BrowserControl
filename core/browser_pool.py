import asyncio
from typing import List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)

class BrowserInstance:
    """Wrapper for browser instance with context and page."""
    def __init__(self, browser: Browser, context: BrowserContext, page: Page):
        self.browser = browser
        self.context = context
        self.page = page
        self.in_use = False
        self.task_id: Optional[str] = None

class BrowserPool:
    """Manages a pool of browser instances for parallel execution."""
    
    def __init__(self, max_browsers: Optional[int] = None, headless: Optional[bool] = None):
        self.max_browsers = max_browsers or settings.MAX_BROWSERS
        self.headless = headless if headless is not None else settings.HEADLESS
        self.playwright: Optional[Playwright] = None
        self.instances: List[BrowserInstance] = []
        self.lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize the browser pool."""
        self.playwright = await async_playwright().start()
        logger.info(f"Browser pool initialized with max {self.max_browsers} browsers")
    
    async def get_browser_instance(self, task_id: str) -> BrowserInstance:
        """Get an available browser instance or create a new one."""
        async with self.lock:
            # Find available instance
            for instance in self.instances:
                if not instance.in_use:
                    instance.in_use = True
                    instance.task_id = task_id
                    return instance
            
            # Create new instance if under limit
            if len(self.instances) < self.max_browsers:
                if self.playwright is None:
                    raise RuntimeError("Browser pool not initialized. Call initialize() first.")
                    
                browser = await self.playwright.chromium.launch(headless=self.headless)
                context = await browser.new_context()
                page = await context.new_page()
                
                instance = BrowserInstance(browser, context, page)
                instance.in_use = True
                instance.task_id = task_id
                self.instances.append(instance)
                
                logger.info(f"Created new browser instance (total: {len(self.instances)})")
                return instance
            
            # Wait for available instance
            while True:
                await asyncio.sleep(0.5)
                for instance in self.instances:
                    if not instance.in_use:
                        instance.in_use = True
                        instance.task_id = task_id
                        return instance
    
    async def release_browser_instance(self, instance: BrowserInstance):
        """Release a browser instance back to the pool."""
        async with self.lock:
            instance.in_use = False
            instance.task_id = None
    
    async def cleanup(self):
        """Close all browser instances."""
        for instance in self.instances:
            try:
                await instance.context.close()
                await instance.browser.close()
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
        
        if self.playwright:
            await self.playwright.stop()
        
        self.instances.clear()
        logger.info("Browser pool cleaned up")