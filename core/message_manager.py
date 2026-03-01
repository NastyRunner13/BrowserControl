"""
Message Manager for BrowserAgent.

Handles intelligent message history management with token-aware compaction
to prevent context overflow during long-running agent sessions.
Inspired by browser-use's MessageManager pattern.
"""

import re
from typing import List, Dict, Any, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for a string.
    
    Uses a simple heuristic (~4 characters per token for English).
    This avoids requiring tiktoken as a dependency.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


class MessageManager:
    """
    Manages LLM message history with token-aware compaction.
    
    Prevents context overflow by:
    1. Tracking estimated token usage per message
    2. Compacting old messages when approaching limits
    3. Preserving the most relevant context (system + recent actions + goal)
    
    Compaction strategy:
    - System message is always preserved
    - Recent N messages are preserved in full
    - Older messages are summarized into a compact digest
    """
    
    def __init__(
        self,
        max_tokens: int = 8000,
        preserve_recent: int = 4,
        system_message: Optional[str] = None,
    ):
        """
        Args:
            max_tokens: Maximum estimated tokens before compaction triggers
            preserve_recent: Number of recent message pairs to preserve in full
            system_message: Optional system message (always preserved)
        """
        self.max_tokens = max_tokens
        self.preserve_recent = preserve_recent
        self._messages: List[Dict[str, str]] = []
        self._token_counts: List[int] = []
        self._total_tokens: int = 0
        self._compaction_count: int = 0
        
        if system_message:
            self.add_message("system", system_message)
    
    @property
    def total_tokens(self) -> int:
        """Current estimated total token count."""
        return self._total_tokens
    
    @property
    def message_count(self) -> int:
        """Number of messages in history."""
        return len(self._messages)
    
    @property
    def compaction_count(self) -> int:
        """Number of times compaction has been performed."""
        return self._compaction_count
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the history.
        
        Automatically triggers compaction if token limit is exceeded.
        """
        tokens = estimate_tokens(content)
        self._messages.append({"role": role, "content": content})
        self._token_counts.append(tokens)
        self._total_tokens += tokens
        
        # Auto-compact if over limit
        if self._total_tokens > self.max_tokens:
            self.compact()
    
    def add_user_message(self, content: str) -> None:
        """Add a user message."""
        self.add_message("user", content)
    
    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message."""
        self.add_message("assistant", content)
    
    def get_messages(self) -> List[Dict[str, str]]:
        """Get the current message history."""
        return list(self._messages)
    
    def compact(self) -> None:
        """
        Compact message history to stay within token limits.
        
        Strategy:
        1. Always preserve system messages
        2. Always preserve the last N message pairs
        3. Summarize everything in between into a digest
        """
        if len(self._messages) <= self.preserve_recent + 1:
            # Too few messages to compact
            return
        
        # Separate system messages from conversation
        system_msgs = []
        conversation_msgs = []
        system_tokens = 0
        
        for i, msg in enumerate(self._messages):
            if msg["role"] == "system":
                system_msgs.append(msg)
                system_tokens += self._token_counts[i]
            else:
                conversation_msgs.append((msg, self._token_counts[i]))
        
        if len(conversation_msgs) <= self.preserve_recent:
            return
        
        # Split into old (to summarize) and recent (to preserve)
        split_point = len(conversation_msgs) - self.preserve_recent
        old_msgs = conversation_msgs[:split_point]
        recent_msgs = conversation_msgs[split_point:]
        
        # Create digest of old messages
        digest_parts = []
        for msg, _ in old_msgs:
            role = msg["role"]
            content = msg["content"]
            
            # Truncate individual old messages aggressively
            if len(content) > 200:
                content = content[:150] + "...[truncated]"
            
            digest_parts.append(f"[{role}]: {content}")
        
        digest = "COMPACTED HISTORY:\n" + "\n".join(digest_parts)
        digest_tokens = estimate_tokens(digest)
        
        # Rebuild message list
        self._messages = system_msgs.copy()
        self._token_counts = [system_tokens] if system_msgs else []
        
        if system_msgs:
            # Adjust: we stored system_tokens as a total, fix per-message
            self._token_counts = [estimate_tokens(m["content"]) for m in system_msgs]
        
        # Add digest as a system message
        self._messages.append({"role": "system", "content": digest})
        self._token_counts.append(digest_tokens)
        
        # Add preserved recent messages
        for msg, tokens in recent_msgs:
            self._messages.append(msg)
            self._token_counts.append(tokens)
        
        # Recalculate total
        self._total_tokens = sum(self._token_counts)
        self._compaction_count += 1
        
        logger.info(
            f"Message history compacted (#{self._compaction_count}): "
            f"{len(old_msgs)} old messages → digest, "
            f"{len(recent_msgs)} recent preserved, "
            f"~{self._total_tokens} tokens"
        )
    
    def build_prompt_messages(
        self,
        current_prompt: str,
        include_history: bool = True,
    ) -> List[Dict[str, str]]:
        """
        Build the full message list for an LLM call.
        
        Args:
            current_prompt: The current user prompt to append
            include_history: Whether to include message history
            
        Returns:
            List of message dicts ready for LLM invocation
        """
        if not include_history:
            return [{"role": "user", "content": current_prompt}]
        
        messages = self.get_messages()
        messages.append({"role": "user", "content": current_prompt})
        return messages
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the message history."""
        return {
            "message_count": len(self._messages),
            "estimated_tokens": self._total_tokens,
            "max_tokens": self.max_tokens,
            "utilization": round(self._total_tokens / self.max_tokens, 2) if self.max_tokens > 0 else 0,
            "compaction_count": self._compaction_count,
        }
    
    def clear(self) -> None:
        """Clear all messages."""
        self._messages.clear()
        self._token_counts.clear()
        self._total_tokens = 0
