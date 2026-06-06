"""Nerdface constants for browser tool paths.

Provides the .nerdface directory path used by browser tools.
Import-safe with no dependencies.
"""

from pathlib import Path


def get_nerdface_home() -> Path:
    """Return the Nerdface home directory (.nerdface).

    This is the single source of truth for all Nerdface data directories.
    """
    return Path(__file__).resolve().parent.parent / ".nerdface"


def get_nerdface_dir(subpath: str) -> Path:
    """Return subpath under .nerdface directory.

    Args:
        subpath: Path relative to .nerdface (e.g., "browser_auth/camofox")

    Returns:
        Absolute Path to the subdirectory
    """
    return get_nerdface_home() / subpath
