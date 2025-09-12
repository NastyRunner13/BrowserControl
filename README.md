# BrowserControl

## Overview

BrowserControl is an advanced, intelligent parallel browser automation platform that combines the scalability of parallel processing with adaptive AI reasoning. Powered by tools like Playwright for browser control and LangChain for orchestration, it creates a "god-tier" agent capable of handling complex web interactions that are both fast and smart. The system intelligently finds and interacts with web elements using AI-powered analysis, executes tasks in parallel, and adapts to website changes without hardcoded selectors.

This project is ideal for tasks like web scraping, price comparison, job searching, social media monitoring, and custom browser workflows. It emphasizes a hybrid approach: using fast, traditional actions for predictable steps and intelligent, AI-driven actions for dynamic or critical operations.

## Features

- **Intelligent Element Finding**: Uses AI (via Groq LLM) to analyze page structure and match elements based on natural language descriptions, falling back to rule-based matching if needed.
- **Parallel Task Execution**: Supports concurrent execution of multiple browser tasks with dependency management and retry logic.
- **Hybrid Actions**: Mix of fast (e.g., navigate, click) and intelligent actions (e.g., intelligent_click, intelligent_type) for optimal speed and reliability.
- **Pre-built Workflows**: Templates for e-commerce searches, job applications, and social media monitoring.
- **Custom Workflow Generation**: Create adaptive workflows from natural language descriptions using AI.
- **Tools Integration**: Includes tools for price comparison, benchmarking intelligence vs. speed, and parallel task execution.
- **Demo and Interactive Mode**: Includes demonstrations and an interactive CLI for testing.

## Installation

1. **Clone the Repository**:
   ```
   git clone https://github.com/NastyRunner13/BrowserControl.git
   cd BrowserAgent
   ```

2. **Set Up Environment**:
   - Create a virtual environment (optional but recommended):
     ```
     python -m venv venv
     source venv/bin/activate  # On Windows: venv\Scripts\activate
     ```

3. **Install Dependencies**:
   ```
   pip install langchain-groq playwright python-dotenv
   ```
   - After installing Playwright, install browser binaries:
     ```
     playwright install
     ```

4. **Environment Variables**:
   - Create a `.env` file in the root directory:
     ```
     GROQ_API_KEY=your_groq_api_key_here
     ```
   - Obtain a Groq API key from [groq.com](https://groq.com).

## Usage

Run the main script to start the demonstration and interactive mode:

```
python main.py
```

- The script will run demos for price comparison, custom workflow creation, and system reports.
- Enter interactive mode to input natural language tasks (e.g., "Compare prices for iPhone 15 across amazon.com, bestbuy.com").

### Key Classes and Components

- **IntelligentElementFinder**: Core for AI-powered element detection.
- **IntelligentParallelExecutor**: Handles parallel execution of steps.
- **IntelligentParallelBrowserAgent**: Main agent class for running tasks and creating workflows.
- **Tools**:
  - `execute_intelligent_parallel_tasks`: Run parallel intelligent tasks.
  - `create_intelligent_price_comparison`: Adaptive price checks across sites.
  - `benchmark_intelligence_vs_speed`: Compare intelligent vs. fast actions.

### Customizing

- Adjust `intelligence_ratio` in the agent init for more/less AI usage (default: 0.3).
- Extend workflows in `IntelligentWorkflowTemplates`.
- Add custom tools to the agent's `self.tools` list.

## Examples

### Price Comparison
In interactive mode:
```
Compare prices for wireless gaming headset on amazon.com,bestbuy.com
```
This creates and executes intelligent tasks, adapting to site layouts.

### Custom Workflow
```
Create a workflow to search for jobs on indeed.com
```
The agent uses AI to generate and run a JSON-defined workflow.

## Contributing

Contributions are welcome! Please fork the repo, create a feature branch, and submit a pull request.
