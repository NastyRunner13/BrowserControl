import json
import re
from typing import Any, Dict, Optional

def parse_json_safely(text: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON from text, handling markdown code blocks."""
    try:
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        # Try to find JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        
        return json.loads(text)
    except json.JSONDecodeError:
        return None

def extract_number(text: str) -> Optional[int]:
    """Extract first number from text."""
    match = re.search(r'-?\d+', text)
    return int(match.group(0)) if match else None