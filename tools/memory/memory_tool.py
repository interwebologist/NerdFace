"""Holographic Memory Tool - fact_store and fact_feedback for nerdface-agent."""

from dataclasses import dataclass
from typing import Optional
from tools.registry import registry, tool_result, tool_error
from .store import MemoryStore
from .retrieval import FactRetriever


@dataclass
class MemoryToolState:
    """Thread-safe state container for memory tools."""

    store: Optional[MemoryStore] = None
    retriever: Optional[FactRetriever] = None


_state = MemoryToolState()


def _get_store() -> MemoryStore:
    """Get or create the MemoryStore instance."""
    if _state.store is None:
        _state.store = MemoryStore(db_path="~/.skunk/state.db")
    return _state.store


def _get_retriever() -> FactRetriever:
    """Get or create the FactRetriever instance."""
    if _state.retriever is None:
        _state.retriever = FactRetriever(store=_get_store())
    return _state.retriever


def fact_store(args: dict) -> str:
    """Handle fact_store tool actions."""
    try:
        action = args.get("action")

        if action == "add":
            fact_id = _get_store().add_fact(
                args.get("content", ""),
                category=args.get("category", "general"),
                tags=args.get("tags", ""),
            )
            return tool_result(fact_id=fact_id, status="added")

        elif action == "search":
            results = _get_retriever().search(
                args.get("query", ""),
                category=args.get("category"),
                min_trust=float(args.get("min_trust", 0.3)),
                limit=int(args.get("limit", 10)),
            )
            return tool_result(results=results, count=len(results))

        elif action == "probe":
            results = _get_retriever().probe(
                args.get("entity", ""),
                category=args.get("category"),
                limit=int(args.get("limit", 10)),
            )
            return tool_result(results=results, count=len(results))

        elif action == "related":
            results = _get_retriever().related(
                args.get("entity", ""),
                category=args.get("category"),
                limit=int(args.get("limit", 10)),
            )
            return tool_result(results=results, count=len(results))

        elif action == "reason":
            entities = args.get("entities", [])
            if not entities:
                return tool_error("reason requires 'entities' list")
            results = _get_retriever().reason(
                entities,
                category=args.get("category"),
                limit=int(args.get("limit", 10)),
            )
            return tool_result(results=results, count=len(results))

        elif action == "contradict":
            results = _get_retriever().contradict(
                category=args.get("category"),
                limit=int(args.get("limit", 10)),
            )
            return tool_result(results=results, count=len(results))

        elif action == "update":
            trust_val = args.get("trust_delta")
            trust_delta = float(trust_val) if trust_val is not None else None
            updated = _get_store().update_fact(
                int(args.get("fact_id", 0)),
                content=args.get("content"),
                trust_delta=trust_delta,
                tags=args.get("tags"),
                category=args.get("category"),
            )
            return tool_result(updated=updated)

        elif action == "remove":
            removed = _get_store().remove_fact(int(args.get("fact_id", 0)))
            return tool_result(removed=removed)

        elif action == "list":
            facts = _get_store().list_facts(
                category=args.get("category"),
                min_trust=float(args.get("min_trust", 0.0)),
                limit=int(args.get("limit", 10)),
            )
            return tool_result(facts=facts, count=len(facts))

        else:
            return tool_error(f"Unknown action: {action}")

    except KeyError as exc:
        return tool_error(f"Missing required argument: {exc}")
    except Exception as exc:
        return tool_error(str(exc))


def fact_feedback(args: dict) -> str:
    """Handle fact_feedback tool."""
    try:
        fact_id = int(args.get("fact_id", 0))
        helpful = args.get("action") == "helpful"
        result = _get_store().record_feedback(fact_id, helpful=helpful)
        return tool_result(result)
    except Exception as exc:
        return tool_error(str(exc))


# Tool schemas
FACT_STORE_SCHEMA = {
    "name": "fact_store",
    "description": (
        "Deep structured memory with algebraic reasoning. "
        "Use to store facts the user would expect you to remember, "
        "or search/probe for past information.\n\n"
        "ACTIONS:\n"
        "• add — Store a fact (requires 'content' parameter)\n"
        "• search — Keyword lookup (requires 'query' parameter)\n"
        "• probe — Entity recall: ALL facts about a person/thing "
        "(requires 'entity' parameter)\n"
        "• related — What connects to an entity? Structural adjacency\n"
        "• reason — Compositional: facts connected to MULTIPLE entities "
        "simultaneously\n"
        "• contradict — Find facts making conflicting claims\n"
        "• update/remove/list — CRUD operations\n\n"
        "IMPORTANT: Before answering questions about the user, "
        "ALWAYS probe or reason first."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "add",
                    "search",
                    "probe",
                    "related",
                    "reason",
                    "contradict",
                    "update",
                    "remove",
                    "list",
                ],
            },
            "content": {
                "type": "string",
                "description": "Fact content (required for 'add').",
            },
            "query": {
                "type": "string",
                "description": "Search query (required for 'search').",
            },
            "entity": {
                "type": "string",
                "description": "Entity name for 'probe'/'related'.",
            },
            "entities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Entity names for 'reason'.",
            },
            "fact_id": {
                "type": "integer",
                "description": "Fact ID for 'update'/'remove'.",
            },
            "category": {
                "type": "string",
                "enum": ["user_pref", "project", "tool", "general"],
            },
            "tags": {"type": "string", "description": "Comma-separated tags."},
            "trust_delta": {
                "type": "number",
                "description": "Trust adjustment for 'update'.",
            },
            "min_trust": {
                "type": "number",
                "description": "Minimum trust filter (default: 0.3).",
            },
            "limit": {"type": "integer", "description": "Max results (default: 10)."},
        },
        "required": ["action"],
    },
}

FACT_FEEDBACK_SCHEMA = {
    "name": "fact_feedback",
    "description": (
        "Rate a fact after using it. Mark 'helpful' if accurate, "
        "'unhelpful' if outdated. "
        "This trains the memory — good facts rise, bad facts sink."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["helpful", "unhelpful"]},
            "fact_id": {"type": "integer", "description": "The fact ID to rate."},
        },
        "required": ["action", "fact_id"],
    },
}

# Register tools
registry.register(
    name="fact_store",
    toolset="memory",
    schema=FACT_STORE_SCHEMA,
    handler=lambda args, **kw: fact_store(args),
    check_fn=None,
    emoji="🧠",
)

registry.register(
    name="fact_feedback",
    toolset="memory",
    schema=FACT_FEEDBACK_SCHEMA,
    handler=lambda args, **kw: fact_feedback(args),
    check_fn=None,
    emoji="⭐",
)
