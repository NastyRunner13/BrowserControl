import json
import re
from typing import Any, Dict, Optional

def parse_json_safely(text: str) -> Optional[Any]:
    """Safely parse JSON from text, handling markdown code blocks and arrays."""
    try:
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        # Try direct parse first (handles both arrays and objects)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON array first (for planner output like [{...}])
        array_match = re.search(r'\[.*\]', text, re.DOTALL)
        if array_match:
            try:
                return json.loads(array_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object
        obj_match = re.search(r'\{.*\}', text, re.DOTALL)
        if obj_match:
            return json.loads(obj_match.group(0))
        
        return None
    except json.JSONDecodeError:
        return None

def extract_number(text: str) -> Optional[int]:
    """Extract first number from text."""
    match = re.search(r'-?\d+', text)
    return int(match.group(0)) if match else None