import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from openai import OpenAI, InternalServerError, APIConnectionError
from openinference.instrumentation.openai import OpenAIInstrumentor
from phoenix.otel import register, using_session
from tools.registry import registry, discover_builtin_tools
from guardrails import create_guardrails, Guardrails
from tools.memory.store import MemoryStore

logger = logging.getLogger(__name__)

# Configure Phoenix tracer to send traces to local instance
PHOENIX_ENDPOINT = "http://127.0.0.1:6006/v1/traces"

tracer_provider = register(
    endpoint=PHOENIX_ENDPOINT,
    project_name="nerdface",
    set_global_tracer_provider=False,
    auto_instrument=True
)

tracer = tracer_provider.get_tracer(__name__)

# Instrument OpenAI with our tracer provider. This catches llm reqs with 
OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

discover_builtin_tools()

load_dotenv(".nerdface/.env")

guardrails: Guardrails = create_guardrails()


client = OpenAI(
    base_url=os.getenv("OPENAI_API_BASE", "http://192.168.1.33:8080/v1"),
    api_key=os.getenv("OPENAI_API_KEY", "not-needed"),
)
model = os.getenv("MODEL_NAME", "NVIDIA-Nemotron-3-Super-120B-A12B-UD-Q4_K_XL.gguf")

class Agent():

    def __init__(self):
        self.CHAT_HISTORY: list[dict[str, Any]] = []
        self.MAX_ITERATIONS = 30
        self.session_id = str(uuid.uuid4())[-6:]

    def load_system_prompt(self) -> str:
        """Load system prompt from environment variable or file."""
        #env_prompt = os.getenv("SYSTEM_PROMPT")
        #if env_prompt:
        #    return env_prompt.strip()

        path = Path("prompts/system_prompt.md")
        if path.exists():
            logging.debug("System Prompt Exists At %s", path)
            with path.open("r") as f:
                return f.read().strip()
        else:
            logging.debug("No system prompt loading from %s", path)
            return ""


    @tracer.agent
    def run(self, prompt: str) -> str:
        max_iterations = self.MAX_ITERATIONS
        with using_session(self.session_id):
            if guardrails.is_kill_switch_triggered():
                kill_result = guardrails.trigger_kill_switch()
                return f"ERROR: Kill switch activated. {kill_result}"

            is_blocked, block_msg, block_type = guardrails.validate_input(prompt)
            if is_blocked:
                guardrails.trigger_kill_switch()
                return f"ERROR: Input blocked [{block_type}]: {block_msg}"

            if self.CHAT_HISTORY:
                logger.debug("chat history detected")
                sys_p = self.load_system_prompt()
                if sys_p:
                    msg = {"role": "system", "content": sys_p}
                    if self.CHAT_HISTORY and self.CHAT_HISTORY[0].get("role") == "system":
                        self.CHAT_HISTORY.pop(0)
                    self.CHAT_HISTORY.insert(0, msg)
                    logger.debug("chat history was cleared. Added to CHAT_HISTORY new system prompt: %s", json.dumps(msg, indent=2))
                elif sys_p == None:
                            logging.debug("No System Prompt Loaded")
            else:
                logger.debug("No Chat History")

            msg = {"role": "user", "content": prompt}
            self.CHAT_HISTORY.append(msg)
            logger.debug("Added to CHAT_HISTORY: %s", json.dumps(msg, indent=2))

            iterations = 0
            while iterations < max_iterations:
                if guardrails.is_kill_switch_triggered():
                    kill_result = guardrails.trigger_kill_switch()
                    return f"ERROR: Kill switch activated during execution. {kill_result}"

                iterations += 1
                tools = registry.get_definitions(set(registry.get_all_tool_names()), quiet=True)
                logger.debug("LLM REQUEST: %s", json.dumps({"messages": self.CHAT_HISTORY, "tools": tools}, indent=2))
                try:
                    res = client.chat.completions.create(
                        model=model, messages=self.CHAT_HISTORY, tools=tools, timeout=360
                    )
                except APIConnectionError as e:
                    logger.error("OpenAI API Connection error. Is LLM server up? : %s", str(e), exc_info=True)
                    raise
                except Exception as e:
                    logger.error("OpenAI API client error: %s", str(e), exc_info=True)

                    if "Failed to parse tool call arguments as JSON" in str(e):
                        error_msg = "JSON parsing error: The model returned malformed JSON for tool arguments. Please reformat your request."
                        msg = {
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
                        }
                        self.CHAT_HISTORY.append(msg)
                        logger.debug("Added to CHAT_HISTORY: %s", json.dumps(msg, indent=2))
                        msg = {
                            "role": "tool",
                            "tool_call_id": "error_tool_call",
                            "content": json.dumps({"error": error_msg}),
                        }
                        self.CHAT_HISTORY.append(msg)
                        logger.debug("Added to CHAT_HISTORY: %s", json.dumps(msg, indent=2))
                        return error_msg
                    raise
                msg = res.choices[0].message
                logger.debug("LLM RESPONSE: %s", json.dumps(msg.model_dump(exclude_none=True), indent=2))

                msg_dict = msg.model_dump(exclude_none=True)
                self.CHAT_HISTORY.append(msg_dict)
                logger.debug("Added to CHAT_HISTORY: %s", json.dumps(msg_dict, indent=2))

                if not msg.tool_calls:
                    return str(msg.content)

                for call in msg.tool_calls:
                    if call.type == "function":
                        func_name = call.function.name
                        try:
                            args = json.loads(call.function.arguments)
                            with tracer.start_as_current_span(
                                f"tool.{func_name}",
                                openinference_span_kind="tool",
                            ) as span:
                                span.set_input(args)
                                out = registry.dispatch(func_name, args)
                                span.set_output(out)
                            msg = {
                                "role": "tool",
                                "tool_call_id": call.id,
                                "content": out,
                            }
                            self.CHAT_HISTORY.append(msg)
                            logger.debug("Added to CHAT_HISTORY: %s", json.dumps(msg, indent=2))
                        except Exception as e:
                            logger.error(
                                "Tool execution error for %s: %s",
                                call.id,
                                str(e),
                                exc_info=True,
                            )
                            msg = {
                                "role": "tool",
                                "tool_call_id": call.id,
                                "content": f"Error: {str(e)}",
                            }
                            self.CHAT_HISTORY.append(msg)
                            logger.debug("Added to CHAT_HISTORY: %s", json.dumps(msg, indent=2))

            return "Error: Maximum iterations reached without final response."


    def on_session_end() -> None:
        """Auto-extract facts from conversation at session end."""
        global CHAT_HISTORY
        try:
            store = MemoryStore(db_path="~/.skunk/state.db")
            extracted = store.auto_extract_facts(CHAT_HISTORY)
            if extracted > 0:
                logger.info("Auto-extracted %d facts from session", extracted)
        except Exception as e:
            logger.error("Auto-extraction failed: %s", e, exc_info=True)


if __name__ == "__main__":
    #logging.basicConfig(level=logging.INFO)
    agent = Agent()
    result = agent.run("Run a bash command that fails and outputs a lot of text.")
    logger.info("Agent result: %s", result)
