"""
Tests for plan tracking models.
Verifies plan creation, advancement, replanning, stall detection, and prompt formatting.
"""

import pytest
from models.plan import AgentPlan, PlanItem


class TestPlanItem:
    """Test individual plan item behavior."""

    def test_default_status(self):
        item = PlanItem(text="Navigate to Google")
        assert item.status == "pending"

    def test_custom_status(self):
        item = PlanItem(text="Search", status="done")
        assert item.status == "done"

    def test_valid_statuses(self):
        for status in ["pending", "current", "done", "failed", "skipped"]:
            item = PlanItem(text="test", status=status)
            assert item.status == status


class TestAgentPlan:
    """Test AgentPlan state machine."""

    @pytest.fixture
    def sample_plan(self):
        return AgentPlan.from_text_list([
            "Navigate to Google",
            "Search for Python tutorials",
            "Extract top 3 results",
            "Provide final answer",
        ], step_number=1)

    def test_creation(self, sample_plan):
        assert len(sample_plan.items) == 4
        assert sample_plan.items[0].status == "current"
        assert sample_plan.items[1].status == "pending"
        assert sample_plan.current_index == 0
        assert sample_plan.created_at_step == 1

    def test_advance(self, sample_plan):
        sample_plan.advance()
        assert sample_plan.items[0].status == "done"
        assert sample_plan.items[1].status == "current"
        assert sample_plan.current_index == 1

    def test_advance_multiple(self, sample_plan):
        sample_plan.advance()
        sample_plan.advance()
        assert sample_plan.items[0].status == "done"
        assert sample_plan.items[1].status == "done"
        assert sample_plan.items[2].status == "current"
        assert sample_plan.current_index == 2

    def test_advance_past_end(self, sample_plan):
        for _ in range(10):  # More than total items
            sample_plan.advance()
        assert sample_plan.current_index == 4  # Past last index
        assert all(item.status == "done" for item in sample_plan.items)

    def test_mark_current_failed(self, sample_plan):
        sample_plan.mark_current_failed()
        assert sample_plan.items[0].status == "failed"

    def test_skip_current(self, sample_plan):
        sample_plan.skip_current()
        assert sample_plan.items[0].status == "skipped"
        assert sample_plan.items[1].status == "current"

    def test_is_complete(self, sample_plan):
        assert not sample_plan.is_complete
        for _ in range(4):
            sample_plan.advance()
        assert sample_plan.is_complete

    def test_is_complete_with_failures(self, sample_plan):
        sample_plan.mark_current_failed()
        for _ in range(4):
            sample_plan.advance()
        assert sample_plan.is_complete

    def test_progress_ratio(self, sample_plan):
        assert sample_plan.progress_ratio == 0.0
        sample_plan.advance()
        assert sample_plan.progress_ratio == 0.25
        sample_plan.advance()
        assert sample_plan.progress_ratio == 0.5

    def test_progress_ratio_empty(self):
        plan = AgentPlan()
        assert plan.progress_ratio == 0.0

    def test_current_step_text(self, sample_plan):
        assert sample_plan.current_step_text == "Navigate to Google"
        sample_plan.advance()
        assert sample_plan.current_step_text == "Search for Python tutorials"

    def test_current_step_text_complete(self, sample_plan):
        for _ in range(4):
            sample_plan.advance()
        assert sample_plan.current_step_text is None


class TestPlanUpdate:
    """Test plan revision behavior."""

    def test_update_preserves_done(self):
        plan = AgentPlan.from_text_list(["Step A", "Step B", "Step C"])
        plan.advance()  # A -> done, B -> current
        
        plan.update_plan(["New Step X", "New Step Y"], step_number=3)
        
        # A should be preserved as done
        assert plan.items[0].status == "done"
        assert plan.items[0].text == "Step A"
        # New items added
        assert plan.items[1].text == "New Step X"
        assert plan.items[1].status == "current"
        assert plan.items[2].text == "New Step Y"
        assert plan.revision_count == 1

    def test_update_increments_revision(self):
        plan = AgentPlan.from_text_list(["Step A"])
        plan.update_plan(["Step B"], step_number=2)
        plan.update_plan(["Step C"], step_number=3)
        assert plan.revision_count == 2

    def test_update_preserves_failed(self):
        plan = AgentPlan.from_text_list(["Step A", "Step B"])
        plan.mark_current_failed()
        
        plan.update_plan(["Retry Step A"], step_number=2)
        
        assert plan.items[0].status == "failed"
        assert plan.items[0].text == "Step A"
        assert plan.items[1].text == "Retry Step A"


class TestPlanPromptFormat:
    """Test prompt formatting for LLM injection."""

    def test_format_empty(self):
        plan = AgentPlan()
        result = plan.format_for_prompt()
        assert "No plan" in result

    def test_format_with_items(self):
        plan = AgentPlan.from_text_list(["Navigate", "Search", "Extract"])
        result = plan.format_for_prompt()
        
        assert "[>]" in result  # Current marker
        assert "[ ]" in result  # Pending marker
        assert "CURRENT" in result
        assert "Navigate" in result
        assert "progress: 0%" in result

    def test_format_with_progress(self):
        plan = AgentPlan.from_text_list(["Step A", "Step B"])
        plan.advance()
        result = plan.format_for_prompt()
        
        assert "[x]" in result  # Done marker
        assert "progress: 50%" in result

    def test_format_with_failed(self):
        plan = AgentPlan.from_text_list(["Step A", "Step B"])
        plan.mark_current_failed()
        result = plan.format_for_prompt()
        
        assert "[!]" in result  # Failed marker

    def test_format_revision_count(self):
        plan = AgentPlan.from_text_list(["Step A"])
        plan.update_plan(["Step B"], step_number=2)
        result = plan.format_for_prompt()
        
        assert "revision #1" in result
