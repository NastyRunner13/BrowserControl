import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from core.executor import IntelligentParallelExecutor
from core.browser_pool import BrowserPool
from utils.exceptions import ElementNotFoundError, ElementInteractionError

@pytest.fixture
def mock_browser_pool():
    """Create mock browser pool."""
    pool = Mock(spec=BrowserPool)
    return pool

@pytest.fixture
def mock_page():
    """Create mock page object."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.screenshot = AsyncMock()
    page.text_content = AsyncMock(return_value="Sample text")
    page.inner_html = AsyncMock(return_value="<div>HTML</div>")
    page.input_value = AsyncMock(return_value="input value")
    page.wait_for_selector = AsyncMock()
    page.locator = Mock()
    
    # Setup locator mock
    locator = AsyncMock()
    locator.scroll_into_view_if_needed = AsyncMock()
    locator.click = AsyncMock()
    page.locator.return_value = locator
    
    return page

@pytest.fixture
def mock_element_finder():
    """Create mock element finder."""
    finder = Mock()
    finder.find_element_intelligently = AsyncMock(return_value={
        'success': True,
        'selector': '#test-element',
        'element': {'text': 'Test Element'}
    })
    return finder

@pytest.mark.asyncio
async def test_execute_navigate_step(mock_browser_pool, mock_page):
    """Test executing navigate action."""
    executor = IntelligentParallelExecutor(mock_browser_pool)
    
    step = {
        'action': 'navigate',
        'url': 'https://example.com'
    }
    
    result = await executor.execute_intelligent_step(mock_page, step)
    
    assert 'Navigated to' in result
    mock_page.goto.assert_called_once_with(
        'https://example.com',
        wait_until='domcontentloaded',
        timeout=30000
    )

@pytest.mark.asyncio
async def test_execute_click_step(mock_browser_pool, mock_page):
    """Test executing click action."""
    executor = IntelligentParallelExecutor(mock_browser_pool)
    
    step = {
        'action': 'click',
        'selector': '#submit-button'
    }
    
    result = await executor.execute_intelligent_step(mock_page, step)
    
    assert 'Clicked' in result
    mock_page.click.assert_called_once_with('#submit-button', timeout=10000)

@pytest.mark.asyncio
async def test_execute_type_step(mock_browser_pool, mock_page):
    """Test executing type action."""
    executor = IntelligentParallelExecutor(mock_browser_pool)
    
    step = {
        'action': 'type',
        'selector': '#email',
        'text': 'test@example.com'
    }
    
    result = await executor.execute_intelligent_step(mock_page, step)
    
    assert 'Typed' in result
    mock_page.fill.assert_called_once_with('#email', 'test@example.com', timeout=10000)

@pytest.mark.asyncio
async def test_execute_wait_step(mock_browser_pool, mock_page):
    """Test executing wait action."""
    executor = IntelligentParallelExecutor(mock_browser_pool)
    
    step = {
        'action': 'wait',
        'seconds': 2
    }
    
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        result = await executor.execute_intelligent_step(mock_page, step)
        
        assert 'Waited 2 seconds' in result
        mock_sleep.assert_called_once_with(2)

@pytest.mark.asyncio
async def test_execute_screenshot_step(mock_browser_pool, mock_page):
    """Test executing screenshot action."""
    executor = IntelligentParallelExecutor(mock_browser_pool)
    
    step = {
        'action': 'screenshot',
        'filename': 'test.png'
    }
    
    with patch('os.makedirs'):
        result = await executor.execute_intelligent_step(mock_page, step)
        
        assert 'Screenshot saved' in result
        mock_page.screenshot.assert_called_once()

@pytest.mark.asyncio
async def test_execute_intelligent_click(mock_browser_pool, mock_page):
    """Test executing intelligent click action."""
    executor = IntelligentParallelExecutor(mock_browser_pool)
    executor.element_finder = Mock()
    executor.element_finder.find_element_intelligently = AsyncMock(return_value={
        'success': True,
        'selector': '#submit-btn',
        'element': {'text': 'Submit'}
    })
    
    step = {
        'action': 'intelligent_click',
        'description': 'submit button'
    }
    
    result = await executor.execute_intelligent_step(mock_page, step, "Test context")
    
    assert 'Clicked' in result
    executor.element_finder.find_element_intelligently.assert_called_once_with(
        mock_page, 'submit button', 'Test context'
    )

@pytest.mark.asyncio
async def test_intelligent_click_element_not_found(mock_browser_pool, mock_page):
    """Test intelligent click when element is not found."""
    executor = IntelligentParallelExecutor(mock_browser_pool)
    executor.element_finder = Mock()
    executor.element_finder.find_element_intelligently = AsyncMock(return_value={
        'success': False,
        'error': 'Element not found'
    })
    
    step = {
        'action': 'intelligent_click',
        'description': 'nonexistent button'
    }
    
    with pytest.raises(Exception) as exc_info:
        await executor.execute_intelligent_step(mock_page, step)
    
    assert 'Could not find element' in str(exc_info.value)

@pytest.mark.asyncio
async def test_intelligent_click_with_force(mock_browser_pool, mock_page):
    """Test intelligent click falls back to force click on error."""
    executor = IntelligentParallelExecutor(mock_browser_pool)
    executor.element_finder = Mock()
    executor.element_finder.find_element_intelligently = AsyncMock(return_value={
        'success': True,
        'selector': '#tricky-button',
        'element': {'text': 'Button'}
    })
    
    # Make normal click fail
    locator = AsyncMock()
    locator.scroll_into_view_if_needed = AsyncMock()
    locator.click = AsyncMock(side_effect=[Exception("Click failed"), None])
    mock_page.locator.return_value = locator
    mock_page.click.side_effect = Exception("Regular click failed")
    
    step = {
        'action': 'intelligent_click',
        'description': 'tricky button'
    }
    
    result = await executor.execute_intelligent_step(mock_page, step)
    
    assert 'Force-clicked' in result

@pytest.mark.asyncio
async def test_execute_intelligent_type(mock_browser_pool, mock_page):
    """Test executing intelligent type action."""
    executor = IntelligentParallelExecutor(mock_browser_pool)
    executor.element_finder = Mock()
    executor.element_finder.find_element_intelligently = AsyncMock(return_value={
        'success': True,
        'selector': '#email-field',
        'element': {'placeholder': 'Email'}
    })
    
    locator = AsyncMock()
    locator.scroll_into_view_if_needed = AsyncMock()
    mock_page.locator.return_value = locator
    mock_page.fill = AsyncMock()
    
    step = {
        'action': 'intelligent_type',
        'description': 'email input',
        'text': 'user@example.com'
    }
    
    result = await executor.execute_intelligent_step(mock_page, step)
    
    assert 'Typed' in result
    assert 'user@example.com' in result

@pytest.mark.asyncio
async def test_execute_intelligent_extract_text(mock_browser_pool, mock_page):
    """Test executing intelligent extract action for text."""
    executor = IntelligentParallelExecutor(mock_browser_pool)
    executor.element_finder = Mock()
    executor.element_finder.find_element_intelligently = AsyncMock(return_value={
        'success': True,
        'selector': '.product-title',
        'element': {'text': 'Product Name'}
    })
    
    mock_page.text_content = AsyncMock(return_value='Sample Product Title')
    
    step = {
        'action': 'intelligent_extract',
        'description': 'product title',
        'data_type': 'text'
    }
    
    result = await executor.execute_intelligent_step(mock_page, step)
    
    assert 'Extracted' in result
    assert 'Sample Product Title' in result

@pytest.mark.asyncio
async def test_execute_intelligent_extract_html(mock_browser_pool, mock_page):
    """Test executing intelligent extract action for HTML."""
    executor = IntelligentParallelExecutor(mock_browser_pool)
    executor.element_finder = Mock()
    executor.element_finder.find_element_intelligently = AsyncMock(return_value={
        'success': True,
        'selector': '.content',
        'element': {}
    })
    
    mock_page.inner_html = AsyncMock(return_value='<div>Content</div>')
    
    step = {
        'action': 'intelligent_extract',
        'description': 'content area',
        'data_type': 'html'
    }
    
    result = await executor.execute_intelligent_step(mock_page, step)
    
    assert 'Extracted' in result
    assert '<div>Content</div>' in result

@pytest.mark.asyncio
async def test_execute_intelligent_wait_element(mock_browser_pool, mock_page):
    """Test executing intelligent wait for element."""
    executor = IntelligentParallelExecutor(mock_browser_pool)
    executor.element_finder = Mock()
    executor.element_finder.find_element_intelligently = AsyncMock(return_value={
        'success': True,
        'selector': '.loading-spinner',
        'element': {}
    })
    
    mock_page.wait_for_selector = AsyncMock()
    
    step = {
        'action': 'intelligent_wait',
        'condition': 'element',
        'description': 'loading spinner',
        'timeout': 10000
    }
    
    result = await executor.execute_intelligent_step(mock_page, step)
    
    assert 'Successfully waited' in result
    mock_page.wait_for_selector.assert_called_once()

@pytest.mark.asyncio
async def test_execute_intelligent_wait_time(mock_browser_pool, mock_page):
    """Test executing intelligent wait with time condition."""
    executor = IntelligentParallelExecutor(mock_browser_pool)
    
    step = {
        'action': 'intelligent_wait',
        'condition': 'time',
        'seconds': 3
    }
    
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        result = await executor.execute_intelligent_step(mock_page, step)
        
        assert 'Waited 3 seconds' in result
        mock_sleep.assert_called_once_with(3)

@pytest.mark.asyncio
async def test_execute_unknown_action(mock_browser_pool, mock_page):
    """Test executing unknown action raises error."""
    executor = IntelligentParallelExecutor(mock_browser_pool)
    
    step = {
        'action': 'unknown_action'
    }
    
    with pytest.raises(ValueError) as exc_info:
        await executor.execute_intelligent_step(mock_page, step)
    
    assert 'Unknown action' in str(exc_info.value)