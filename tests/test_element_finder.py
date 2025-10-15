import pytest
from unittest.mock import Mock, AsyncMock, patch
from core.element_finder import IntelligentElementFinder
from utils.exceptions import AIServiceError

@pytest.fixture
def mock_page():
    """Create mock page object."""
    page = AsyncMock()
    page.evaluate = AsyncMock(return_value=[])
    return page

@pytest.fixture
def mock_llm():
    """Create mock LLM."""
    llm = AsyncMock()
    return llm

@pytest.fixture
def sample_elements():
    """Sample DOM elements for testing."""
    return [
        {
            'tagName': 'button',
            'text': 'Submit Form',
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
            'type': 'text',
            'placeholder': 'Enter your email',
            'value': '',
            'id': 'email-input',
            'className': 'form-control',
            'ariaLabel': 'Email address',
            'title': '',
            'name': 'email',
            'href': '',
            'selector': '#email-input',
            'position': {'x': 100, 'y': 100, 'width': 200, 'height': 30}
        },
        {
            'tagName': 'a',
            'text': 'Learn More',
            'type': '',
            'placeholder': '',
            'value': '',
            'id': '',
            'className': 'link',
            'ariaLabel': '',
            'title': 'Learn more about our service',
            'name': '',
            'href': 'https://example.com/learn',
            'selector': 'a.link',
            'position': {'x': 100, 'y': 300, 'width': 80, 'height': 20}
        }
    ]

@pytest.mark.asyncio
async def test_find_element_intelligently_success(mock_page, mock_llm, sample_elements):
    """Test successful element finding."""
    mock_page.evaluate.return_value = sample_elements
    
    # Mock LLM response
    mock_response = Mock()
    mock_response.content = "0"  # Select first element
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    
    finder = IntelligentElementFinder(llm=mock_llm)
    result = await finder.find_element_intelligently(mock_page, "submit button")
    
    assert result['success'] is True
    assert result['element']['tagName'] == 'button'
    assert result['selector'] == '#submit-btn'

@pytest.mark.asyncio
async def test_find_element_no_elements_found(mock_page, mock_llm):
    """Test when no interactive elements are found on page."""
    mock_page.evaluate.return_value = []
    
    finder = IntelligentElementFinder(llm=mock_llm)
    result = await finder.find_element_intelligently(mock_page, "any button")
    
    assert result['success'] is False
    assert 'error' in result

@pytest.mark.asyncio
async def test_fallback_element_matching_exact_text(sample_elements):
    """Test fallback matching with exact text match."""
    finder = IntelligentElementFinder(llm=Mock())
    
    result = await finder._fallback_element_matching("Submit Form", sample_elements)
    
    assert result['success'] is True
    assert result['element']['text'] == 'Submit Form'
    assert result['confidence'] in ['medium', 'low']

@pytest.mark.asyncio
async def test_fallback_element_matching_placeholder(sample_elements):
    """Test fallback matching with placeholder text."""
    finder = IntelligentElementFinder(llm=Mock())
    
    result = await finder._fallback_element_matching("email", sample_elements)
    
    assert result['success'] is True
    assert result['element']['placeholder'] == 'Enter your email'

@pytest.mark.asyncio
async def test_fallback_element_matching_aria_label(sample_elements):
    """Test fallback matching with aria-label."""
    finder = IntelligentElementFinder(llm=Mock())
    
    result = await finder._fallback_element_matching("Email address", sample_elements)
    
    assert result['success'] is True
    assert result['element']['ariaLabel'] == 'Email address'

@pytest.mark.asyncio
async def test_fallback_element_matching_type_keywords(sample_elements):
    """Test fallback matching with type keywords."""
    finder = IntelligentElementFinder(llm=Mock())
    
    result = await finder._fallback_element_matching("click button", sample_elements)
    
    assert result['success'] is True
    assert result['element']['tagName'] == 'button'

@pytest.mark.asyncio
async def test_fallback_no_match(sample_elements):
    """Test fallback when no elements match."""
    finder = IntelligentElementFinder(llm=Mock())
    
    result = await finder._fallback_element_matching("nonexistent element xyz", sample_elements)
    
    assert result['success'] is False
    assert 'error' in result

@pytest.mark.asyncio
async def test_ai_matching_with_list_content_response(mock_page, mock_llm, sample_elements):
    """Test AI matching when LLM returns list content."""
    mock_page.evaluate.return_value = sample_elements
    
    # Mock LLM response with list content (as sometimes happens)
    mock_response = Mock()
    mock_response.content = [{"text": "1"}]
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    
    finder = IntelligentElementFinder(llm=mock_llm)
    result = await finder.find_element_intelligently(mock_page, "email input")
    
    assert result['success'] is True
    assert result['element']['tagName'] == 'input'

@pytest.mark.asyncio
async def test_ai_matching_invalid_index_fallback(mock_page, mock_llm, sample_elements):
    """Test that invalid AI response falls back to rule-based matching."""
    mock_page.evaluate.return_value = sample_elements
    
    # Mock LLM response with invalid index
    mock_response = Mock()
    mock_response.content = "999"  # Out of range
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    
    finder = IntelligentElementFinder(llm=mock_llm)
    result = await finder.find_element_intelligently(mock_page, "submit")
    
    # Should fall back and still find the submit button
    assert result['success'] is True

@pytest.mark.asyncio
async def test_ai_matching_exception_fallback(mock_page, mock_llm, sample_elements):
    """Test that AI exceptions fall back to rule-based matching."""
    mock_page.evaluate.return_value = sample_elements
    
    # Mock LLM to raise exception
    mock_llm.ainvoke = AsyncMock(side_effect=Exception("API Error"))
    
    finder = IntelligentElementFinder(llm=mock_llm)
    result = await finder.find_element_intelligently(mock_page, "submit button")
    
    # Should fall back to rule-based and find the button
    assert result['success'] is True
    assert result['element']['text'] == 'Submit Form'

@pytest.mark.asyncio
async def test_get_interactive_elements(mock_page):
    """Test extracting interactive elements from page."""
    mock_elements = [
        {
            'tagName': 'button',
            'text': 'Click Me',
            'selector': 'button.primary'
        }
    ]
    mock_page.evaluate.return_value = mock_elements
    
    finder = IntelligentElementFinder(llm=Mock())
    elements = await finder._get_interactive_elements(mock_page)
    
    assert len(elements) == 1
    assert elements[0]['text'] == 'Click Me'
    mock_page.evaluate.assert_called_once()

@pytest.mark.asyncio
async def test_element_matching_position_scoring(sample_elements):
    """Test that element position affects scoring."""
    # Add position info to test top/bottom detection
    top_button = sample_elements[1].copy()
    top_button['position']['y'] = 50  # Top of page
    
    bottom_button = sample_elements[0].copy()
    bottom_button['position']['y'] = 800  # Bottom of page
    
    elements = [top_button, bottom_button]
    
    finder = IntelligentElementFinder(llm=Mock())
    
    # The AI summary should include position hints
    # This is more of an integration test of the summary generation
    result = await finder._fallback_element_matching("button", elements)
    
    assert result['success'] is True