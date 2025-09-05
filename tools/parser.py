import re
import json
import logging

def parse_tool_response(tool_response: str) -> list:
    """Parse XML-formatted tool calls"""
    if tool_response.strip() == "<tool_call>None</tool_call>":
        return []
        
    tool_calls = []
    # Allow whitespace/newlines between tags and JSON with DOTALL
    pattern = r"<tool>\s*(.*?)\s*</tool>\s*<arguments>\s*(.*?)\s*</arguments>"
    matches = re.findall(pattern, tool_response, flags=re.DOTALL)
    
    for match in matches:
        try:
            tool_calls.append({
                "tool_name": match[0],
                "arguments": json.loads(match[1])
            })
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing tool arguments: {str(e)}")
            
    return tool_calls
