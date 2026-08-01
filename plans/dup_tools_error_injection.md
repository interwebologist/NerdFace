# Duplicate Tool Call Detection & Error Injection

## Problem
Agent loops indefinitely re-calling the same tools with the same arguments (e.g., re-fetching 404 URLs). The LLM never learns its tool calls are duplicates because the results are appended to CHAT_HISTORY without any deduplication signal.

## Solution
Track executed tool calls in a set. Before executing each tool call, check if the same (tool_name, arguments) pair was already executed in this session. If duplicate, inject an error message into CHAT_HISTORY instead of re-executing.

## Steps

1. **Add `_seen_tool_calls` set to `Agent.__init__`** (`agent.py:40-44`)
   - Initialize `self._seen_tool_calls: set[str] = set()`

2. **Add `_tool_call_signature` helper method** (`agent.py:165`)
   - Takes `func_name` and `call` arguments
   - Returns a canonical string like `web_fetch|{"url":"https://example.com"}`
   - Use `json.dumps` with `sort_keys=True` for stable hashing

3. **Modify `_execute_tool_calls`** (`agent.py:145-163`)
   - For each tool call, compute signature
   - If signature in `_seen_tool_calls`: append a tool error message to CHAT_HISTORY with content like `{"error": "Duplicate tool call: web_fetch with these arguments was already executed. Try a different approach."}`
   - If not duplicate: add to `_seen_tool_calls`, proceed with normal dispatch

4. **Clear `_seen_tool_calls` on new conversation** (`agent.py:91-95`)
   - In `run()`, when a new user message starts, clear the set so cross-session dedup doesn't block legitimate repeated calls

5. **Test**
   - Run `python agent.py` and verify the loop is broken
   - Check that legitimate repeated tool calls (different args) still work
