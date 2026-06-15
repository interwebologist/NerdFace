import json
import logging
import os
from pathlib import Path
from typing import cast
from dotenv import load_dotenv
from openai import InternalServerError
from openai.types.chat import ChatCompletionMessageParam
from tools.registry import registry, discover_builtin_tools

from guardrails import create_guardrails, Guardrails
from llm_client import client, DEFAULT_MODEL

logger = logging.getLogger(__name__)

discover_builtin_tools()
load_dotenv(".nerdface/.env")

guardrails: Guardrails = create_guardrails()

model = DEFAULT_MODEL

CHAT_HISTORY: list[ChatCompletionMessageParam] = []

MAX_ITERATIONS = 300


def load_system_prompt() -> str:
    """Load system prompt from environment variable or file."""
    env_prompt = os.getenv("SYSTEM_PROMPT")
    if env_prompt:
        return env_prompt.strip()

    path = Path("prompts/system_prompt.md")
    if path.exists():
        with path.open("r") as f:
            return f.read().strip()
    return ""


def run(prompt: str, max_iterations: int = MAX_ITERATIONS) -> str:
    global CHAT_HISTORY

    if guardrails.is_kill_switch_triggered():
        kill_result = guardrails.trigger_kill_switch()
        return f"ERROR: Kill switch activated. {kill_result}"

    is_blocked, block_msg, block_type = guardrails.validate_input(prompt)
    if is_blocked:
        guardrails.trigger_kill_switch()
        return f"ERROR: Input blocked [{block_type}]: {block_msg}"

    if not CHAT_HISTORY:
        sys_p = load_system_prompt()
        if sys_p:
            msg = cast(ChatCompletionMessageParam, {"role": "system", "content": sys_p})
            CHAT_HISTORY.append(msg)
            logger.debug("Added to CHAT_HISTORY: %s", msg)

    msg = cast(ChatCompletionMessageParam, {"role": "user", "content": prompt})
    CHAT_HISTORY.append(msg)
    logger.debug("Added to CHAT_HISTORY: %s", msg)

    iterations = 0
    while iterations < max_iterations:
        if guardrails.is_kill_switch_triggered():
            kill_result = guardrails.trigger_kill_switch()
            return f"ERROR: Kill switch activated during execution. {kill_result}"

        iterations += 1
        tools = registry.get_definitions(set(registry.get_all_tool_names()), quiet=True)
        logger.debug(
            "LLM REQUEST: %s",
            json.dumps({"messages": CHAT_HISTORY, "tools": tools}, indent=2),
        )
        try:
            res = client.chat.completions.create(
                model=model, messages=CHAT_HISTORY, tools=tools, timeout=360
            )
        except InternalServerError as e:
            logger.error("OpenAI API error: %s", str(e), exc_info=True)
            if "Failed to parse tool call arguments as JSON" in str(e):
                error_msg = (
                    "JSON parsing error: The model returned malformed JSON "
                    "for tool arguments. Please reformat your request."
                )
                msg = cast(
                    ChatCompletionMessageParam,
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "error_tool_call",
                                "type": "function",
                                "function": {
                                    "name": "error_handler",
                                    "arguments": "{}",
                                },
                            }
                        ],
                    },
                )
                CHAT_HISTORY.append(msg)
                logger.debug("Added to CHAT_HISTORY: %s", msg)
                msg = cast(
                    ChatCompletionMessageParam,
                    {
                        "role": "tool",
                        "tool_call_id": "error_tool_call",
                        "content": json.dumps({"error": error_msg}),
                    },
                )
                CHAT_HISTORY.append(msg)
                logger.debug("Added to CHAT_HISTORY: %s", msg)
                return error_msg
            raise
        msg_obj = res.choices[0].message
        logger.debug(
            "LLM RESPONSE: %s",
            json.dumps(msg_obj.model_dump(exclude_none=True), indent=2),
        )

        msg_dict = cast(
            ChatCompletionMessageParam, msg_obj.model_dump(exclude_none=True)
        )
        CHAT_HISTORY.append(msg_dict)
        logger.debug("Added to CHAT_HISTORY: %s", msg_dict)

        if not msg_obj.tool_calls:
            return str(msg_obj.content)

        for call in msg_obj.tool_calls:
            if call.type == "function":
                func_name = call.function.name
                try:
                    args = json.loads(call.function.arguments)
                    out = registry.dispatch(func_name, args)
                    msg = cast(
                        ChatCompletionMessageParam,
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": out,
                        },
                    )
                    CHAT_HISTORY.append(msg)
                    logger.debug("Added to CHAT_HISTORY: %s", msg)
                except Exception as e:
                    logger.error(
                        "Tool execution error for %s: %s",
                        call.id,
                        str(e),
                        exc_info=True,
                    )
                    msg = cast(
                        ChatCompletionMessageParam,
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": f"Error: {str(e)}",
                        },
                    )
                    CHAT_HISTORY.append(msg)
                    logger.debug("Added to CHAT_HISTORY: %s", msg)

    return "Error: Maximum iterations reached without final response."


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run("Run a bash command that fails and outputs a lot of text.")
    logger.info("Agent result: %s", result)
