import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from models.task import IntelligentParallelTask
from core.browser_pool import BrowserPool
from core.executor import IntelligentParallelExecutor

@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return IntelligentParallelTask(
        task_id="test_task_1",
        name="Test Navigation Task",
        context="Testing basic navigation",
        steps=[
            {"action": "navigate", "url": "https://example.com"},
            {"action": "wait", "seconds": 1},
            {"action": "screenshot", "filename": "test_screenshot.png"}
        ]
    )

@pytest.fixture
def mock_playwright_full():
    """Create a fully mocked playwright environment."""
    with patch('core.browser_pool.async_playwright') as mock_pw:
        # Setup playwright
        playwright = AsyncMock()
        mock_pw.return_value.start = AsyncMock(return_value=playwright)
        
        # Setup browser
        browser = AsyncMock()
        browser.is_connected.return_value = True
        playwright.chromium.launch = AsyncMock(return_value=browser)
        
        # Setup context
        context = AsyncMock()
        browser.new_context = AsyncMock(return_value=context)
        
        # Setup page
        page = AsyncMock()
        page.goto = AsyncMock()
        page.screenshot = AsyncMock()
        page.set_default_timeout = Mock()
        context.new_page = AsyncMock(return_value=page)
        
        yield playwright, browser, context, page

@pytest.mark.asyncio
async def test_full_task_execution(mock_playwright_full, sample_task):
    """Test executing a complete task end-to-end."""
    playwright, browser, context, page = mock_playwright_full
    
    pool = BrowserPool(max_browsers=1, headless=True)
    
    try:
        await pool.initialize()
        executor = IntelligentParallelExecutor(pool)
        
        # Get browser instance
        instance = await pool.get_browser_instance(sample_task.task_id)
        
        # Execute all steps
        results = []
        for step in sample_task.steps:
            with patch('os.makedirs'):  # Mock directory creation for screenshot
                result = await executor.execute_intelligent_step(
                    instance.page, step, sample_task.context
                )
                results.append(result)
        
        # Release instance
        await pool.release_browser_instance(instance)
        
        # Verify execution
        assert len(results) == 3
        assert 'Navigated' in results[0]
        assert 'Waited' in results[1]
        assert 'Screenshot' in results[2]
        
    finally:
        await pool.cleanup()

@pytest.mark.asyncio
async def test_parallel_task_execution(mock_playwright_full):
    """Test executing multiple tasks in parallel."""
    playwright, browser, context, page = mock_playwright_full
    
    tasks = [
        IntelligentParallelTask(
            task_id=f"task_{i}",
            name=f"Test Task {i}",
            context="Test context",
            steps=[
                {"action": "navigate", "url": f"https://example{i}.com"},
                {"action": "wait", "seconds": 1}
            ]
        )
        for i in range(3)
    ]
    
    pool = BrowserPool(max_browsers=3, headless=True)
    
    try:
        await pool.initialize()
        executor = IntelligentParallelExecutor(pool)
        
        async def execute_task(task):
            instance = await pool.get_browser_instance(task.task_id)
            try:
                results = []
                for step in task.steps:
                    result = await executor.execute_intelligent_step(
                        instance.page, step, task.context
                    )
                    results.append(result)
                return {'task_id': task.task_id, 'success': True, 'results': results}
            finally:
                await pool.release_browser_instance(instance)
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*[execute_task(task) for task in tasks])
        
        # Verify all tasks completed
        assert len(results) == 3
        assert all(r['success'] for r in results)
        
    finally:
        await pool.cleanup()

@pytest.mark.asyncio
async def test_task_with_error_recovery(mock_playwright_full):
    """Test task execution with error and recovery."""
    playwright, browser, context, page = mock_playwright_full
    
    # Make first navigation fail, second succeed
    page.goto.side_effect = [
        Exception("Network error"),
        None  # Success on retry
    ]
    
    task = IntelligentParallelTask(
        task_id="error_task",
        name="Error Recovery Task",
        context="Testing error recovery",
        steps=[
            {"action": "navigate", "url": "https://example.com"}
        ],
        retry_count=2
    )
    
    pool = BrowserPool(max_browsers=1, headless=True)
    
    try:
        await pool.initialize()
        executor = IntelligentParallelExecutor(pool)
        
        instance = await pool.get_browser_instance(task.task_id)
        
        # First attempt should fail
        with pytest.raises(Exception):
            await executor.execute_intelligent_step(
                instance.page, task.steps[0], task.context
            )
        
        # Second attempt should succeed
        result = await executor.execute_intelligent_step(
            instance.page, task.steps[0], task.context
        )
        
        assert 'Navigated' in result
        
        await pool.release_browser_instance(instance)
        
    finally:
        await pool.cleanup()

@pytest.mark.asyncio
async def test_browser_pool_resource_limits(mock_playwright_full):
    """Test that browser pool respects resource limits."""
    playwright, browser, context, page = mock_playwright_full
    
    pool = BrowserPool(max_browsers=2, headless=True)
    
    try:
        await pool.initialize()
        
        # Get max instances
        instance1 = await pool.get_browser_instance("task_1")
        instance2 = await pool.get_browser_instance("task_2")
        
        # Trying to get another should timeout
        with pytest.raises(Exception):  # BrowserInstanceUnavailableError
            await pool.get_browser_instance("task_3", timeout=1.0)
        
        # Release one and try again
        await pool.release_browser_instance(instance1)
        instance3 = await pool.get_browser_instance("task_3", timeout=2.0)
        
        assert instance3 is not None
        assert instance3.task_id == "task_3"
        
        # Cleanup
        await pool.release_browser_instance(instance2)
        await pool.release_browser_instance(instance3)
        
    finally:
        await pool.cleanup()

@pytest.mark.asyncio
async def test_task_timeout_handling(mock_playwright_full):
    """Test task execution with timeout."""
    playwright, browser, context, page = mock_playwright_full
    
    # Make page hang
    async def slow_goto(*args, **kwargs):
        await asyncio.sleep(10)
    
    page.goto = slow_goto
    
    task = IntelligentParallelTask(
        task_id="timeout_task",
        name="Timeout Task",
        context="Testing timeout",
        steps=[
            {"action": "navigate", "url": "https://example.com"}
        ],
        timeout=2  # 2 second timeout
    )
    
    pool = BrowserPool(max_browsers=1, headless=True)
    
    try:
        await pool.initialize()
        executor = IntelligentParallelExecutor(pool)
        
        instance = await pool.get_browser_instance(task.task_id)
        
        # Execution should timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                executor.execute_intelligent_step(
                    instance.page, task.steps[0], task.context
                ),
                timeout=task.timeout
            )
        
        await pool.release_browser_instance(instance, had_error=True)
        
    finally:
        await pool.cleanup()

@pytest.mark.asyncio
async def test_intelligent_action_workflow(mock_playwright_full):
    """Test workflow with intelligent actions."""
    playwright, browser, context, page = mock_playwright_full
    
    # Mock element finder
    task = IntelligentParallelTask(
        task_id="intelligent_task",
        name="Intelligent Actions Task",
        context="Testing intelligent actions",
        steps=[
            {"action": "navigate", "url": "https://example.com"},
            {"action": "intelligent_click", "description": "search button"},
            {"action": "intelligent_type", "description": "search input", "text": "test query"}
        ]
    )
    
    pool = BrowserPool(max_browsers=1, headless=True)
    
    try:
        await pool.initialize()
        executor = IntelligentParallelExecutor(pool)
        
        # Mock element finder
        executor.element_finder.find_element_intelligently = AsyncMock(return_value={
            'success': True,
            'selector': '#test-element',
            'element': {'text': 'Test'}
        })
        
        # Mock page interactions
        locator = AsyncMock()
        locator.scroll_into_view_if_needed = AsyncMock()
        locator.click = AsyncMock()
        page.locator.return_value = locator
        page.fill = AsyncMock()
        
        instance = await pool.get_browser_instance(task.task_id)
        
        results = []
        for step in task.steps:
            result = await executor.execute_intelligent_step(
                instance.page, step, task.context
            )
            results.append(result)
        
        await pool.release_browser_instance(instance)
        
        # Verify intelligent actions were attempted
        assert len(results) == 3
        assert 'Navigated' in results[0]
        assert 'Clicked' in results[1]
        assert 'Typed' in results[2]
        
    finally:
        await pool.cleanup()

@pytest.mark.asyncio
async def test_workflow_template_execution(mock_playwright_full):
    """Test executing a workflow template."""
    from workflows.templates import WorkflowTemplates
    
    playwright, browser, context, page = mock_playwright_full
    
    task = WorkflowTemplates.create_ecommerce_search(
        site_url="https://example-shop.com",
        product_query="test product",
        site_context="Testing template"
    )
    
    pool = BrowserPool(max_browsers=1, headless=True)
    
    try:
        await pool.initialize()
        executor = IntelligentParallelExecutor(pool)
        
        # Mock all necessary methods
        executor.element_finder.find_element_intelligently = AsyncMock(return_value={
            'success': True,
            'selector': '#test',
            'element': {}
        })
        
        locator = AsyncMock()
        locator.scroll_into_view_if_needed = AsyncMock()
        locator.click = AsyncMock()
        page.locator.return_value = locator
        page.fill = AsyncMock()
        page.text_content = AsyncMock(return_value="Test product")
        page.wait_for_selector = AsyncMock()
        
        instance = await pool.get_browser_instance(task.task_id)
        
        # Execute template steps
        with patch('os.makedirs'):
            results = []
            for step in task.steps:
                result = await executor.execute_intelligent_step(
                    instance.page, step, task.context
                )
                results.append(result)
        
        await pool.release_browser_instance(instance)
        
        # Verify template executed
        assert len(results) > 0
        
    finally:
        await pool.cleanup()