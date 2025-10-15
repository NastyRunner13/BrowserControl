import re
from typing import Dict, Any, List
from urllib.parse import urlparse
from utils.exceptions import ValidationError

class TaskValidator:
    """Validator for task definitions."""
    
    VALID_ACTIONS = {
        'navigate', 'click', 'type', 'wait', 'screenshot',
        'intelligent_click', 'intelligent_type', 'intelligent_extract',
        'intelligent_wait'
    }
    
    REQUIRED_PARAMS = {
        'navigate': ['url'],
        'click': ['selector'],
        'type': ['selector', 'text'],
        'wait': ['seconds'],
        'screenshot': [],
        'intelligent_click': ['description'],
        'intelligent_type': ['description', 'text'],
        'intelligent_extract': ['description'],
        'intelligent_wait': ['condition']
    }
    
    @staticmethod
    def validate_task(task_data: Dict[str, Any]) -> None:
        """
        Validate a complete task definition.
        
        Args:
            task_data: Task dictionary to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Check required fields
        required_fields = ['task_id', 'name', 'steps']
        for field in required_fields:
            if field not in task_data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate task_id
        if not isinstance(task_data['task_id'], str) or not task_data['task_id']:
            raise ValidationError("task_id must be a non-empty string")
        
        # Validate name
        if not isinstance(task_data['name'], str) or not task_data['name']:
            raise ValidationError("name must be a non-empty string")
        
        # Validate steps
        if not isinstance(task_data['steps'], list) or len(task_data['steps']) == 0:
            raise ValidationError("steps must be a non-empty list")
        
        # Validate each step
        for i, step in enumerate(task_data['steps']):
            try:
                TaskValidator.validate_step(step)
            except ValidationError as e:
                raise ValidationError(f"Step {i}: {str(e)}")
        
        # Validate optional fields
        if 'priority' in task_data:
            if not isinstance(task_data['priority'], int) or task_data['priority'] < 1:
                raise ValidationError("priority must be a positive integer")
        
        if 'timeout' in task_data:
            if not isinstance(task_data['timeout'], (int, float)) or task_data['timeout'] <= 0:
                raise ValidationError("timeout must be a positive number")
        
        if 'retry_count' in task_data:
            if not isinstance(task_data['retry_count'], int) or task_data['retry_count'] < 0:
                raise ValidationError("retry_count must be a non-negative integer")
    
    @staticmethod
    def validate_step(step: Dict[str, Any]) -> None:
        """
        Validate a single step definition.
        
        Args:
            step: Step dictionary to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Check action exists
        if 'action' not in step:
            raise ValidationError("Step missing 'action' field")
        
        action = step['action']
        
        # Check action is valid
        if action not in TaskValidator.VALID_ACTIONS:
            raise ValidationError(
                f"Invalid action '{action}'. "
                f"Valid actions: {', '.join(TaskValidator.VALID_ACTIONS)}"
            )
        
        # Check required parameters
        required = TaskValidator.REQUIRED_PARAMS.get(action, [])
        for param in required:
            if param not in step:
                raise ValidationError(
                    f"Action '{action}' missing required parameter: {param}"
                )
        
        # Validate specific parameters
        if action == 'navigate':
            TaskValidator.validate_url(step['url'])
        
        if action in ['click', 'type'] and 'selector' in step:
            TaskValidator.validate_selector(step['selector'])
        
        if action == 'wait' and 'seconds' in step:
            if not isinstance(step['seconds'], (int, float)) or step['seconds'] <= 0:
                raise ValidationError("wait seconds must be a positive number")
        
        if 'text' in step:
            if not isinstance(step['text'], str):
                raise ValidationError("text parameter must be a string")
        
        if 'description' in step:
            if not isinstance(step['description'], str) or not step['description']:
                raise ValidationError("description must be a non-empty string")
    
    @staticmethod
    def validate_url(url: str) -> None:
        """
        Validate a URL.
        
        Args:
            url: URL to validate
            
        Raises:
            ValidationError: If URL is invalid
        """
        if not isinstance(url, str) or not url:
            raise ValidationError("URL must be a non-empty string")
        
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValidationError(f"Invalid URL format: {url}")
            
            if result.scheme not in ['http', 'https']:
                raise ValidationError(f"URL must use http or https: {url}")
                
        except Exception as e:
            raise ValidationError(f"Invalid URL: {url} - {str(e)}")
    
    @staticmethod
    def validate_selector(selector: str) -> None:
        """
        Validate a CSS selector.
        
        Args:
            selector: CSS selector to validate
            
        Raises:
            ValidationError: If selector is invalid
        """
        if not isinstance(selector, str) or not selector:
            raise ValidationError("Selector must be a non-empty string")
        
        # Basic validation - check for obviously invalid patterns
        if selector.strip() != selector:
            raise ValidationError("Selector should not have leading/trailing whitespace")
        
        # Check for potentially dangerous patterns
        dangerous_patterns = ['javascript:', 'data:', '<script', 'eval(']
        for pattern in dangerous_patterns:
            if pattern.lower() in selector.lower():
                raise ValidationError(f"Selector contains dangerous pattern: {pattern}")
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 10000) -> str:
        """
        Sanitize text input.
        
        Args:
            text: Text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
            
        Raises:
            ValidationError: If text is invalid
        """
        if not isinstance(text, str):
            raise ValidationError("Text must be a string")
        
        if len(text) > max_length:
            raise ValidationError(f"Text exceeds maximum length of {max_length}")
        
        # Remove null bytes and other potentially problematic characters
        sanitized = text.replace('\x00', '')
        
        return sanitized

class ConfigValidator:
    """Validator for configuration."""
    
    @staticmethod
    def validate_api_key(api_key: str, service_name: str = "API") -> None:
        """
        Validate API key format.
        
        Args:
            api_key: API key to validate
            service_name: Name of the service for error messages
            
        Raises:
            ValidationError: If API key is invalid
        """
        if not api_key:
            raise ValidationError(f"{service_name} key is missing")
        
        if not isinstance(api_key, str):
            raise ValidationError(f"{service_name} key must be a string")
        
        if len(api_key) < 10:
            raise ValidationError(f"{service_name} key appears to be too short")
        
        # Check for placeholder values
        placeholder_patterns = ['your_', 'replace_', 'example', 'test_key']
        if any(pattern in api_key.lower() for pattern in placeholder_patterns):
            raise ValidationError(
                f"{service_name} key appears to be a placeholder. "
                "Please set a valid API key."
            )
    
    @staticmethod
    def validate_browser_config(config: Dict[str, Any]) -> None:
        """
        Validate browser configuration.
        
        Args:
            config: Configuration dictionary
            
        Raises:
            ValidationError: If configuration is invalid
        """
        if 'max_browsers' in config:
            max_browsers = config['max_browsers']
            if not isinstance(max_browsers, int) or max_browsers < 1:
                raise ValidationError("max_browsers must be a positive integer")
            if max_browsers > 20:
                raise ValidationError("max_browsers should not exceed 20")
        
        if 'browser_timeout' in config:
            timeout = config['browser_timeout']
            if not isinstance(timeout, (int, float)) or timeout < 1000:
                raise ValidationError("browser_timeout must be at least 1000ms")
        
        if 'intelligence_ratio' in config:
            ratio = config['intelligence_ratio']
            if not isinstance(ratio, (int, float)) or not (0 <= ratio <= 1):
                raise ValidationError("intelligence_ratio must be between 0 and 1")

def validate_tasks_json(tasks_json: str) -> List[Dict[str, Any]]:
    """
    Validate and parse tasks JSON.
    
    Args:
        tasks_json: JSON string containing tasks
        
    Returns:
        Parsed and validated list of tasks
        
    Raises:
        ValidationError: If JSON is invalid or tasks are malformed
    """
    import json
    
    try:
        tasks = json.loads(tasks_json)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON: {str(e)}")
    
    if not isinstance(tasks, list):
        raise ValidationError("Tasks JSON must be a list")
    
    if len(tasks) == 0:
        raise ValidationError("Tasks list cannot be empty")
    
    if len(tasks) > 50:
        raise ValidationError("Too many tasks (max 50)")
    
    # Validate each task
    for i, task in enumerate(tasks):
        try:
            TaskValidator.validate_task(task)
        except ValidationError as e:
            raise ValidationError(f"Task {i} ({task.get('task_id', 'unknown')}): {str(e)}")
    
    return tasks