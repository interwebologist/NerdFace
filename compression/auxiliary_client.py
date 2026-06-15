"""Auxiliary LLM client for compression tasks."""

import logging
from openai.types.chat import ChatCompletionMessageParam
from llm_client import client, DEFAULT_MODEL

logger = logging.getLogger(__name__)


def call_llm(
    messages: list[ChatCompletionMessageParam],
    model: str | None = None,
    max_tokens: int | None = None,
) -> str:
    """Call LLM and return response content.

    Args:
        messages: List of message dicts
        model: Model name (uses default if None)
        max_tokens: Maximum tokens to generate

    Returns:
        LLM response content
    """
    model_name = model or DEFAULT_MODEL

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise
