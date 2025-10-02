# BrowserControl

A production-ready browser automation framework that combines parallel processing with AI-powered element finding for robust, scalable web automation.

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
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Intelligent Element Finding**: AI-powered element matching that adapts to changing website layouts
- **Parallel Execution**: Run multiple browser tasks concurrently with managed browser pool
- **Hybrid Approach**: Combines fast hardcoded selectors with intelligent AI-based finding
- **Workflow Templates**: Pre-built templates for common automation scenarios
- **Robust Error Handling**: Automatic fallbacks and retry mechanisms
- **Comprehensive Logging**: Detailed logs for debugging and monitoring
- **Environment-Based Configuration**: Flexible settings via .env file

## Installation

### Prerequisites

- Python 3.8 or higher
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
│   ├── browser_pool.py     # Browser instance pool manager
│   ├── element_finder.py   # AI-powered element finding
│   └── executor.py         # Task step execution
│
├── models/                  # Data models
│   ├── __init__.py
│   └── task.py            # Task definition model
│
├── tools/                   # Automation tools
│   ├── __init__.py
│   └── automation_tools.py # Main execution tools
│
├── utils/                   # Utility functions
│   ├── __init__.py
│   ├── logger.py          # Logging configuration
│   └── helpers.py         # Helper functions
│
├── workflows/              # Pre-built workflow templates
│   ├── __init__.py
│   └── templates.py       # Common automation workflows
│
├── screenshots/            # Generated screenshots
├── logs/                   # Application logs
│
├── main.py                 # Entry point with demos
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment configuration
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

The `BrowserPool` class manages multiple browser instances:

- Automatically creates browsers up to `MAX_BROWSERS` limit
- Reuses idle browsers for efficiency
- Handles cleanup and resource management
- Thread-safe with asyncio locks

### Element Finder

The `IntelligentElementFinder` uses a two-tier approach:

1. **AI-Powered Matching**: Uses LLM to understand natural language descriptions
2. **Rule-Based Fallback**: Falls back to fuzzy string matching and heuristics

### Executor

The `IntelligentParallelExecutor` orchestrates task execution:

- Executes steps sequentially within a task
- Manages multiple tasks in parallel
- Handles errors and retries
- Logs all actions for debugging

## Troubleshooting

### Common Issues

**Issue: "GROQ_API_KEY not found"**
- Ensure `.env` file exists and contains `GROQ_API_KEY=your_key`
- Check that you're running from the project root directory

**Issue: "Playwright not installed"**
- Run: `playwright install chromium`

**Issue: "Element not found"**
- Try using more specific descriptions
- Check if the element is visible (not hidden by CSS)
- Increase wait times before the action
- Use `headless=False` to see what's happening

**Issue: "Timeout waiting for page"**
- Increase `BROWSER_TIMEOUT` in `.env`
- Check your internet connection
- Website might be slow or blocking automation

### Debug Mode

Run with detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

View screenshots in `./screenshots/` to see what the browser saw.

Check logs in `./logs/` for detailed execution information.

## Performance Tips

1. **Use Fast Actions When Possible**: If you know the exact selector, use fast actions instead of intelligent ones
2. **Batch Similar Tasks**: Group similar tasks together for better resource usage
3. **Adjust MAX_BROWSERS**: Increase for more parallelism, decrease if running out of memory
4. **Use Headless Mode**: Set `HEADLESS=true` for better performance in production
5. **Optimize Intelligence Ratio**: Use 20-30% intelligent actions for best speed/reliability balance

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review logs in `./logs/`
- Open an issue on the repository

## Acknowledgments

- Built with [Playwright](https://playwright.dev/) for browser automation
- Uses [LangChain](https://langchain.com/) for LLM integration
- Powered by [Groq](https://groq.com/) for fast AI inference

---

**Note**: This tool is for legitimate automation purposes only. Always respect websites' Terms of Service and robots.txt files. Use responsibly and ethically.