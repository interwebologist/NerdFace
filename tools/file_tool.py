"""File Tool Module - read_file tool."""

from pathlib import Path
from tools.registry import registry, tool_result, tool_error


def read_file(path: str) -> str:
    """Read a file."""
    try:
        p = Path(path).expanduser()
        with open(p, "r") as f:
            content = f.read()
        return tool_result(path=str(p), content=content)
    except Exception as e:
        return tool_error(str(e))


READ_FILE_SCHEMA = {
    "name": "read_file",
    "description": (
        "Read a text file. Returns the file contents as JSON "
        "with path and content fields."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to read (absolute or relative)",
            }
        },
        "required": ["path"],
    },
}

registry.register(
    name="read_file",
    toolset="file",
    schema=READ_FILE_SCHEMA,
    handler=lambda args, **kw: read_file(path=args.get("path", "")),
    check_fn=None,
    emoji="📖",
)
