# BrowserControl

A production-ready, enterprise-grade browser automation framework that combines parallel processing with AI-powered element finding for robust, scalable web automation.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Available Actions](#available-actions)
- [Workflow Templates](#workflow-templates)
- [Architecture](#architecture)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

### Core Capabilities
- **🤖 Intelligent Element Finding**: AI-powered element matching that adapts to changing website layouts
- **⚡ Parallel Execution**: Run multiple browser tasks concurrently with managed browser pool
- **🔄 Hybrid Approach**: Combines fast hardcoded selectors with intelligent AI-based finding
- **📋 Workflow Templates**: Pre-built templates for common automation scenarios
- **🛡️ Robust Error Handling**: Comprehensive exception hierarchy with automatic fallbacks
- **🔁 Automatic Retry**: Exponential backoff retry mechanism with circuit breaker pattern
- **✅ Input Validation**: Comprehensive validation for tasks, URLs, selectors, and configuration
- **📊 Comprehensive Logging**: Detailed logs for debugging and monitoring
- **⚙️ Environment-Based Configuration**: Flexible settings via .env file
- **🧪 Full Test Coverage**: Comprehensive test suite with pytest

### Advanced Features
- **Circuit Breaker Pattern**: Prevents cascading failures
- **Health Checks**: Automatic browser instance health monitoring
- **Resource Management**: Intelligent browser pool with timeout handling
- **Type Safety**: Full type hints for better IDE support
- **Custom Exceptions**: Detailed error types for precise error handling

## Installation

### Prerequisites

- Python 3.12 or higher
- pip package manager
- Internet connection for installing dependencies

### Step 1: Clone or Download

```bash
# If using git
git clone <repository-url>
cd intelligent-browser-automation

# Or manually create the directory structure
mkdir intelligent-browser-automation
cd intelligent-browser-automation
```

### Step 2: Create Virtual Environment (Recommended)

```bash
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Step 4: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# REQUIRED: Add your GROQ_API_KEY
```

## Quick Start

### Basic Example

Create a file `test_automation.py`:

```python
import asyncio
import json
from tools.automation_tools import execute_intelligent_parallel_tasks

async def main():
    task = {
        "task_id": "google_search",
        "name": "Simple Google Search",
        "context": "Testing basic search functionality",
        "steps": [
            {"action": "navigate", "url": "https://www.google.com"},
            {"action": "wait", "seconds": 2},
            {"action": "intelligent_type", 
             "description": "search box", 
             "text": "browser automation"},
            {"action": "intelligent_click", 
             "description": "search button"},
            {"action": "wait", "seconds": 3},
            {"action": "screenshot", 
             "filename": "google_results.png"}
        ]
    }
    
    result = await execute_intelligent_parallel_tasks.ainvoke({
        "tasks_json": json.dumps([task]),
        "headless": False
    })
    
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
python test_automation.py
```

### Run Built-in Demos

```bash
python main.py
```

### Run Tests

```bash
pytest tests/ -v
```

## Project Structure

```
intelligent-browser-automation/
│
├── config/                  # Configuration management
│   ├── __init__.py
│   └── settings.py         # Centralized settings from .env
│
├── core/                    # Core automation functionality
│   ├── __init__.py
│   ├── browser_pool.py     # Browser instance pool manager with health checks
│   ├── element_finder.py   # AI-powered element finding with fallbacks
│   └── executor.py         # Task step execution with retry logic
│
├── models/                  # Data models
│   ├── __init__.py
│   └── task.py            # Task definition model with validation
│
├── tools/                   # Automation tools
│   ├── __init__.py
│   └── automation_tools.py # Main execution tools with error handling
│
├── utils/                   # Utility functions
│   ├── __init__.py
│   ├── logger.py          # Logging configuration
│   ├── helpers.py         # Helper functions
│   ├── validators.py      # Input validation utilities
│   ├── exceptions.py      # Custom exception hierarchy
│   └── retry.py           # Retry logic and circuit breaker
│
├── workflows/              # Pre-built workflow templates
│   ├── __init__.py
│   └── templates.py       # Common automation workflows
│
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── conftest.py        # Pytest fixtures
│   ├── test_browser_pool.py
│   ├── test_element_finder.py
│   ├── test_executor.py
│   ├── test_integration.py
│   └── test_validators.py
│
├── screenshots/            # Generated screenshots
├── logs/                   # Application logs
│
├── main.py                 # Entry point with demos
├── requirements.txt        # Python dependencies
├── pyproject.toml         # Project configuration
├── .env.example           # Example environment configuration
├── .python-version        # Python version specification
└── README.md              # This file
```

## Configuration

### Environment Variables

Edit `.env` file to customize behavior:

```bash
# API Keys
GROQ_API_KEY=your_groq_api_key_here

# Browser Configuration
MAX_BROWSERS=5              # Maximum concurrent browser instances
HEADLESS=true              # Run browsers in headless mode
BROWSER_TIMEOUT=30000      # Page load timeout (milliseconds)

# LLM Configuration
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.1

# Execution Configuration
DEFAULT_TASK_TIMEOUT=300   # Task timeout (seconds)
DEFAULT_RETRY_COUNT=3      # Number of retries on failure
INTELLIGENCE_RATIO=0.3     # Ratio of intelligent actions (0.0-1.0)

# Paths
SCREENSHOT_DIR=./screenshots
LOG_DIR=./logs
```

### Getting a GROQ API Key

1. Visit [https://console.groq.com](https://console.groq.com)
2. Sign up for a free account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key to your `.env` file

## Usage Examples

### Example 1: E-commerce Product Search

```python
from workflows.templates import WorkflowTemplates
from tools.automation_tools import execute_intelligent_parallel_tasks
import json
import asyncio

async def search_product():
    task = WorkflowTemplates.create_ecommerce_search(
        site_url="https://www.amazon.com",
        product_query="wireless headphones",
        site_context="Looking for audio products under $100"
    )
    
    result = await execute_intelligent_parallel_tasks.ainvoke({
        "tasks_json": json.dumps([task.to_dict()]),
        "headless": False
    })
    
    print(result)

asyncio.run(search_product())
```

### Example 2: Price Comparison Across Multiple Sites

```python
from workflows.templates import WorkflowTemplates
import json
import asyncio

async def compare_prices():
    tasks = WorkflowTemplates.create_price_comparison(
        product_name="laptop",
        websites=["amazon.com", "bestbuy.com", "newegg.com"]
    )
    
    result = await execute_intelligent_parallel_tasks.ainvoke({
        "tasks_json": json.dumps([task.to_dict() for task in tasks]),
        "headless": False
    })
    
    print(result)

asyncio.run(compare_prices())
```

### Example 3: Job Search

```python
from workflows.templates import WorkflowTemplates
import json
import asyncio

async def search_jobs():
    task = WorkflowTemplates.create_job_search(
        job_site_url="https://www.indeed.com",
        job_title="Python Developer",
        location="San Francisco, CA"
    )
    
    result = await execute_intelligent_parallel_tasks.ainvoke({
        "tasks_json": json.dumps([task.to_dict()]),
        "headless": False
    })
    
    print(result)

asyncio.run(search_jobs())
```

### Example 4: Form Filling

```python
from workflows.templates import WorkflowTemplates
import json
import asyncio

async def fill_form():
    form_data = {
        "name field or full name": "John Doe",
        "email field or email address": "john@example.com",
        "message box or comment field": "This is a test message"
    }
    
    task = WorkflowTemplates.create_form_fill(
        site_url="https://example.com/contact",
        form_data=form_data
    )
    
    result = await execute_intelligent_parallel_tasks.ainvoke({
        "tasks_json": json.dumps([task.to_dict()]),
        "headless": False
    })
    
    print(result)

asyncio.run(fill_form())
```

## Available Actions

### Fast Actions (Hardcoded Selectors)

These actions use traditional CSS selectors for maximum speed:

| Action | Parameters | Description |
|--------|-----------|-------------|
| `navigate` | `url` | Navigate to URL |
| `click` | `selector` | Click element by CSS selector |
| `type` | `selector`, `text` | Type into element by CSS selector |
| `wait` | `seconds` | Wait for specified time |
| `screenshot` | `filename` | Take screenshot |

**Example:**
```python
{"action": "click", "selector": "#submit-button"}
```

### Intelligent Actions (AI-Powered)

These actions use AI to find elements by natural language description:

| Action | Parameters | Description |
|--------|-----------|-------------|
| `intelligent_click` | `description` | Find and click element |
| `intelligent_type` | `description`, `text` | Find and type into element |
| `intelligent_extract` | `description`, `data_type` | Extract data from element |
| `intelligent_wait` | `condition`, `description` | Wait for element by description |

**Example:**
```python
{"action": "intelligent_click", "description": "blue submit button at bottom"}
```

## Workflow Templates

Pre-built templates are available in `workflows/templates.py`:

### WorkflowTemplates.create_ecommerce_search()
```python
task = WorkflowTemplates.create_ecommerce_search(
    site_url="https://example-store.com",
    product_query="search term",
    site_context="additional context for AI"
)
```

### WorkflowTemplates.create_job_search()
```python
task = WorkflowTemplates.create_job_search(
    job_site_url="https://job-site.com",
    job_title="Job Title",
    location="City, State"
)
```

### WorkflowTemplates.create_price_comparison()
```python
tasks = WorkflowTemplates.create_price_comparison(
    product_name="product name",
    websites=["site1.com", "site2.com", "site3.com"]
)
```

### WorkflowTemplates.create_form_fill()
```python
task = WorkflowTemplates.create_form_fill(
    site_url="https://example.com/form",
    form_data={"field description": "value", ...}
)
```

## Architecture

### Browser Pool

The `BrowserPool` class manages multiple browser instances with advanced features:

- **Automatic Instance Creation**: Creates browsers up to `MAX_BROWSERS` limit
- **Instance Reuse**: Efficiently reuses idle browsers
- **Health Monitoring**: Tracks errors and disconnections
- **Timeout Handling**: Configurable timeouts for operations
- **Resource Cleanup**: Proper cleanup on shutdown
- **Thread Safety**: asyncio locks for concurrent access

### Element Finder

The `IntelligentElementFinder` uses a two-tier approach:

1. **AI-Powered Matching**: Uses LLM to understand natural language descriptions
2. **Rule-Based Fallback**: Falls back to fuzzy string matching and heuristics
3. **Scoring System**: Ranks elements by relevance
4. **Position Awareness**: Considers element position on page

### Executor

The `IntelligentParallelExecutor` orchestrates task execution:

- **Sequential Step Execution**: Executes steps in order within a task
- **Parallel Task Execution**: Runs multiple tasks concurrently
- **Retry Logic**: Automatic retries with exponential backoff
- **Error Recovery**: Graceful error handling with detailed reporting
- **Comprehensive Logging**: Tracks all actions for debugging

## Error Handling

### Exception Hierarchy

```python
BrowserAutomationError (Base)
├── BrowserPoolError
│   ├── BrowserInstanceUnavailableError
│   └── BrowserInitializationError
├── ElementNotFoundError
├── ElementInteractionError
├── NavigationError
├── TaskExecutionError
│   └── TaskTimeoutError
├── AIServiceError
├── ConfigurationError
└── ValidationError
```

### Retry Mechanism

The framework includes a sophisticated retry mechanism with:

- **Exponential Backoff**: Delays increase exponentially between retries
- **Configurable Attempts**: Set max retry attempts per operation
- **Exception Filtering**: Specify which exceptions to retry
- **Circuit Breaker**: Prevents cascading failures

### Example: Using Retry Logic

```python
from utils.retry import RetryConfig, retry_async

config = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    exceptions=(BrowserAutomationError,)
)

result = await retry_async(some_async_function, config=config)
```

### Circuit Breaker Pattern

```python
from utils.retry import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0
)

result = await breaker.call(risky_operation)
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_browser_pool.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test
pytest tests/test_browser_pool.py::test_browser_pool_initialization -v
```

### Test Structure

- **Unit Tests**: Individual component testing
- **Integration Tests**: Full workflow testing
- **Fixtures**: Reusable test components in `conftest.py`
- **Mocking**: Mock objects for external dependencies

### Writing Tests

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_my_function():
    # Your test here
    pass
```

## Troubleshooting

### Common Issues

**Issue: "GROQ_API_KEY not found"**
- Ensure `.env` file exists and contains `GROQ_API_KEY=your_key`
- Check that you're running from the project root directory
- Verify the key is not a placeholder value

**Issue: "Playwright not installed"**
- Run: `playwright install chromium`
- If issues persist, try: `playwright install --with-deps chromium`

**Issue: "Element not found"**
- Try using more specific descriptions
- Check if the element is visible (not hidden by CSS)
- Increase wait times before the action
- Use `headless=False` to see what's happening
- Check screenshots in `./screenshots/` directory

**Issue: "Timeout waiting for page"**
- Increase `BROWSER_TIMEOUT` in `.env`
- Check your internet connection
- Website might be slow or blocking automation
- Try using a VPN if region-restricted

**Issue: "BrowserInstanceUnavailableError"**
- Increase `MAX_BROWSERS` in `.env`
- Check if you have enough system resources
- Look for browser instances that aren't being released properly

**Issue: "ValidationError on task input"**
- Verify JSON syntax is correct
- Check all required fields are present
- Ensure URLs use http:// or https://
- Validate selector syntax

### Debug Mode

Run with detailed logging:

```python
import logging
from utils.logger import setup_logger

# Set to DEBUG level
logging.basicConfig(level=logging.DEBUG)
logger = setup_logger(__name__)
```

View screenshots in `./screenshots/` to see what the browser saw.

Check logs in `./logs/` for detailed execution information.

### Health Monitoring

Get browser pool statistics:

```python
stats = pool.get_stats()
print(f"Total instances: {stats['total_instances']}")
print(f"In use: {stats['in_use']}")
print(f"Available: {stats['available']}")
print(f"Healthy: {stats['healthy']}")
```

## Performance Tips

1. **Use Fast Actions When Possible**: If you know the exact selector, use fast actions instead of intelligent ones
2. **Batch Similar Tasks**: Group similar tasks together for better resource usage
3. **Adjust MAX_BROWSERS**: Increase for more parallelism, decrease if running out of memory
4. **Use Headless Mode**: Set `HEADLESS=true` for better performance in production
5. **Optimize Intelligence Ratio**: Use 20-30% intelligent actions for best speed/reliability balance
6. **Monitor Resource Usage**: Use the health monitoring features to track browser instances
7. **Configure Timeouts Appropriately**: Balance between reliability and performance
8. **Use Circuit Breakers**: Prevent cascading failures in production

## Best Practices

### Task Design
- Keep tasks focused and single-purpose
- Use descriptive task IDs and names
- Provide clear context for AI actions
- Set appropriate timeouts and retry counts

### Error Handling
- Always handle potential exceptions
- Use specific exception types when possible
- Log errors with sufficient detail
- Implement graceful degradation

### Testing
- Write tests for custom workflows
- Mock external dependencies
- Test error conditions
- Verify cleanup occurs properly

### Production Deployment
- Use headless mode
- Configure appropriate resource limits
- Implement monitoring and alerting
- Rotate API keys securely
- Use environment variables for configuration

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Ensure all tests pass
6. Update documentation
7. Submit a pull request

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for functions and classes
- Keep functions focused and small
- Add comments for complex logic

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review logs in `./logs/`
- Check test examples in `tests/`
- Open an issue on the repository

## Acknowledgments

- Built with [Playwright](https://playwright.dev/) for browser automation
- Uses [LangChain](https://langchain.com/) for LLM integration
- Powered by [Groq](https://groq.com/) for fast AI inference
- Testing with [pytest](https://pytest.org/)

## Version History

### v0.1.0 (Current)
- Initial release
- AI-powered element finding
- Parallel execution
- Comprehensive error handling
- Full test coverage
- Circuit breaker pattern
- Health monitoring

---

**Note**: This tool is for legitimate automation purposes only. Always respect websites' Terms of Service and robots.txt files. Use responsibly and ethically.

**Security**: Never commit `.env` files with real API keys. Use environment variables in production. Validate all inputs before processing.