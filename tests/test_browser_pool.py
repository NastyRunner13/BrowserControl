import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from core.browser_pool import BrowserPool, BrowserInstance
from utils.exceptions import BrowserInitializationError, BrowserInstanceUnavailableError

@pytest.fixture
def mock_playwright():
    """Create mock playwright instance."""
    playwright = AsyncMock()
    browser = AsyncMock()
    context = AsyncMock()
    page = AsyncMock()
    
    browser.is_connected.return_value = True
    browser.new_context = AsyncMock(return_value=context)
    context.new_page = AsyncMock(return_value=page)
    page.set_default_timeout = Mock()
    
    playwright.chromium.launch = AsyncMock(return_value=browser)
    
    return playwright, browser, context, page

@pytest.mark.asyncio
async def test_browser_pool_initialization():
    """Test browser pool initializes correctly."""
    pool = BrowserPool(max_browsers=3, headless=True)
    
    with patch('core.browser_pool.async_playwright') as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=Mock())
        
        await pool.initialize()
        
        assert pool._initialized is True
        assert pool.max_browsers == 3
        assert pool.headless is True

@pytest.mark.asyncio
async def test_browser_pool_double_initialization():
    """Test that double initialization is handled gracefully."""
    pool = BrowserPool()
    
    with patch('core.browser_pool.async_playwright') as mock_pw:
        mock_pw.return_value.start = AsyncMock(return_value=Mock())
        
        await pool.initialize()
        await pool.initialize()  # Should not raise error
        
        # Start should only be called once
        assert mock_pw.return_value.start.call_count == 1

@pytest.mark.asyncio
async def test_get_browser_instance_creates_new(mock_playwright):
    """Test getting browser instance creates new one when pool is empty."""
    playwright, browser, context, page = mock_playwright
    
    pool = BrowserPool(max_browsers=2)
    pool.playwright = playwright
    pool._initialized = True
    
    instance = await pool.get_browser_instance("task_1")
    
    assert instance is not None
    assert instance.task_id == "task_1"
    assert instance.in_use is True
    assert len(pool.instances) == 1
    playwright.chromium.launch.assert_called_once()

@pytest.mark.asyncio
async def test_get_browser_instance_reuses_existing(mock_playwright):
    """Test that available instances are reused."""
    playwright, browser, context, page = mock_playwright
    
    pool = BrowserPool(max_browsers=2)
    pool.playwright = playwright
    pool._initialized = True
    
    # Get first instance
    instance1 = await pool.get_browser_instance("task_1")
    await pool.release_browser_instance(instance1)
    
    # Get second instance - should reuse
    instance2 = await pool.get_browser_instance("task_2")
    
    assert instance1 == instance2
    assert instance2.task_id == "task_2"
    assert len(pool.instances) == 1

@pytest.mark.asyncio
async def test_browser_pool_max_limit(mock_playwright):
    """Test that pool respects max_browsers limit."""
    playwright, browser, context, page = mock_playwright
    
    pool = BrowserPool(max_browsers=2)
    pool.playwright = playwright
    pool._initialized = True
    
    # Get max instances
    instance1 = await pool.get_browser_instance("task_1")
    instance2 = await pool.get_browser_instance("task_2")
    
    # Try to get one more - should timeout quickly
    with pytest.raises(BrowserInstanceUnavailableError):
        await pool.get_browser_instance("task_3", timeout=1.0)
    
    assert len(pool.instances) == 2

@pytest.mark.asyncio
async def test_release_browser_instance():
    """Test releasing browser instance."""
    pool = BrowserPool()
    
    mock_browser = Mock()
    mock_browser.is_connected.return_value = True
    
    instance = BrowserInstance(
        mock_browser,
        Mock(),
        Mock(),
        "test_instance"
    )
    instance.in_use = True
    instance.task_id = "task_1"
    
    pool.instances.append(instance)
    
    await pool.release_browser_instance(instance)
    
    assert instance.in_use is False
    assert instance.task_id is None

@pytest.mark.asyncio
async def test_release_with_error_increments_count():
    """Test that releasing with error increments error count."""
    pool = BrowserPool()
    
    mock_browser = Mock()
    mock_browser.is_connected.return_value = True
    
    instance = BrowserInstance(
        mock_browser,
        Mock(),
        Mock(),
        "test_instance"
    )
    instance.in_use = True
    pool.instances.append(instance)
    
    await pool.release_browser_instance(instance, had_error=True)
    
    assert instance.error_count == 1

@pytest.mark.asyncio
async def test_unhealthy_instance_removed():
    """Test that unhealthy instances are removed on release."""
    pool = BrowserPool()
    
    mock_browser = Mock()
    mock_browser.is_connected.return_value = True
    mock_context = AsyncMock()
    
    instance = BrowserInstance(
        mock_browser,
        mock_context,
        Mock(),
        "test_instance"
    )
    instance.in_use = True
    instance.error_count = 2  # Will be 3 after release
    pool.instances.append(instance)
    
    await pool.release_browser_instance(instance, had_error=True)
    
    assert len(pool.instances) == 0

@pytest.mark.asyncio
async def test_cleanup_closes_all_instances():
    """Test that cleanup closes all browser instances."""
    pool = BrowserPool()
    
    mock_instances = []
    for i in range(3):
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        instance = BrowserInstance(
            mock_browser,
            mock_context,
            Mock(),
            f"instance_{i}"
        )
        mock_instances.append(instance)
        pool.instances.append(instance)
    
    pool.playwright = AsyncMock()
    
    await pool.cleanup()
    
    # Verify all instances were closed
    for instance in mock_instances:
        instance.context.close.assert_called_once()
        instance.browser.close.assert_called_once()
    
    assert len(pool.instances) == 0
    assert pool._initialized is False

@pytest.mark.asyncio
async def test_get_stats():
    """Test getting pool statistics."""
    pool = BrowserPool(max_browsers=5)
    
    mock_browser = Mock()
    mock_browser.is_connected.return_value = True
    
    # Add some instances
    for i in range(3):
        instance = BrowserInstance(
            mock_browser,
            Mock(),
            Mock(),
            f"instance_{i}"
        )
        instance.in_use = (i == 0)  # First one in use
        pool.instances.append(instance)
    
    stats = pool.get_stats()
    
    assert stats["total_instances"] == 3
    assert stats["in_use"] == 1
    assert stats["available"] == 2
    assert stats["healthy"] == 3
    assert stats["max_browsers"] == 5

@pytest.mark.asyncio
async def test_browser_instance_health_check():
    """Test browser instance health check."""
    mock_browser = Mock()
    
    instance = BrowserInstance(
        mock_browser,
        Mock(),
        Mock(),
        "test_instance"
    )
    
    # Healthy instance
    mock_browser.is_connected.return_value = True
    instance.error_count = 0
    assert instance.is_healthy is True
    
    # Unhealthy due to errors
    instance.error_count = 3
    assert instance.is_healthy is False
    
    # Unhealthy due to disconnection
    instance.error_count = 0
    mock_browser.is_connected.return_value = False
    assert instance.is_healthy is False

@pytest.mark.asyncio
async def test_initialization_failure_raises_error():
    """Test that initialization failure raises appropriate error."""
    pool = BrowserPool()
    
    with patch('core.browser_pool.async_playwright') as mock_pw:
        mock_pw.return_value.start = AsyncMock(side_effect=Exception("Connection failed"))
        
        with pytest.raises(BrowserInitializationError):
            await pool.initialize()