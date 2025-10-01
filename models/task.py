from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class IntelligentParallelTask:
    """Enhanced parallel task with intelligent action support."""
    task_id: str
    name: str
    steps: List[Dict[str, Any]]
    priority: int = 1
    timeout: int = 300
    retry_count: int = 3
    depends_on: Optional[List[str]] = None
    context: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'steps': self.steps,
            'priority': self.priority,
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'depends_on': self.depends_on,
            'context': self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IntelligentParallelTask':
        """Create task from dictionary."""
        return cls(
            task_id=data['task_id'],
            name=data['name'],
            steps=data['steps'],
            priority=data.get('priority', 1),
            timeout=data.get('timeout', 300),
            retry_count=data.get('retry_count', 3),
            depends_on=data.get('depends_on'),
            context=data.get('context', '')
        )