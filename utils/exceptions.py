class BrowserAutomationError(Exception):
    """Base exception for browser automation errors."""
    pass

class BrowserPoolError(BrowserAutomationError):
    """Errors related to browser pool management."""
    pass

class BrowserInstanceUnavailableError(BrowserPoolError):
    """No browser instances available."""
    pass

class BrowserInitializationError(BrowserPoolError):
    """Failed to initialize browser."""
    pass

class ElementNotFoundError(BrowserAutomationError):
    """Element could not be found on the page."""
    def __init__(self, description: str, available_elements: int = 0):
        self.description = description
        self.available_elements = available_elements
        super().__init__(
            f"Element '{description}' not found. "
            f"Available elements: {available_elements}"
        )

class ElementInteractionError(BrowserAutomationError):
    """Failed to interact with element."""
    def __init__(self, action: str, element: str, reason: str):
        self.action = action
        self.element = element
        self.reason = reason
        super().__init__(
            f"Failed to {action} element '{element}': {reason}"
        )

class NavigationError(BrowserAutomationError):
    """Failed to navigate to URL."""
    def __init__(self, url: str, reason: str):
        self.url = url
        self.reason = reason
        super().__init__(f"Failed to navigate to {url}: {reason}")

class TaskExecutionError(BrowserAutomationError):
    """Task execution failed."""
    def __init__(self, task_id: str, step_index: int, reason: str):
        self.task_id = task_id
        self.step_index = step_index
        self.reason = reason
        super().__init__(
            f"Task {task_id} failed at step {step_index}: {reason}"
        )

class TaskTimeoutError(TaskExecutionError):
    """Task execution timed out."""
    def __init__(self, task_id: str, timeout: int):
        self.timeout = timeout
        super().__init__(
            task_id=task_id,
            step_index=-1,
            reason=f"Task timed out after {timeout}s"
        )

class AIServiceError(BrowserAutomationError):
    """AI service (LLM) related errors."""
    def __init__(self, service: str, reason: str):
        self.service = service
        self.reason = reason
        super().__init__(f"AI service '{service}' error: {reason}")

class ConfigurationError(BrowserAutomationError):
    """Configuration or environment errors."""
    pass

class ValidationError(BrowserAutomationError):
    """Input validation errors."""
    pass