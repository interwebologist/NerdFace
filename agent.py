import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from openai import OpenAI, APIConnectionError
from openinference.instrumentation.openai import OpenAIInstrumentor
from phoenix.otel import register, using_session
from tools.registry import registry, discover_builtin_tools
from guardrails import create_guardrails, Guardrails
from tools.memory.store import MemoryStore

logger = logging.getLogger(__name__)

PHOENIX_ENDPOINT = "http://127.0.0.1:6006/v1/traces"

tracer_provider = register(
    endpoint=PHOENIX_ENDPOINT,
    project_name="nerdface",
    set_global_tracer_provider=False,
    auto_instrument=True,
)

tracer = tracer_provider.get_tracer(__name__)

OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

discover_builtin_tools()

load_dotenv(".nerdface/.env")

client = OpenAI(
    base_url=os.getenv("OPENAI_API_BASE", "http://192.168.1.33:8080/v1"),
    api_key=os.getenv("OPENAI_API_KEY", "not-needed"),
)
model = os.getenv("MODEL_NAME", "NVIDIA-Nemotron-3-Super-120B-A12B-UD-Q4_K_XL.gguf")


class Agent:
    def __init__(self):
        self.CHAT_HISTORY: list[dict[str, Any]] = []
        self.load_system_prompt()
        self.MAX_ITERATIONS = 30
        self.session_id = str(uuid.uuid4())[-6:]
        self.guardrails: Guardrails = create_guardrails()

    def load_system_prompt(self) -> None:
        """Load system prompt as first chat history message."""
        path = Path("prompts/system_prompt.md")
        if path.exists():
            self.CHAT_HISTORY.insert(
                0, {"role": "system", "content": path.read_text().strip()}
            )

    def guardrails_checks(self, prompt: str) -> tuple[bool, str]:
        """Validate input against guardrails. Returns (is_blocked, message)."""
        is_blocked, block_msg, block_type = self.guardrails.validate_input(prompt)

        if self.guardrails.is_kill_switch_triggered():
            kill_result = self.guardrails.trigger_kill_switch()
            return (True, f"ERROR: Kill switch activated. {kill_result}")

        if is_blocked:
            self.guardrails.trigger_kill_switch()
            return (True, f"ERROR: Input blocked [{block_type}]: {block_msg}")

        return (False, "Guardrail Checks Passed")

    def _add_message(self, msg: dict) -> None:
        """Add message to chat history with logging."""
        self.CHAT_HISTORY.append(msg)
        logger.debug("Added to CHAT_HISTORY: %s", json.dumps(msg, indent=2))

    def _add_error_tool_call(self, error_msg: str) -> None:
        """Add error tool call to history for JSON parse failures."""
        msg = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "error_tool_call",
                    "type": "function",
                    "function": {"name": "error_handler", "arguments": "{}"},
                }
            ],
        }
        self._add_message(msg)

        msg = {
            "role": "tool",
            "tool_call_id": "error_tool_call",
            "content": json.dumps({"error": error_msg}),
        }
        self._add_message(msg)

    def _handle_llm_error(self, error: Exception) -> None:
        """Handle LLM API errors and update chat history."""
        if "Failed to parse tool call arguments as JSON" in str(error):
            error_msg = "JSON parsing error: The model returned malformed JSON for tool arguments."
            self._add_error_tool_call(error_msg)
        else:
            logger.error("OpenAI API client error: %s", error, exc_info=True)

    def _handle_tool_error(self, call, error: Exception) -> dict:
        """Create error message for failed tool execution."""
        logger.error("Tool execution error for %s: %s", call.id, error, exc_info=True)
        return {
            "role": "tool",
            "tool_call_id": call.id,
            "content": f"Error: {str(error)}",
        }

    def _call_llm(self, tools: list[dict]) -> dict:
        """Make LLM call and return response message."""
        try:
            res = client.chat.completions.create(
                model=model,
                messages=self.CHAT_HISTORY,
                tools=tools,
                timeout=360,
            )
            return res.choices[0].message
        except APIConnectionError:
            logger.error("OpenAI API Connection error. Is LLM server up?")
            raise
        except Exception as e:
            self._handle_llm_error(e)
            raise

    def _execute_tool(self, call) -> str:
        """Execute a single tool call and return the output."""
        func_name = call.function.name
        args = json.loads(call.function.arguments)

        with tracer.start_as_current_span(
            f"tool.{func_name}",
            openinference_span_kind="tool",
        ) as span:
            span.set_input(args)
            output = registry.dispatch(func_name, args)
            span.set_output(output)

        return output

    def _handle_kill_switch(self) -> str:
        """Handle kill switch activation and return error message."""
        kill_result = self.guardrails.trigger_kill_switch()
        return f"ERROR: Kill switch activated during execution. {kill_result}"

    def _log_llm_request(self, tools: list[dict]) -> None:
        """Log LLM request details."""
        logger.debug(
            "LLM REQUEST: %s",
            json.dumps(
                {"messages": self.CHAT_HISTORY, "tools": tools},
                indent=2,
            ),
        )

    @tracer.agent
    def run(self, prompt: str) -> str:
        with using_session(self.session_id):
            self._add_message({"role": "user", "content": prompt})

            for _ in range(self.MAX_ITERATIONS):
                if self.guardrails.is_kill_switch_triggered():
                    return self._handle_kill_switch()

                tools = registry.get_definitions(
                    set(registry.get_all_tool_names()), quiet=True
                )
                self._log_llm_request(tools)

                msg = self._call_llm(tools)
                self._add_message(msg.model_dump(exclude_none=True))

                if not msg.tool_calls:
                    return str(msg.content)

                for call in msg.tool_calls:
                    if call.type == "function":
                        try:
                            output = self._execute_tool(call)
                            tool_msg = {
                                "role": "tool",
                                "tool_call_id": call.id,
                                "content": output,
                            }
                            self._add_message(tool_msg)
                        except Exception as e:
                            tool_msg = self._handle_tool_error(call, e)
                            self._add_message(tool_msg)

            return "Error: Maximum iterations reached without final response."

    def on_session_end(self) -> None:
        """Auto-extract facts from conversation at session end."""
        try:
            store = MemoryStore(db_path="~/.skunk/state.db")
            extracted = store.auto_extract_facts(self.CHAT_HISTORY)
            if extracted > 0:
                logger.info("Auto-extracted %d facts from session", extracted)
        except Exception as e:
            logger.error("Auto-extraction failed: %s", e, exc_info=True)


if __name__ == "__main__":
    agent = Agent()
    result = agent.run("Run a bash command that fails and outputs a lot of text.")
    logger.info("Agent result: %s", result)
