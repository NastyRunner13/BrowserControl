"""
Structured Action Models for BrowserAgent.

Pydantic-validated models for every agent action type, replacing raw Dict[str, Any].
Inspired by browser-use's ActionModel pattern for type-safe action dispatch.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field, model_validator


# ==========================================
# Individual Action Models
# ==========================================

class NavigateAction(BaseModel):
    """Navigate to a URL."""
    url: str = Field(..., description="URL to navigate to")

class ClickAction(BaseModel):
    """Click an element described in natural language."""
    description: str = Field(..., description="Natural language description of element to click")

class TypeAction(BaseModel):
    """Type text into an input element."""
    description: str = Field(..., description="Natural language description of input field")
    text: str = Field(..., description="Text to type")
    press_enter: bool = Field(False, description="Whether to press Enter after typing")

class ExtractAction(BaseModel):
    """Extract data from the page."""
    description: str = Field(..., description="What data to extract")
    data_type: str = Field("text", description="Type of data: text, html, value, attribute")
    store_as: Optional[str] = Field(None, description="Variable name to store extracted data")

class ScrollAction(BaseModel):
    """Scroll the page."""
    direction: Literal["up", "down", "left", "right"] = Field("down", description="Scroll direction")
    amount: int = Field(500, description="Pixels to scroll")

class WaitAction(BaseModel):
    """Wait for a duration or condition."""
    seconds: Optional[float] = Field(None, description="Seconds to wait")
    condition: Optional[str] = Field(None, description="Condition type: element, url, text")
    description: Optional[str] = Field(None, description="What to wait for")
    timeout: int = Field(10000, description="Timeout in ms")

class ScreenshotAction(BaseModel):
    """Take a screenshot."""
    filename: str = Field("screenshot.png", description="Filename for screenshot")

class HoverAction(BaseModel):
    """Hover over an element."""
    description: str = Field(..., description="Element to hover over")

class SelectAction(BaseModel):
    """Select an option from a dropdown."""
    description: str = Field(..., description="Dropdown element description")
    value: str = Field(..., description="Option to select")
    by: Literal["value", "label", "index"] = Field("value", description="Selection method")

class FinalAnswerAction(BaseModel):
    """Provide final answer and end execution."""
    answer: str = Field(..., description="The complete answer to the user's question")

class NewTabAction(BaseModel):
    """Open a new browser tab."""
    url: Optional[str] = Field(None, description="URL to open in new tab")

class SwitchTabAction(BaseModel):
    """Switch to a different tab."""
    tab_index: int = Field(..., description="Index of tab to switch to")

class CloseTabAction(BaseModel):
    """Close a browser tab."""
    tab_index: Optional[int] = Field(None, description="Tab index to close, None for current")

class GoalAchievedAction(BaseModel):
    """Signal that the goal has been achieved."""
    reasoning: str = Field("", description="Why the goal is considered achieved")


# ==========================================
# Unified Agent Output Model
# ==========================================

# Map action names to their model classes
ACTION_REGISTRY = {
    "navigate": NavigateAction,
    "intelligent_click": ClickAction,
    "intelligent_type": TypeAction,
    "intelligent_extract": ExtractAction,
    "intelligent_wait": WaitAction,
    "intelligent_hover": HoverAction,
    "scroll": ScrollAction,
    "wait": WaitAction,
    "screenshot": ScreenshotAction,
    "hover": HoverAction,
    "select_option": SelectAction,
    "final_answer": FinalAnswerAction,
    "new_tab": NewTabAction,
    "switch_tab": SwitchTabAction,
    "close_tab": CloseTabAction,
    "list_tabs": BaseModel,  # No params needed
    "goal_achieved": GoalAchievedAction,
}


class AgentOutput(BaseModel):
    """
    Validated output from the LLM agent.
    
    Parses the flat JSON format the LLM returns:
    {"action": "navigate", "url": "...", "reasoning": "..."}
    
    into a validated model with type-checked parameters.
    """
    
    # The action type
    action: str = Field(..., description="Action to perform")
    
    # Optional reasoning (LLM explains why)
    reasoning: str = Field("", description="Agent's reasoning for this action")
    
    # Action-specific parameters (validated after parsing)
    params: Optional[BaseModel] = Field(None, exclude=True)
    
    # Raw parameters dict for backward compatibility
    raw_params: dict = Field(default_factory=dict, exclude=True)
    
    class Config:
        arbitrary_types_allowed = True
    
    @model_validator(mode="before")
    @classmethod
    def parse_action_params(cls, values: dict) -> dict:
        """Extract and validate action-specific parameters from flat dict."""
        if not isinstance(values, dict):
            return values
        
        action = values.get("action", "")
        reasoning = values.get("reasoning", "")
        
        # Collect all non-meta fields as raw params
        meta_keys = {"action", "reasoning"}
        raw_params = {k: v for k, v in values.items() if k not in meta_keys}
        
        # Validate against the action's model if registered
        params = None
        action_model = ACTION_REGISTRY.get(action)
        if action_model and action_model is not BaseModel:
            try:
                params = action_model(**raw_params)
            except Exception:
                # Fallback: keep raw params, don't fail validation
                params = None
        
        values["raw_params"] = raw_params
        values["params"] = params
        
        return values
    
    def to_dict(self) -> dict:
        """Convert back to flat dict format for backward compatibility."""
        result = {"action": self.action}
        if self.reasoning:
            result["reasoning"] = self.reasoning
        result.update(self.raw_params)
        return result
    
    def get(self, key: str, default=None):
        """Dict-like access for backward compatibility."""
        if key == "action":
            return self.action
        if key == "reasoning":
            return self.reasoning
        return self.raw_params.get(key, default)
    
    def __getitem__(self, key: str):
        """Dict-like bracket access for backward compatibility."""
        if key == "action":
            return self.action
        if key == "reasoning":
            return self.reasoning
        if key in self.raw_params:
            return self.raw_params[key]
        raise KeyError(key)
    
    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for backward compatibility."""
        return key in {"action", "reasoning"} or key in self.raw_params


def parse_agent_output(raw: dict) -> AgentOutput:
    """
    Parse a raw dict (from LLM JSON) into a validated AgentOutput.
    
    Args:
        raw: Dictionary from LLM response
        
    Returns:
        Validated AgentOutput
        
    Raises:
        ValueError: If action field is missing
    """
    if not isinstance(raw, dict) or "action" not in raw:
        raise ValueError(f"Invalid action format: missing 'action' field in {raw}")
    
    return AgentOutput.model_validate(raw)
