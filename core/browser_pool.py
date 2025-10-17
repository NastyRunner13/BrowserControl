import asyncio
from typing import List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from utils.logger import setup_logger
from utils.exceptions import (
    BrowserPoolError,
    BrowserInstanceUnavailableError,
    BrowserInitializationError
)
from utils.retry import RetryConfig, retry_async
from config.settings import settings

logger = setup_logger(__name__)

class BrowserInstance:
    """Wrapper for browser instance with context and page."""
    def __init__(self, browser: Browser, context: BrowserContext, page: Page, instance_id: str):
        self.browser = browser
        self.context = context
        self.page = page
        self.instance_id = instance_id
        self.in_use = False
        self.task_id: Optional[str] = None
        self.error_count = 0
        self.created_at = asyncio.get_event_loop().time()
        self.last_used_at = self.created_at
        
    @property
    def is_healthy(self) -> bool:
        """Check if instance is healthy and can be reused."""
        return self.error_count < 3 and self.browser.is_connected()
    
    async def close(self, timeout: float = 5.0):
        """Safely close browser instance with timeout."""
        try:
            await asyncio.wait_for(self.context.close(), timeout=timeout)
            await asyncio.wait_for(self.browser.close(), timeout=timeout)
            logger.debug(f"Browser instance {self.instance_id} closed successfully")
        except asyncio.TimeoutError:
            logger.error(f"Timeout closing browser instance {self.instance_id}")
        except Exception as e:
            logger.error(f"Error closing browser instance {self.instance_id}: {e}")

class BrowserPool:
    """Enhanced browser pool with error handling and health checks."""
    
    def __init__(self, max_browsers: Optional[int] = None, headless: Optional[bool] = None):
        self.max_browsers = max_browsers or settings.MAX_BROWSERS
        self.headless = headless if headless is not None else settings.HEADLESS
        self.playwright: Optional[Playwright] = None
        self.instances: List[BrowserInstance] = []
        self.lock = asyncio.Lock()
        self._instance_counter = 0
        self._initialized = False
        
    async def initialize(self):
        """Initialize the browser pool with error handling."""
        if self._initialized:
            logger.warning("Browser pool already initialized")
            return
        
        try:
            # Fixed: Create a wrapper function for retry_async
            async def start_playwright():
                pw = await async_playwright().start()
                return pw
            
            self.playwright = await retry_async(
                start_playwright,
                config=RetryConfig(max_attempts=3, initial_delay=2.0)
            )
            self._initialized = True
            logger.info(f"Browser pool initialized with max {self.max_browsers} browsers")
            
        except Exception as e:
            raise BrowserInitializationError(f"Failed to initialize browser pool: {e}")
    
    async def get_browser_instance(self, task_id: str, timeout: float = 30.0) -> BrowserInstance:
        """
        Get an available browser instance with timeout and health checks.
        
        Args:
            task_id: ID of the task requesting the instance
            timeout: Maximum time to wait for instance
            
        Returns:
            BrowserInstance ready for use
            
        Raises:
            BrowserInstanceUnavailableError: If no instance available within timeout
            BrowserInitializationError: If instance creation fails
        """
        if not self._initialized:
            raise BrowserPoolError("Browser pool not initialized. Call initialize() first.")
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise BrowserInstanceUnavailableError(
                    f"No browser instance available within {timeout}s. "
                    f"Current instances: {len(self.instances)}/{self.max_browsers}"
                )
            
            async with self.lock:
                # Clean up unhealthy instances
                await self._cleanup_unhealthy_instances()
                
                # Find available healthy instance
                for instance in self.instances:
                    if not instance.in_use and instance.is_healthy:
                        instance.in_use = True
                        instance.task_id = task_id
                        instance.last_used_at = asyncio.get_event_loop().time()
                        logger.debug(f"Reusing browser instance {instance.instance_id} for task {task_id}")
                        return instance
                
                # Create new instance if under limit
                if len(self.instances) < self.max_browsers:
                    try:
                        instance = await self._create_browser_instance(task_id)
                        return instance
                    except Exception as e:
                        logger.error(f"Failed to create browser instance: {e}")
                        # Continue to wait loop
            
            # Wait before retry
            await asyncio.sleep(0.5)
    
    async def _create_browser_instance(self, task_id: str) -> BrowserInstance:
        """Create a new browser instance with retry logic."""
        if self.playwright is None:
            raise BrowserInitializationError("Playwright not initialized")
        
        self._instance_counter += 1
        instance_id = f"browser_{self._instance_counter}"
        
        # Store playwright reference to help type checker
        playwright = self.playwright
        
        try:
            logger.info(f"Creating new browser instance {instance_id}")
            
            # Fixed: Create a proper wrapper function for launch
            async def launch_browser():
                return await playwright.chromium.launch(headless=self.headless)
            
            # Launch browser with retry
            browser = await retry_async(
                launch_browser,
                config=RetryConfig(
                    max_attempts=3,
                    initial_delay=1.0,
                    exceptions=(Exception,)
                )
            )
            
            # Create context and page
            context = await browser.new_context()
            page = await context.new_page()
            
            # Set default timeout
            page.set_default_timeout(settings.BROWSER_TIMEOUT)
            
            instance = BrowserInstance(browser, context, page, instance_id)
            instance.in_use = True
            instance.task_id = task_id
            self.instances.append(instance)
            
            logger.info(f"Created browser instance {instance_id} (total: {len(self.instances)})")
            return instance
            
        except Exception as e:
            logger.error(f"Failed to create browser instance {instance_id}: {e}")
            raise BrowserInitializationError(f"Browser creation failed: {e}")
    
    async def _cleanup_unhealthy_instances(self):
        """Remove unhealthy instances from the pool."""
        unhealthy = [inst for inst in self.instances if not inst.is_healthy and not inst.in_use]
        
        for instance in unhealthy:
            logger.warning(f"Removing unhealthy browser instance {instance.instance_id}")
            self.instances.remove(instance)
            await instance.close()
    
    async def release_browser_instance(self, instance: BrowserInstance, had_error: bool = False):
        """
        Release a browser instance back to the pool.
        
        Args:
            instance: The instance to release
            had_error: Whether the task had an error
        """
        async with self.lock:
            if had_error:
                instance.error_count += 1
                logger.warning(
                    f"Instance {instance.instance_id} released with error "
                    f"(total errors: {instance.error_count})"
                )
            
            instance.in_use = False
            instance.task_id = None
            instance.last_used_at = asyncio.get_event_loop().time()
            
            # Remove if too many errors
            if instance.error_count >= 3:
                logger.warning(f"Removing instance {instance.instance_id} due to excessive errors")
                self.instances.remove(instance)
                await instance.close()
    
    async def cleanup(self, timeout: float = 10.0):
        """
        Close all browser instances with timeout.
        
        Args:
            timeout: Maximum time to wait for cleanup
        """
        logger.info(f"Cleaning up browser pool ({len(self.instances)} instances)")
        
        close_tasks = [instance.close(timeout=5.0) for instance in self.instances]
        
        try:
            await asyncio.wait_for(
                asyncio.gather(*close_tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Browser pool cleanup timed out after {timeout}s")
        
        if self.playwright:
            try:
                await asyncio.wait_for(self.playwright.stop(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.error("Playwright shutdown timed out")
            except Exception as e:
                logger.error(f"Error stopping playwright: {e}")
        
        self.instances.clear()
        self._initialized = False
        logger.info("Browser pool cleaned up")
    
    def get_stats(self) -> dict:
        """Get current pool statistics."""
        return {
            "total_instances": len(self.instances),
            "in_use": sum(1 for inst in self.instances if inst.in_use),
            "available": sum(1 for inst in self.instances if not inst.in_use),
            "healthy": sum(1 for inst in self.instances if inst.is_healthy),
            "max_browsers": self.max_browsers
        }