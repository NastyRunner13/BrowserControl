"""
Plan Tracking Models for BrowserAgent.

Provides step-level progress tracking for the dynamic agent, allowing it 
to maintain an evolving plan it can reference and update throughout task execution.
Inspired by browser-use's plan tracking pattern.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class PlanItem(BaseModel):
    """Individual step in the agent's plan."""
    text: str = Field(..., description="Description of this plan step")
    status: Literal["pending", "current", "done", "failed", "skipped"] = Field(
        "pending", description="Current status of this step"
    )


class AgentPlan(BaseModel):
    """
    Evolving plan that the agent maintains during task execution.
    
    The plan is created after the first observation and updated
    as the agent progresses through steps.
    """
    items: List[PlanItem] = Field(default_factory=list)
    current_index: int = Field(0, description="Index of the current active step")
    created_at_step: int = Field(0, description="Agent step when plan was created")
    revision_count: int = Field(0, description="Number of times the plan was revised")
    
    def advance(self) -> None:
        """Mark current step as done and move to next pending step."""
        if self.items and 0 <= self.current_index < len(self.items):
            self.items[self.current_index].status = "done"
        
        # Find next pending step
        for i in range(self.current_index + 1, len(self.items)):
            if self.items[i].status == "pending":
                self.current_index = i
                self.items[i].status = "current"
                return
        
        # No more pending steps
        self.current_index = len(self.items)
    
    def mark_current_failed(self) -> None:
        """Mark current step as failed."""
        if self.items and 0 <= self.current_index < len(self.items):
            self.items[self.current_index].status = "failed"
    
    def skip_current(self) -> None:
        """Skip current step and move to next."""
        if self.items and 0 <= self.current_index < len(self.items):
            self.items[self.current_index].status = "skipped"
        
        # Find next pending step
        for i in range(self.current_index + 1, len(self.items)):
            if self.items[i].status == "pending":
                self.current_index = i
                self.items[i].status = "current"
                return
        
        # No more pending steps
        self.current_index = len(self.items)
    
    def update_plan(self, new_items: List[str], step_number: int) -> None:
        """
        Replace remaining pending items with new plan.
        Preserves already done/failed items.
        """
        # Keep completed items
        preserved = [item for item in self.items if item.status in ("done", "failed")]
        
        # Add new items
        new_plan_items = [PlanItem(text=text.strip()) for text in new_items if text.strip()]
        
        self.items = preserved + new_plan_items
        self.revision_count += 1
        
        # Set current to first pending
        for i, item in enumerate(self.items):
            if item.status == "pending":
                self.current_index = i
                self.items[i].status = "current"
                return
        
        self.current_index = len(self.items)
    
    @property
    def is_complete(self) -> bool:
        """Check if all steps are done, failed, or skipped."""
        return all(item.status in ("done", "failed", "skipped") for item in self.items)
    
    @property
    def progress_ratio(self) -> float:
        """Fraction of steps completed (0.0 to 1.0)."""
        if not self.items:
            return 0.0
        done = sum(1 for item in self.items if item.status in ("done", "skipped"))
        return done / len(self.items)
    
    @property
    def current_step_text(self) -> Optional[str]:
        """Get the text of the current step, or None if plan is complete."""
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index].text
        return None
    
    def format_for_prompt(self) -> str:
        """
        Format plan with status markers for injection into LLM prompt.
        
        Example output:
            [x] 0: Navigate to Google
            [>] 1: Search for Python tutorials  ← CURRENT
            [ ] 2: Extract top 3 results
            [ ] 3: Provide final answer
        """
        if not self.items:
            return "No plan created yet."
        
        lines = []
        status_markers = {
            "done": "[x]",
            "current": "[>]",
            "pending": "[ ]",
            "failed": "[!]",
            "skipped": "[-]",
        }
        
        for i, item in enumerate(self.items):
            marker = status_markers.get(item.status, "[ ]")
            line = f"  {marker} {i}: {item.text}"
            if item.status == "current":
                line += "  ← CURRENT"
            lines.append(line)
        
        progress = f"{int(self.progress_ratio * 100)}%"
        header = f"PLAN (progress: {progress}, revision #{self.revision_count}):"
        return header + "\n" + "\n".join(lines)
    
    @classmethod
    def from_text_list(cls, items: List[str], step_number: int = 0) -> "AgentPlan":
        """Create a new plan from a list of step descriptions."""
        plan_items = []
        for i, text in enumerate(items):
            status = "current" if i == 0 else "pending"
            plan_items.append(PlanItem(text=text.strip(), status=status))
        
        return cls(
            items=plan_items,
            current_index=0,
            created_at_step=step_number,
            revision_count=0,
        )
