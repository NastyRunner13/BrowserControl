# BrowserControl

<div align="center">

🤖 **AI-Powered Browser Automation Framework** 🚀

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

*Production-ready, enterprise-grade browser automation combining parallel processing with AI-powered element detection*

[Features](#features) • [Quick Start](#quick-start) • [Documentation](#documentation) • [API](#api-usage) • [Examples](#usage-examples)

</div>

---

## 🌟 Key Features

### Core Capabilities
- **🧠 Dual-Mode Intelligence**
  - **DOM-based AI**: Fast natural language element matching
  - **Vision AI (Set-of-Marks)**: Visual element detection with numbered overlays
  - Automatic fallback chain for maximum reliability

- **🔄 Dynamic Agent**
  - Self-correcting execution with LLM-powered replanning
  - Observes page state and adapts strategy mid-task
  - Learns from failures and tries alternative approaches

- **⚡ Parallel Execution**
  - Managed browser pool with health monitoring
  - Execute multiple tasks concurrently
  - Automatic resource allocation and cleanup

- **🛡️ Enterprise-Grade Reliability**
  - Circuit breaker pattern prevents cascading failures
  - Exponential backoff retry with configurable limits
  - Comprehensive exception hierarchy
  - Full async/await throughout

### Advanced Features
- 🎯 **Hybrid Approach**: Fast selectors + intelligent AI fallback
- 📋 **Workflow Templates**: Pre-built for e-commerce, job search, forms
- 🔁 **Self-Correction**: Agent learns from mistakes and retries smartly
- 📊 **Comprehensive Logging**: Debug with detailed execution traces
- 🧪 **Full Test Coverage**: 95%+ test coverage with pytest
- 🐳 **Docker Ready**: Containerized deployment included
- 🌐 **REST API**: FastAPI server for remote automation

---

## 📦 Installation

### Prerequisites
- Python 3.12 or higher
- pip package manager
- 4GB+ RAM recommended
- Internet connection

### Option 1: Local Setup

```bash
# Clone repository
git clone <repository-url>
cd browsercontrol

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### Option 2: Docker Setup

```bash
# Build image
docker build -t browsercontrol:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -e GROQ_API_KEY=your_key_here \
  -v $(pwd)/screenshots:/app/screenshots \
  -v $(pwd)/logs:/app/logs \
  browsercontrol:latest
```

### Getting API Keys

#### GROQ API Key (Required)
1. Visit [console.groq.com](https://console.groq.com)
2. Sign up for free account
3. Navigate to API Keys
4. Create new key
5. Add to `.env`: `GROQ_API_KEY=gsk_...`

**Free Tier Limits:**
- 30 requests/minute
- 14,400 requests/day
- Sufficient for most automation tasks

---

## ⚡ Quick Start

### 1. Simple Navigation & Search

```python
import asyncio
from core.planner import AutomationAgent

async def main():
    agent = AutomationAgent()
    await agent.run(
        "Go to google.com and search for 'AI automation tools'",
        headless=False
    )

asyncio.run(main())
```

### 2. Using Dynamic Agent (Recommended)

```python
from core.planner import DynamicAutomationAgent

async def main():
    agent = DynamicAutomationAgent()
    await agent.run_dynamic(
        "Find the price of iPhone 15 on Amazon",
        headless=False
    )

asyncio.run(main())
```

### 3. Using Workflow Templates

```python
from workflows.templates import WorkflowTemplates
from tools.automation_tools import execute_intelligent_parallel_tasks
import json

async def main():
    # E-commerce search
    task = WorkflowTemplates.create_ecommerce_search(
        site_url="https://www.amazon.com",
        product_query="wireless headphones",
        site_context="Looking for under $100"
    )
    
    result = await execute_intelligent_parallel_tasks.ainvoke({
        "tasks_json": json.dumps([task.to_dict()]),
        "headless": False
    })
    print(result)

asyncio.run(main())
```

### 4. Running Pre-built Demos

```bash
# Interactive mode
python main.py

# One-off command
python main.py "Navigate to github.com and search for python projects"

# Dynamic mode (adaptive)
python main.py --mode=dynamic "Book a flight on kayak.com"

# Headless mode
python main.py --headless "Check weather on weather.com"
```

---

## 🎛️ Configuration

### Environment Variables

Create `.env` file with these settings:

```bash
# ==========================================
# REQUIRED
# ==========================================
GROQ_API_KEY=gsk_your_groq_api_key_here

# ==========================================
# BROWSER SETTINGS
# ==========================================
MAX_BROWSERS=5              # Max concurrent browsers
HEADLESS=true              # Run without UI
BROWSER_TIMEOUT=30000      # Page load timeout (ms)

# ==========================================
# AI MODELS
# ==========================================
# Text-based reasoning
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.1

# Vision-based element detection
VISION_MODEL=llama-3.2-90b-vision-preview
VISION_ENABLED=false       # Enable Set-of-Marks vision
ENABLE_VISION_FALLBACK=true
VISION_MAX_MARKERS=50

# ==========================================
# AGENT BEHAVIOR
# ==========================================
ENABLE_DYNAMIC_AGENT=true
MAX_AGENT_STEPS=50
AGENT_HISTORY_LENGTH=5

ENABLE_SELF_CORRECTION=true
MAX_CORRECTION_ATTEMPTS=2

# ==========================================
# EXECUTION
# ==========================================
DEFAULT_TASK_TIMEOUT=300   # Task timeout (seconds)
DEFAULT_RETRY_COUNT=3
INTELLIGENCE_RATIO=0.3     # 0.0-1.0 (AI vs fast selectors)
MAX_LLM_CALLS_PER_TASK=100

# ==========================================
# PATHS
# ==========================================
SCREENSHOT_DIR=./screenshots
LOG_DIR=./logs

# ==========================================
# ADVANCED (USE WITH CAUTION)
# ==========================================
ENABLE_PERSISTENT_CONTEXT=false  # ⚠️ Stores auth tokens
STORAGE_STATE_PATH=./storage_state.json
```

### Feature Flags Explained

| Feature | Description | When to Enable |
|---------|-------------|----------------|
| `VISION_ENABLED` | Use Vision AI for element detection | Complex UIs, dynamic sites |
| `DYNAMIC_AGENT` | Adaptive planning with self-correction | Unpredictable workflows |
| `SELF_CORRECTION` | Retry with LLM-suggested fixes | Flaky elements |
| `PERSISTENT_CONTEXT` | Save cookies/auth between runs | Login required sites |

---

## 📚 Available Actions

### Fast Actions (CSS Selectors)
Use when you know exact selectors for maximum speed:

```python
{"action": "navigate", "url": "https://example.com"}
{"action": "click", "selector": "#submit-button"}
{"action": "type", "selector": "#email", "text": "user@example.com"}
{"action": "wait", "seconds": 2}
{"action": "screenshot", "filename": "result.png"}
```

### Intelligent Actions (AI-Powered)
Use natural language descriptions:

```python
{"action": "intelligent_click", "description": "blue submit button at bottom"}
{"action": "intelligent_type", "description": "email input field", "text": "test@example.com"}
{"action": "intelligent_extract", "description": "product price", "data_type": "text"}
{"action": "intelligent_wait", "condition": "element", "description": "loading spinner disappears"}
```

### When to Use Which?

| Scenario | Use Fast Actions | Use Intelligent Actions |
|----------|------------------|-------------------------|
| Known selectors | ✅ | ❌ |
| Changing layouts | ❌ | ✅ |
| Dynamic IDs | ❌ | ✅ |
| Speed critical | ✅ | ❌ |
| Unclear structure | ❌ | ✅ |

---

## 🌐 API Usage

### Starting the Server

```bash
# Development
uvicorn server:app --reload --port 8000

# Production
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4

# Docker
docker run -p 8000:8000 browsercontrol:latest
```

### API Endpoints

#### Submit Task

```bash
POST /api/v1/tasks/submit
Content-Type: application/json

{
  "prompt": "Go to amazon.com and search for laptops",
  "headless": true
}

# Response
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "message": "Task submitted successfully"
}
```

#### Check Status

```bash
GET /api/v1/tasks/{job_id}

# Response
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "created_at": "2025-01-15T10:30:00",
  "completed_at": "2025-01-15T10:31:23",
  "result": {
    "summary": "Task completed successfully...",
    "details": { ... }
  }
}
```

#### Health Check

```bash
GET /health

# Response
{
  "status": "healthy",
  "pool_stats": {
    "total_instances": 5,
    "in_use": 2,
    "available": 3,
    "healthy": 5
  }
}
```

### Python Client Example

```python
import httpx
import asyncio

async def submit_task():
    async with httpx.AsyncClient() as client:
        # Submit
        response = await client.post(
            "http://localhost:8000/api/v1/tasks/submit",
            json={
                "prompt": "Search for hotels in Tokyo",
                "headless": True
            }
        )
        job_id = response.json()["job_id"]
        
        # Poll status
        while True:
            status_response = await client.get(
                f"http://localhost:8000/api/v1/tasks/{job_id}"
            )
            status_data = status_response.json()
            
            if status_data["status"] in ["COMPLETED", "FAILED"]:
                print(status_data["result"])
                break
            
            await asyncio.sleep(2)

asyncio.run(submit_task())
```

---

## 💡 Usage Examples

### Example 1: E-commerce Price Comparison

```python
from workflows.templates import WorkflowTemplates
import asyncio

async def compare_prices():
    tasks = WorkflowTemplates.create_price_comparison(
        product_name="iPhone 15",
        websites=["amazon.com", "bestbuy.com", "walmart.com"]
    )
    
    results = await execute_intelligent_parallel_tasks.ainvoke({
        "tasks_json": json.dumps([t.to_dict() for t in tasks]),
        "headless": True
    })
    
    print(results)

asyncio.run(compare_prices())
```

### Example 2: Job Application Automation

```python
async def apply_to_jobs():
    task = WorkflowTemplates.create_job_search(
        job_site_url="https://www.indeed.com",
        job_title="Python Developer",
        location="Remote"
    )
    
    result = await execute_intelligent_parallel_tasks.ainvoke({
        "tasks_json": json.dumps([task.to_dict()]),
        "headless": False
    })
    
    print(result)
```

### Example 3: Form Filling with Dynamic Data

```python
async def fill_contact_form():
    form_data = {
        "name field or full name": "John Doe",
        "email field or email address": "john@example.com",
        "phone number or telephone": "+1-555-0123",
        "message box or comment field": "Interested in your services"
    }
    
    task = WorkflowTemplates.create_form_fill(
        site_url="https://example.com/contact",
        form_data=form_data
    )
    
    result = await execute_intelligent_parallel_tasks.ainvoke({
        "tasks_json": json.dumps([task.to_dict()]),
        "headless": False
    })
```

### Example 4: Dynamic Agent (Adaptive)

```python
async def adaptive_shopping():
    agent = DynamicAutomationAgent()
    
    result = await agent.run_dynamic(
        user_goal=(
            "Go to amazon.com, search for 'mechanical keyboard', "
            "filter by 4+ stars, and tell me the top 3 results with prices"
        ),
        headless=False
    )
    
    print(f"Success: {result['success']}")
    print(f"Steps taken: {result['steps_taken']}")
```

### Example 5: Vision AI for Complex UIs

```python
# Enable vision in .env:
# VISION_ENABLED=true

async def use_vision():
    task = {
        "task_id": "vision_test",
        "name": "Vision-based Navigation",
        "steps": [
            {"action": "navigate", "url": "https://complex-site.com"},
            {"action": "intelligent_click", "description": "login button in top right"},
            # Vision AI will visually locate the element
        ]
    }
    
    result = await execute_intelligent_parallel_tasks.ainvoke({
        "tasks_json": json.dumps([task]),
        "headless": False
    })
```

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────┐
│              User Interface                      │
│  (CLI / API / Python Client)                    │
└───────────────┬─────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────┐
│          AutomationAgent                        │
│  - Natural Language → JSON                      │
│  - Task Planning & Decomposition                │
└───────────────┬─────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────┐
│       IntelligentParallelExecutor               │
│  - Task Orchestration                           │
│  - Parallel Execution                           │
│  - Error Recovery                               │
└───────────┬────────────────────┬────────────────┘
            │                    │
┌───────────▼──────────┐ ┌──────▼────────────────┐
│   BrowserPool        │ │ IntelligentElementFinder│
│  - Instance Mgmt     │ │  - DOM-based AI        │
│  - Health Checks     │ │  - Vision AI (SOM)     │
│  - Resource Limits   │ │  - Rule-based Fallback │
└──────────────────────┘ └───────────────────────┘
```

### Component Breakdown

#### 1. **Browser Pool** (`core/browser_pool.py`)
- Manages up to `MAX_BROWSERS` concurrent instances
- Automatic health monitoring and recovery
- Thread-safe with asyncio locks
- Timeout handling for operations

#### 2. **Element Finder** (`core/element_finder.py`)
- **Tier 1**: DOM-based AI matching (fast)
- **Tier 2**: Vision AI with Set-of-Marks (reliable)
- **Tier 3**: Rule-based fallback (last resort)
- Caching for repeated queries

#### 3. **Executor** (`core/executor.py`)
- Sequential step execution within tasks
- Parallel task execution across tasks
- Retry logic with exponential backoff
- Self-correction with LLM feedback

#### 4. **Dynamic Agent** (`core/planner.py`)
- Observes current page state
- Decides next action based on context
- Self-corrects on failures
- Adapts strategy mid-execution

---

## 🐛 Troubleshooting

### Common Issues

<details>
<summary><b>"GROQ_API_KEY not found"</b></summary>

**Symptoms**: Error on startup  
**Causes**:
- Missing `.env` file
- Running from wrong directory
- Placeholder key value

**Solutions**:
```bash
# 1. Check file exists
ls -la .env

# 2. Verify contents
cat .env | grep GROQ_API_KEY

# 3. Ensure correct directory
pwd  # Should show project root

# 4. Reload environment
source venv/bin/activate
python -c "from config.settings import settings; print(settings.GROQ_API_KEY[:10])"
```
</details>

<details>
<summary><b>"Element not found" errors</b></summary>

**Symptoms**: Task fails at intelligent_click/type steps  
**Solutions**:

1. **Increase specificity**:
```python
# ❌ Too vague
{"action": "intelligent_click", "description": "button"}

# ✅ Better
{"action": "intelligent_click", "description": "blue submit button at bottom right"}
```

2. **Add wait before action**:
```python
{"action": "wait", "seconds": 3},
{"action": "intelligent_click", "description": "submit button"}
```

3. **Enable vision AI**:
```bash
# In .env
VISION_ENABLED=true
ENABLE_VISION_FALLBACK=true
```

4. **Check screenshots**:
```bash
ls screenshots/
# View what the agent saw
```

5. **Run non-headless to observe**:
```python
await agent.run(task, headless=False)
```
</details>

<details>
<summary><b>"BrowserInstanceUnavailableError"</b></summary>

**Symptoms**: Task waits forever or times out  
**Causes**:
- Too many concurrent tasks
- Instances not being released
- Insufficient system resources

**Solutions**:
```bash
# 1. Check current pool stats
curl http://localhost:8000/health

# 2. Increase max browsers (if you have RAM)
# In .env
MAX_BROWSERS=10

# 3. Check for zombie processes
ps aux | grep chromium

# 4. Restart cleanly
pkill -9 chromium
python main.py
```
</details>

<details>
<summary><b>Vision AI not working</b></summary>

**Symptoms**: Falls back to DOM matching, vision errors in logs  
**Causes**:
- Wrong model name
- GROQ rate limit hit
- Model doesn't support vision

**Solutions**:
```bash
# 1. Verify model
# In .env, use one of:
VISION_MODEL=llama-3.2-90b-vision-preview
VISION_MODEL=llama-3.2-11b-vision-preview

# 2. Check rate limits
# Wait 60 seconds or upgrade plan

# 3. Test vision endpoint
python -c "
from core.element_finder import IntelligentElementFinder
finder = IntelligentElementFinder()
print('Vision LLM:', finder.vision_llm)
"
```
</details>

<details>
<summary><b>API returns 500 errors</b></summary>

**Symptoms**: Server crashes or returns internal errors  
**Solutions**:

```bash
# 1. Check logs
tail -f logs/automation_*.log

# 2. Verify browser pool initialized
curl http://localhost:8000/health

# 3. Restart server
uvicorn server:app --reload

# 4. Check memory usage
free -h  # On Linux
# If low, reduce MAX_BROWSERS
```
</details>

### Debug Mode

Enable detailed logging:

```python
import logging
from utils.logger import setup_logger

logging.basicConfig(level=logging.DEBUG)
logger = setup_logger(__name__)

# Now run your task - logs will be verbose
```

View logs:
```bash
# Real-time monitoring
tail -f logs/automation_$(date +%Y%m%d).log

# Search for errors
grep ERROR logs/*.log

# View specific task
grep "task_123" logs/*.log
```

---

## 🧪 Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_browser_pool.py -v

# With coverage
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html

# Specific test
pytest tests/test_browser_pool.py::test_browser_pool_initialization -v

# Skip slow tests
pytest tests/ -v -m "not slow"
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_browser_pool.py     # Pool management
├── test_element_finder.py   # Element detection
├── test_executor.py         # Task execution
├── test_integration.py      # End-to-end flows
└── test_validators.py       # Input validation
```

### Writing Custom Tests

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_my_workflow():
    # Your test here
    agent = AutomationAgent()
    # Mock LLM responses
    agent.llm.ainvoke = AsyncMock(return_value=Mock(content="..."))
    
    result = await agent.run("test task")
    assert result is not None
```

---

## 🚀 Production Deployment

### Checklist

- [ ] Set `HEADLESS=true` in production
- [ ] Use environment secrets, not `.env` file
- [ ] Implement Redis for job storage (replace in-memory)
- [ ] Set up monitoring (Sentry, DataDog)
- [ ] Configure reverse proxy (nginx)
- [ ] Enable rate limiting on API
- [ ] Set up log aggregation
- [ ] Implement proper authentication
- [ ] Use managed database for task history
- [ ] Set up auto-scaling for workers

### Docker Compose (Production)

```yaml
version: '3.8'

services:
  browsercontrol:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - HEADLESS=true
      - MAX_BROWSERS=10
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./screenshots:/app/screenshots
      - ./logs:/app/logs
    depends_on:
      - redis
    restart: unless-stopped
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - browsercontrol
```

### Environment Variables (Production)

```bash
# Use secrets management
export GROQ_API_KEY=$(aws secretsmanager get-secret-value --secret-id groq-api-key --query SecretString --output text)
export REDIS_URL=redis://redis.internal:6379
export MAX_BROWSERS=20
export HEADLESS=true
```

---

## 📊 Performance Tuning

### Optimization Tips

1. **Use Fast Actions When Possible**
   ```python
   # ❌ Slower (AI call)
   {"action": "intelligent_click", "description": "submit"}
   
   # ✅ Faster (direct selector)
   {"action": "click", "selector": "#submit-btn"}
   ```

2. **Batch Similar Tasks**
   ```python
   tasks = [
       create_task("amazon.com"),
       create_task("ebay.com"),
       create_task("walmart.com")
   ]
   # Execute all at once - shares browser pool
   ```

3. **Adjust Intelligence Ratio**
   ```bash
   # In .env
   INTELLIGENCE_RATIO=0.2  # 20% AI, 80% fast actions
   ```

4. **Cache Vision Results**
   ```bash
   VISION_CACHE_ENABLED=true
   ```

5. **Monitor Resource Usage**
   ```python
   pool_stats = pool.get_stats()
   print(f"In use: {pool_stats['in_use']}/{pool_stats['total_instances']}")
   ```

### Benchmarks

| Scenario | Speed | Reliability |
|----------|-------|-------------|
| Fast actions only | ~2s/task | 70% |
| DOM-based AI | ~5s/task | 85% |
| Vision AI fallback | ~10s/task | 95% |
| Dynamic agent | ~15s/task | 98% |

---

## 🔒 Security

### Best Practices

1. **Never commit `.env` files**
   ```bash
   # Add to .gitignore
   .env
   .env.local
   storage_state.json
   ```

2. **Validate all inputs**
   ```python
   from utils.validators import TaskValidator
   TaskValidator.validate_task(task_data)  # Always validate
   ```

3. **Use read-only API keys when possible**

4. **Disable persistent context unless necessary**
   ```bash
   ENABLE_PERSISTENT_CONTEXT=false  # Default
   ```

5. **Implement rate limiting on API**
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   
   @app.post("/api/v1/tasks/submit")
   @limiter.limit("10/minute")
   async def submit_task(...):
       ...
   ```

### Responsible Use

⚠️ **This tool is for legitimate automation only:**
- ✅ Testing your own applications
- ✅ Data collection from public APIs
- ✅ Automating repetitive tasks
- ❌ Bypassing rate limits
- ❌ Scraping copyrighted content
- ❌ DDoS or malicious activities

Always respect:
- Website Terms of Service
- `robots.txt` files
- Rate limits
- Copyright laws

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes with tests
4. Ensure tests pass (`pytest tests/ -v`)
5. Update documentation
6. Commit (`git commit -m 'Add amazing feature'`)
7. Push (`git push origin feature/amazing-feature`)
8. Open Pull Request

### Code Style

```bash
# Format code
black .

# Lint
flake8 .

# Type check
mypy .
```

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with:
- [Playwright](https://playwright.dev/) - Browser automation
- [LangChain](https://langchain.com/) - LLM integration
- [Groq](https://groq.com/) - Fast inference
- [FastAPI](https://fastapi.tiangolo.com/) - API framework
- [pytest](https://pytest.org/) - Testing

---

## 📞 Support

- 📖 [Documentation](https://github.com/NastyRunner13/browsercontrol/wiki)
- 🐛 [Issue Tracker](https://github.com/NastyRunner13/browsercontrol/issues)
- 💬 [Discussions](https://github.com/NastyRunner13/browsercontrol/discussions)
- 📧 Email: princegupta1586@gmail.com

---

<div align="center">

**Built with ❤️ by Prince Gupta**

⭐ Star us on GitHub if this helped you!

</div>
