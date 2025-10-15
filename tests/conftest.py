import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_task_dict():
    """Fixture providing a sample task dictionary."""
    return {
        'task_id': 'test_task_1',
        'name': 'Test Task',
        'context': 'Testing context',
        'steps': [
            {'action': 'navigate', 'url': 'https://example.com'},
            {'action': 'wait', 'seconds': 1}
        ],
        'priority': 1,
        'timeout': 60,
        'retry_count': 3
    }

@pytest.fixture
def sample_elements():
    """Fixture providing sample DOM elements."""
    return [
        {
            'tagName': 'button',
            'text': 'Submit',
            'type': 'submit',
            'placeholder': '',
            'value': '',
            'id': 'submit-btn',
            'className': 'btn btn-primary',
            'ariaLabel': '',
            'title': '',
            'name': 'submit',
            'href': '',
            'selector': '#submit-btn',
            'position': {'x': 100, 'y': 200, 'width': 100, 'height': 40}
        },
        {
            'tagName': 'input',
            'text': '',
            'type': 'email',
            'placeholder': 'Enter email',
            'value': '',
            'id': 'email',
            'className': 'form-control',
            'ariaLabel': 'Email address',
            'title': '',
            'name': 'email',
            'href': '',
            'selector': '#email',
            'position': {'x': 100, 'y': 100, 'width': 200, 'height': 30}
        }
    ]

@pytest.fixture
def mock_llm():
    """Fixture providing a mock LLM."""
    llm = AsyncMock()
    response = Mock()
    response.content = "0"
    llm.ainvoke = AsyncMock(return_value=response)
    return llm

@pytest.fixture
def mock_page():
    """Fixture providing a mock Playwright page."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.screenshot = AsyncMock()
    page.evaluate = AsyncMock(return_value=[])
    page.text_content = AsyncMock(return_value="Sample text")
    page.inner_html = AsyncMock(return_value="<div>HTML</div>")
    page.input_value = AsyncMock(return_value="input value")
    page.wait_for_selector = AsyncMock()
    page.set_default_timeout = Mock()
    
    # Setup locator mock
    locator = AsyncMock()
    locator.scroll_into_view_if_needed = AsyncMock()
    locator.click = AsyncMock()
    page.locator = Mock(return_value=locator)
    
    return page

@pytest.fixture
def mock_browser():
    """Fixture providing a mock Playwright browser."""
    browser = AsyncMock()
    browser.is_connected = Mock(return_value=True)
    browser.new_context = AsyncMock()
    browser.close = AsyncMock()
    return browser

@pytest.fixture
def mock_context():
    """Fixture providing a mock Playwright context."""
    context = AsyncMock()
    context.new_page = AsyncMock()
    context.close = AsyncMock()
    return context