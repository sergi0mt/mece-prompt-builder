"""Robust JSON extraction and repair — deepresearch pattern.
Handles truncated responses, thinking blocks, multiple fence variants."""
from __future__ import annotations
import json
import re


def clean_json_response(text: str) -> dict | list | None:
    """Extract and repair JSON from an LLM response.

    Tries multiple strategies:
    1. Extract from ```json fences
    2. Extract from ``` fences (any language)
    3. Find raw JSON structure in text
    4. Repair truncated JSON (close open brackets)
    """
    # Strip thinking blocks (Claude extended thinking)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    text = re.sub(r'<reflection>.*?</reflection>', '', text, flags=re.DOTALL)

    # Strategy 1: ```json fences
    matches = re.findall(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
    for match in matches:
        result = _try_parse(match.strip())
        if result is not None:
            return result

    # Strategy 2: Any ``` fence
    matches = re.findall(r'```\w*\s*\n(.*?)\n```', text, re.DOTALL)
    for match in matches:
        result = _try_parse(match.strip())
        if result is not None:
            return result

    # Strategy 3: Find raw JSON in text (first { or [)
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        idx = text.find(start_char)
        if idx >= 0:
            candidate = text[idx:]
            result = _try_parse(candidate)
            if result is not None:
                return result
            result = _try_parse_balanced(candidate, start_char, end_char)
            if result is not None:
                return result
            # Try repair on the candidate
            result = _try_repair(candidate)
            if result is not None:
                return result

    # Strategy 4: Repair truncated JSON from fences
    for match in re.findall(r'```(?:json)?\s*\n(.*)', text, re.DOTALL):
        cleaned = match.rstrip('`').rstrip()
        result = _try_repair(cleaned)
        if result is not None:
            return result

    return None


def _try_parse(text: str) -> dict | list | None:
    """Try to parse JSON, return None on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _try_parse_balanced(text: str, open_char: str, close_char: str) -> dict | list | None:
    """Find the balanced closing bracket and try to parse."""
    depth = 0
    in_string = False
    escape_next = False

    for i, c in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if c == '\\':
            escape_next = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == open_char:
            depth += 1
        elif c == close_char:
            depth -= 1
            if depth == 0:
                return _try_parse(text[:i + 1])
    return None


def _try_repair(text: str) -> dict | list | None:
    """Try to repair truncated JSON by closing open brackets."""
    # Fix literal newlines inside strings
    text = re.sub(r'(?<!\\)\n(?=[^"]*"[^"]*$)', '\\n', text)

    # Count open/close brackets
    opens = text.count('{') + text.count('[')
    closes = text.count('}') + text.count(']')

    if opens <= closes:
        return _try_parse(text)

    # Close unterminated string
    in_string = False
    for c in text:
        if c == '"' and (not text or text[text.index(c) - 1:text.index(c)] != '\\'):
            in_string = not in_string
    if in_string:
        text += '"'

    # Close open brackets/braces
    stack = []
    in_str = False
    esc = False
    for c in text:
        if esc:
            esc = False
            continue
        if c == '\\':
            esc = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c in ('{', '['):
            stack.append('}' if c == '{' else ']')
        elif c in ('}', ']'):
            if stack:
                stack.pop()

    # Remove trailing comma before closing
    text = re.sub(r',\s*$', '', text)

    # Append missing closers
    text += ''.join(reversed(stack))

    return _try_parse(text)
