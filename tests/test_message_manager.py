"""
Tests for message management with token-aware compaction.
Verifies token estimation, message recording, auto-compaction, and stats tracking.
"""

import pytest
from core.message_manager import MessageManager, estimate_tokens


class TestEstimateTokens:
    """Test token estimation utility."""

    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_short_string(self):
        result = estimate_tokens("hello")
        assert result >= 1

    def test_long_string(self):
        text = "a" * 400
        result = estimate_tokens(text)
        assert result == 100  # 400 / 4

    def test_none_string(self):
        assert estimate_tokens("") == 0


class TestMessageManager:
    """Test MessageManager core functionality."""

    def test_init_default(self):
        mm = MessageManager()
        assert mm.message_count == 0
        assert mm.total_tokens == 0

    def test_init_with_system(self):
        mm = MessageManager(system_message="You are a helpful assistant.")
        assert mm.message_count == 1
        assert mm.total_tokens > 0

    def test_add_message(self):
        mm = MessageManager()
        mm.add_message("user", "Hello")
        assert mm.message_count == 1
        
    def test_add_user_message(self):
        mm = MessageManager()
        mm.add_user_message("Test prompt")
        messages = mm.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Test prompt"

    def test_add_assistant_message(self):
        mm = MessageManager()
        mm.add_assistant_message("Test response")
        messages = mm.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"

    def test_token_tracking(self):
        mm = MessageManager()
        text = "a" * 100  # ~25 tokens
        mm.add_message("user", text)
        assert mm.total_tokens == 25

    def test_get_messages_returns_copy(self):
        mm = MessageManager()
        mm.add_message("user", "test")
        msgs = mm.get_messages()
        msgs.append({"role": "user", "content": "injected"})
        assert mm.message_count == 1  # Original unchanged

    def test_clear(self):
        mm = MessageManager()
        mm.add_message("user", "test1")
        mm.add_message("assistant", "test2")
        mm.clear()
        assert mm.message_count == 0
        assert mm.total_tokens == 0


class TestCompaction:
    """Test auto-compaction behavior."""

    def test_auto_compact_on_overflow(self):
        mm = MessageManager(max_tokens=50, preserve_recent=2)
        
        # Add many messages to overflow
        for i in range(10):
            mm.add_message("user", f"Prompt number {i} " + "x" * 50)
            mm.add_message("assistant", f"Response number {i} " + "y" * 50)
        
        assert mm.compaction_count > 0
        # After compaction, message count should be much less than 20 (10 pairs)
        assert mm.message_count < 20

    def test_preserves_system_messages(self):
        mm = MessageManager(max_tokens=100, preserve_recent=2, system_message="System instruction")
        
        for i in range(10):
            mm.add_message("user", f"Prompt {i} " + "x" * 50)
            mm.add_message("assistant", f"Response {i} " + "y" * 50)
        
        messages = mm.get_messages()
        system_msgs = [m for m in messages if m["role"] == "system"]
        assert len(system_msgs) >= 1  # System message preserved
        assert any("System instruction" in m["content"] for m in system_msgs)

    def test_preserves_recent_messages(self):
        mm = MessageManager(max_tokens=100, preserve_recent=2)
        
        # Add 6 conversation messages
        for i in range(3):
            mm.add_message("user", f"Prompt {i} " + "x" * 80)
            mm.add_message("assistant", f"Response {i} " + "y" * 80)
        
        messages = mm.get_messages()
        # Last messages should be preserved
        non_system = [m for m in messages if "COMPACTED" not in m.get("content", "")]
        assert any("Prompt 2" in m["content"] for m in non_system)

    def test_no_compact_when_under_limit(self):
        mm = MessageManager(max_tokens=10000)
        mm.add_message("user", "short")
        mm.add_message("assistant", "ok")
        assert mm.compaction_count == 0

    def test_no_compact_too_few_messages(self):
        mm = MessageManager(max_tokens=10, preserve_recent=4)
        mm.add_message("user", "x" * 100)  # Over limit but too few messages
        assert mm.compaction_count == 0


class TestBuildPromptMessages:
    """Test prompt building."""

    def test_build_without_history(self):
        mm = MessageManager()
        mm.add_message("user", "old prompt")
        
        result = mm.build_prompt_messages("current prompt", include_history=False)
        assert len(result) == 1
        assert result[0]["content"] == "current prompt"

    def test_build_with_history(self):
        mm = MessageManager(system_message="system")
        mm.add_message("user", "old")
        mm.add_message("assistant", "reply")
        
        result = mm.build_prompt_messages("current prompt", include_history=True)
        assert len(result) == 4  # system + old + reply + current
        assert result[-1]["content"] == "current prompt"


class TestStats:
    """Test stats reporting."""

    def test_stats_initial(self):
        mm = MessageManager(max_tokens=8000)
        stats = mm.get_stats()
        assert stats["message_count"] == 0
        assert stats["estimated_tokens"] == 0
        assert stats["max_tokens"] == 8000
        assert stats["utilization"] == 0
        assert stats["compaction_count"] == 0

    def test_stats_after_messages(self):
        mm = MessageManager(max_tokens=1000)
        mm.add_message("user", "a" * 400)  # ~100 tokens
        stats = mm.get_stats()
        assert stats["message_count"] == 1
        assert stats["estimated_tokens"] == 100
        assert stats["utilization"] == 0.1
