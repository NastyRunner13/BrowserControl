"""
Tests for structured action models.
Verifies Pydantic validation, backward compatibility, and edge cases.
"""

import pytest
from models.actions import (
    AgentOutput,
    parse_agent_output,
    NavigateAction,
    ClickAction,
    TypeAction,
    ExtractAction,
    ScrollAction,
    WaitAction,
    FinalAnswerAction,
    NewTabAction,
    SwitchTabAction,
    ACTION_REGISTRY,
)


class TestIndividualActions:
    """Test individual action model validation."""

    def test_navigate_action(self):
        action = NavigateAction(url="https://google.com")
        assert action.url == "https://google.com"

    def test_click_action(self):
        action = ClickAction(description="Submit button")
        assert action.description == "Submit button"

    def test_type_action_defaults(self):
        action = TypeAction(description="search box", text="hello")
        assert action.press_enter is False

    def test_type_action_with_enter(self):
        action = TypeAction(description="search box", text="hello", press_enter=True)
        assert action.press_enter is True

    def test_extract_action_defaults(self):
        action = ExtractAction(description="price")
        assert action.data_type == "text"
        assert action.store_as is None

    def test_scroll_action_defaults(self):
        action = ScrollAction()
        assert action.direction == "down"
        assert action.amount == 500

    def test_final_answer_action(self):
        action = FinalAnswerAction(answer="The result is 42")
        assert action.answer == "The result is 42"

    def test_navigate_missing_url(self):
        with pytest.raises(Exception):
            NavigateAction()

    def test_click_missing_description(self):
        with pytest.raises(Exception):
            ClickAction()


class TestAgentOutput:
    """Test the unified AgentOutput model."""

    def test_parse_navigate(self):
        raw = {"action": "navigate", "url": "https://google.com", "reasoning": "Go to Google"}
        output = AgentOutput.model_validate(raw)
        assert output.action == "navigate"
        assert output.reasoning == "Go to Google"
        assert output.params is not None
        assert output.params.url == "https://google.com"

    def test_parse_click(self):
        raw = {"action": "intelligent_click", "description": "Submit button"}
        output = AgentOutput.model_validate(raw)
        assert output.action == "intelligent_click"
        assert output.params.description == "Submit button"

    def test_parse_type(self):
        raw = {
            "action": "intelligent_type",
            "description": "search box",
            "text": "hello world",
            "press_enter": True,
        }
        output = AgentOutput.model_validate(raw)
        assert output.params.text == "hello world"
        assert output.params.press_enter is True

    def test_parse_extract(self):
        raw = {
            "action": "intelligent_extract",
            "description": "product price",
            "data_type": "text",
            "store_as": "price",
        }
        output = AgentOutput.model_validate(raw)
        assert output.params.store_as == "price"

    def test_parse_final_answer(self):
        raw = {"action": "final_answer", "answer": "The answer is 42"}
        output = AgentOutput.model_validate(raw)
        assert output.params.answer == "The answer is 42"

    def test_parse_scroll(self):
        raw = {"action": "scroll", "direction": "up", "amount": 300}
        output = AgentOutput.model_validate(raw)
        assert output.params.direction == "up"
        assert output.params.amount == 300

    def test_parse_unknown_action(self):
        """Unknown actions should still parse — just with no validated params."""
        raw = {"action": "unknown_action", "foo": "bar"}
        output = AgentOutput.model_validate(raw)
        assert output.action == "unknown_action"
        assert output.params is None
        assert output.raw_params["foo"] == "bar"

    def test_missing_action_field(self):
        """Missing 'action' field should raise error."""
        with pytest.raises(Exception):
            parse_agent_output({"url": "https://google.com"})


class TestBackwardCompatibility:
    """Test dict-like access for backward compatibility."""

    def test_get_method(self):
        output = AgentOutput.model_validate({"action": "navigate", "url": "https://google.com"})
        assert output.get("action") == "navigate"
        assert output.get("url") == "https://google.com"
        assert output.get("nonexistent", "default") == "default"

    def test_bracket_access(self):
        output = AgentOutput.model_validate({"action": "intelligent_click", "description": "button"})
        assert output["action"] == "intelligent_click"
        assert output["description"] == "button"

    def test_bracket_access_missing_key(self):
        output = AgentOutput.model_validate({"action": "navigate", "url": "https://google.com"})
        with pytest.raises(KeyError):
            output["nonexistent"]

    def test_contains(self):
        output = AgentOutput.model_validate({"action": "navigate", "url": "https://google.com"})
        assert "action" in output
        assert "url" in output
        assert "nonexistent" not in output

    def test_to_dict(self):
        raw = {"action": "navigate", "url": "https://google.com", "reasoning": "test"}
        output = AgentOutput.model_validate(raw)
        result = output.to_dict()
        assert result["action"] == "navigate"
        assert result["url"] == "https://google.com"
        assert result["reasoning"] == "test"


class TestParseAgentOutput:
    """Test the parse_agent_output utility."""

    def test_valid_input(self):
        result = parse_agent_output({"action": "navigate", "url": "https://example.com"})
        assert isinstance(result, AgentOutput)
        assert result.action == "navigate"

    def test_invalid_input_no_action(self):
        with pytest.raises(ValueError, match="missing 'action'"):
            parse_agent_output({"url": "https://example.com"})

    def test_invalid_input_not_dict(self):
        with pytest.raises(ValueError):
            parse_agent_output("not a dict")

    def test_action_registry_coverage(self):
        """Ensure all expected actions are registered."""
        expected = [
            "navigate", "intelligent_click", "intelligent_type",
            "intelligent_extract", "scroll", "wait", "screenshot",
            "hover", "final_answer", "new_tab", "switch_tab",
            "close_tab", "list_tabs", "goal_achieved",
        ]
        for action in expected:
            assert action in ACTION_REGISTRY, f"Action '{action}' not in registry"
