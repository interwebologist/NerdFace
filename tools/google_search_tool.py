"""Google Search Tool - Serpbase.dev search."""

import json
import os
import requests
from tools.registry import registry, tool_result, tool_error


def google_search(q: str, num: int = 10) -> str:
    """Official Serpbase.dev (Serper) Google Search tool."""
    api_key = os.getenv("SERPBASE_API_KEY")
    if not api_key:
        return tool_error(
            "SERPBASE_API_KEY environment variable not set. "
            "Get API key from https://serpbase.com/"
        )
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": q, "num": num})
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        if response.status_code == 403:
            return tool_error(
                "Serpbase API key invalid or unauthorized. "
                "Check your API key at https://serpbase.com/"
            )
        if response.status_code == 429:
            return tool_error("Serpbase API rate limit exceeded. Try again later.")
        response.raise_for_status()
        data = response.json()
        results = data.get("organic", [])
        if not results:
            return tool_error("No organic results found.")
        output = []
        for r in results:
            output.append(
                {
                    "title": r.get("title", ""),
                    "link": r.get("link", ""),
                    "snippet": r.get("snippet", ""),
                }
            )
        return tool_result(query=q, results=output)
    except requests.exceptions.Timeout:
        return tool_error("Serpbase API request timed out")
    except requests.exceptions.ConnectionError:
        return tool_error("Serpbase API connection failed")
    except json.JSONDecodeError as e:
        return tool_error(f"Serpbase API returned invalid JSON: {str(e)}")
    except Exception as e:
        return tool_error(f"Serpbase Error: {str(e)}")


GOOGLE_SEARCH_SCHEMA = {
    "name": "google_search",
    "description": (
        "Search Google using Serpbase.dev (Serper). "
        "Requires SERPBASE_API_KEY environment variable."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "q": {"type": "string", "description": "The search query"},
            "num": {
                "type": "integer",
                "description": "Number of results",
                "default": 10,
            },
        },
        "required": ["q"],
    },
}


def check_google_search_requirements() -> bool:
    """Check if SERPBASE_API_KEY is set."""
    return bool(os.getenv("SERPBASE_API_KEY"))


registry.register(
    name="google_search",
    toolset="web",
    schema=GOOGLE_SEARCH_SCHEMA,
    handler=lambda args, **kw: google_search(
        q=args.get("q", ""), num=args.get("num", 10)
    ),
    check_fn=check_google_search_requirements,
    requires_env=["SERPBASE_API_KEY"],
    emoji="🔍",
)
