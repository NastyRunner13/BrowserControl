import pytest
from utils.validators import TaskValidator, ConfigValidator, validate_tasks_json
from utils.exceptions import ValidationError

class TestTaskValidator:
    """Tests for TaskValidator."""
    
    def test_validate_valid_task(self):
        """Test validation passes for valid task."""
        task = {
            'task_id': 'test_1',
            'name': 'Test Task',
            'steps': [
                {'action': 'navigate', 'url': 'https://example.com'}
            ]
        }
        
        # Should not raise
        TaskValidator.validate_task(task)
    
    def test_validate_task_missing_required_field(self):
        """Test validation fails when required fields are missing."""
        task = {
            'name': 'Test Task',
            'steps': []
        }
        
        with pytest.raises(ValidationError) as exc:
            TaskValidator.validate_task(task)
        
        assert 'task_id' in str(exc.value)
    
    def test_validate_task_empty_steps(self):
        """Test validation fails for empty steps list."""
        task = {
            'task_id': 'test_1',
            'name': 'Test Task',
            'steps': []
        }
        
        with pytest.raises(ValidationError) as exc:
            TaskValidator.validate_task(task)
        
        assert 'steps' in str(exc.value)
    
    def test_validate_task_invalid_priority(self):
        """Test validation fails for invalid priority."""
        task = {
            'task_id': 'test_1',
            'name': 'Test Task',
            'steps': [{'action': 'wait', 'seconds': 1}],
            'priority': -1
        }
        
        with pytest.raises(ValidationError) as exc:
            TaskValidator.validate_task(task)
        
        assert 'priority' in str(exc.value)
    
    def test_validate_step_valid(self):
        """Test step validation for valid steps."""
        steps = [
            {'action': 'navigate', 'url': 'https://example.com'},
            {'action': 'click', 'selector': '#button'},
            {'action': 'type', 'selector': '#input', 'text': 'test'},
            {'action': 'wait', 'seconds': 2},
            {'action': 'intelligent_click', 'description': 'submit button'}
        ]
        
        for step in steps:
            TaskValidator.validate_step(step)
    
    def test_validate_step_missing_action(self):
        """Test step validation fails when action is missing."""
        step = {'url': 'https://example.com'}
        
        with pytest.raises(ValidationError) as exc:
            TaskValidator.validate_step(step)
        
        assert 'action' in str(exc.value)
    
    def test_validate_step_invalid_action(self):
        """Test step validation fails for invalid action."""
        step = {'action': 'invalid_action'}
        
        with pytest.raises(ValidationError) as exc:
            TaskValidator.validate_step(step)
        
        assert 'Invalid action' in str(exc.value)
    
    def test_validate_step_missing_required_param(self):
        """Test step validation fails when required params are missing."""
        step = {'action': 'navigate'}  # Missing 'url'
        
        with pytest.raises(ValidationError) as exc:
            TaskValidator.validate_step(step)
        
        assert 'url' in str(exc.value)
    
    def test_validate_url_valid(self):
        """Test URL validation for valid URLs."""
        valid_urls = [
            'https://example.com',
            'http://test.com/path',
            'https://sub.domain.com:8080/path?query=1'
        ]
        
        for url in valid_urls:
            TaskValidator.validate_url(url)
    
    def test_validate_url_invalid(self):
        """Test URL validation for invalid URLs."""
        invalid_urls = [
            '',
            'not a url',
            'ftp://example.com',  # Wrong scheme
            'example.com',  # Missing scheme
            'javascript:alert(1)'
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValidationError):
                TaskValidator.validate_url(url)
    
    def test_validate_selector_valid(self):
        """Test selector validation for valid selectors."""
        valid_selectors = [
            '#id',
            '.class',
            'div.class',
            '[name="test"]',
            'div > span',
            'input[type="text"]'
        ]
        
        for selector in valid_selectors:
            TaskValidator.validate_selector(selector)
    
    def test_validate_selector_invalid(self):
        """Test selector validation for invalid selectors."""
        invalid_selectors = [
            '',
            '  #id  ',  # Whitespace
            'javascript:alert(1)',
            '<script>alert(1)</script>'
        ]
        
        for selector in invalid_selectors:
            with pytest.raises(ValidationError):
                TaskValidator.validate_selector(selector)
    
    def test_sanitize_text_valid(self):
        """Test text sanitization for valid text."""
        text = "Hello, World!"
        result = TaskValidator.sanitize_text(text)
        
        assert result == text
    
    def test_sanitize_text_removes_null_bytes(self):
        """Test that null bytes are removed."""
        text = "Hello\x00World"
        result = TaskValidator.sanitize_text(text)
        
        assert '\x00' not in result
        assert result == "HelloWorld"
    
    def test_sanitize_text_too_long(self):
        """Test that overly long text raises error."""
        text = "a" * 10001
        
        with pytest.raises(ValidationError) as exc:
            TaskValidator.sanitize_text(text)
        
        assert 'maximum length' in str(exc.value)

class TestConfigValidator:
    """Tests for ConfigValidator."""
    
    def test_validate_api_key_valid(self):
        """Test API key validation for valid keys."""
        valid_keys = [
            'sk-1234567890abcdef',
            'gsk_1234567890abcdefghijklmnop'
        ]
        
        for key in valid_keys:
            ConfigValidator.validate_api_key(key)
    
    def test_validate_api_key_empty(self):
        """Test API key validation fails for empty key."""
        with pytest.raises(ValidationError) as exc:
            ConfigValidator.validate_api_key('')
        
        assert 'missing' in str(exc.value)
    
    def test_validate_api_key_placeholder(self):
        """Test API key validation fails for placeholder keys."""
        placeholder_keys = [
            'your_api_key_here',
            'replace_with_key',
            'example_key',
            'test_key_123'
        ]
        
        for key in placeholder_keys:
            with pytest.raises(ValidationError) as exc:
                ConfigValidator.validate_api_key(key)
            
            assert 'placeholder' in str(exc.value).lower()
    
    def test_validate_api_key_too_short(self):
        """Test API key validation fails for short keys."""
        with pytest.raises(ValidationError) as exc:
            ConfigValidator.validate_api_key('short')
        
        assert 'too short' in str(exc.value)
    
    def test_validate_browser_config_valid(self):
        """Test browser config validation for valid config."""
        config = {
            'max_browsers': 5,
            'browser_timeout': 30000,
            'intelligence_ratio': 0.3
        }
        
        ConfigValidator.validate_browser_config(config)
    
    def test_validate_browser_config_invalid_max_browsers(self):
        """Test browser config validation fails for invalid max_browsers."""
        configs = [
            {'max_browsers': 0},
            {'max_browsers': -1},
            {'max_browsers': 25},  # Too high
            {'max_browsers': 'five'}
        ]
        
        for config in configs:
            with pytest.raises(ValidationError):
                ConfigValidator.validate_browser_config(config)
    
    def test_validate_browser_config_invalid_timeout(self):
        """Test browser config validation fails for invalid timeout."""
        config = {'browser_timeout': 500}  # Too low
        
        with pytest.raises(ValidationError) as exc:
            ConfigValidator.validate_browser_config(config)
        
        assert 'timeout' in str(exc.value)
    
    def test_validate_browser_config_invalid_ratio(self):
        """Test browser config validation fails for invalid intelligence ratio."""
        configs = [
            {'intelligence_ratio': -0.1},
            {'intelligence_ratio': 1.5},
            {'intelligence_ratio': 'high'}
        ]
        
        for config in configs:
            with pytest.raises(ValidationError):
                ConfigValidator.validate_browser_config(config)

class TestValidateTasksJson:
    """Tests for validate_tasks_json function."""
    
    def test_validate_tasks_json_valid(self):
        """Test validation of valid tasks JSON."""
        json_str = '''[
            {
                "task_id": "task_1",
                "name": "Test Task",
                "steps": [
                    {"action": "navigate", "url": "https://example.com"}
                ]
            }
        ]'''
        
        tasks = validate_tasks_json(json_str)
        
        assert len(tasks) == 1
        assert tasks[0]['task_id'] == 'task_1'
    
    def test_validate_tasks_json_invalid_json(self):
        """Test validation fails for invalid JSON."""
        json_str = '{"invalid": json'
        
        with pytest.raises(ValidationError) as exc:
            validate_tasks_json(json_str)
        
        assert 'Invalid JSON' in str(exc.value)
    
    def test_validate_tasks_json_not_list(self):
        """Test validation fails when JSON is not a list."""
        json_str = '{"task_id": "test"}'
        
        with pytest.raises(ValidationError) as exc:
            validate_tasks_json(json_str)
        
        assert 'must be a list' in str(exc.value)
    
    def test_validate_tasks_json_empty_list(self):
        """Test validation fails for empty list."""
        json_str = '[]'
        
        with pytest.raises(ValidationError) as exc:
            validate_tasks_json(json_str)
        
        assert 'cannot be empty' in str(exc.value)
    
    def test_validate_tasks_json_too_many_tasks(self):
        """Test validation fails for too many tasks."""
        tasks = [
            {
                'task_id': f'task_{i}',
                'name': f'Task {i}',
                'steps': [{'action': 'wait', 'seconds': 1}]
            }
            for i in range(51)
        ]
        
        import json
        json_str = json.dumps(tasks)
        
        with pytest.raises(ValidationError) as exc:
            validate_tasks_json(json_str)
        
        assert 'Too many tasks' in str(exc.value)