"""
Task Context for storing and managing data during task execution.

Provides a centralized context for storing extracted data, tracking visited URLs,
and building final responses from accumulated information.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class TaskContext:
    """
    Stores data extracted and collected during task execution.
    
    Used to:
    - Store data extracted via intelligent_extract
    - Track visited URLs and actions taken
    - Build comprehensive final answers from accumulated data
    - Provide memory across action steps
    """
    
    # Extracted data storage - key is the description, value is the extracted content
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    
    # URLs visited during task execution
    visited_urls: List[str] = field(default_factory=list)
    
    # Screenshots taken
    screenshots: List[str] = field(default_factory=list)
    
    # Action history summary
    actions_taken: List[str] = field(default_factory=list)
    
    # Final answer (if set via final_answer action)
    final_answer: Optional[str] = None
    
    # User's original goal/request
    original_goal: str = ""
    
    def store_extracted_data(self, key: str, value: Any) -> None:
        """
        Store extracted data with a key.
        
        Args:
            key: Identifier/description for the data
            value: The extracted value
        """
        self.extracted_data[key] = value
        logger.debug(f"Stored extracted data: {key} = {str(value)[:100]}")
    
    def get_extracted_data(self, key: str) -> Optional[Any]:
        """Get extracted data by key."""
        return self.extracted_data.get(key)
    
    def add_visited_url(self, url: str) -> None:
        """Record a visited URL."""
        if url not in self.visited_urls:
            self.visited_urls.append(url)
    
    def add_screenshot(self, path: str) -> None:
        """Record a screenshot path."""
        self.screenshots.append(path)
    
    def add_action(self, action_description: str) -> None:
        """Record an action taken."""
        self.actions_taken.append(action_description)
    
    def set_final_answer(self, answer: str) -> None:
        """Set the final answer to return to user."""
        self.final_answer = answer
        logger.info(f"Final answer set: {answer[:200]}")
    
    def build_summary(self) -> Dict[str, Any]:
        """
        Build a comprehensive summary of the task execution.
        
        Returns:
            Dictionary containing all collected data and context
        """
        return {
            "goal": self.original_goal,
            "final_answer": self.final_answer,
            "extracted_data": self.extracted_data,
            "visited_urls": self.visited_urls,
            "screenshots": self.screenshots,
            "actions_count": len(self.actions_taken),
            "actions": self.actions_taken[-10:]  # Last 10 actions
        }
    
    def get_context_for_llm(self) -> str:
        """
        Get a formatted context string for LLM prompts.
        
        Returns:
            Formatted string with extracted data for LLM context
        """
        if not self.extracted_data:
            return ""
        
        lines = ["PREVIOUSLY EXTRACTED DATA:"]
        for key, value in self.extracted_data.items():
            value_str = str(value)[:200]
            lines.append(f"  - {key}: {value_str}")
        
        return "\n".join(lines)
    
    def has_data_for_answer(self) -> bool:
        """Check if there's enough data to formulate an answer."""
        return bool(self.extracted_data) or bool(self.final_answer)
    
    def clear(self) -> None:
        """Clear all stored data."""
        self.extracted_data.clear()
        self.visited_urls.clear()
        self.screenshots.clear()
        self.actions_taken.clear()
        self.final_answer = None
        logger.debug("Task context cleared")
