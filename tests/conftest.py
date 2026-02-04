"""Pytest configuration and fixtures."""
import json
import re
from pathlib import Path


def load_fixture(filename):
    """Load a fixture file.
    
    Handles JSON files from Ökofen API which may contain control characters
    (newlines, tabs) in string values, which is technically invalid JSON.
    """
    path = Path(__file__).parent / "fixtures" / filename
    
    # Read as binary first to handle encoding properly
    with open(path, "rb") as f:
        data = f.read()
    
    # Try UTF-8 first, fallback to iso-8859-1 for files with special encoding
    # Files like api_response_base_da.json use iso-8859-1
    try:
        str_response = data.decode("utf-8")
    except UnicodeDecodeError:
        str_response = data.decode("iso-8859-1", "ignore")
    
    # Hotfix for pellematic update 4.02 (invalid json)
    str_response = str_response.replace("L_statetext:", 'L_statetext":')
    
    # Fix for control characters (newlines, tabs) in string values from Ökofen API
    # The API sometimes returns error messages with actual newlines in JSON strings
    # which is invalid JSON. We need to escape them before parsing.
    def escape_control_chars(match):
        string_content = match.group(1)
        # Escape newlines, tabs, carriage returns
        string_content = string_content.replace('\n', '\\n')
        string_content = string_content.replace('\r', '\\r')
        string_content = string_content.replace('\t', '\\t')
        return f'"{string_content}"'
    
    # Match strings in JSON (handling escaped quotes)
    str_response = re.sub(r'"((?:[^"\\]|\\.)*)"', escape_control_chars, str_response)
    
    return json.loads(str_response, strict=False)
