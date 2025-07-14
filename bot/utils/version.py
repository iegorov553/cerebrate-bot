"""
Version management for Doyobi Diary bot.
"""

import os
from pathlib import Path


def get_bot_version() -> str:
    """
    Get the current bot version.

    Returns:
        Version string (e.g., "2.1.0")
    """
    try:
        # Try to read from VERSION file in project root
        version_file = Path(__file__).parent.parent.parent / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
    except Exception as e:
        # Log the error for debugging but continue with fallback
        import logging
        logging.getLogger(__name__).debug(f"Could not read VERSION file: {e}")

    # Fallback to environment variable
    return os.getenv("BOT_VERSION", "unknown")


def get_version_info() -> dict:
    """
    Get detailed version information.

    Returns:
        Dictionary with version info
    """
    version = get_bot_version()

    # Try to get git commit hash if available
    commit_hash = os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown")
    if commit_hash != "unknown" and len(commit_hash) > 7:
        commit_hash = commit_hash[:7]  # Short hash

    return {
        "version": version,
        "commit": commit_hash,
        "environment": os.getenv("ENVIRONMENT", "production")
    }


def format_version_string() -> str:
    """
    Format version string for display.

    Returns:
        Formatted version string
    """
    info = get_version_info()

    if info["commit"] != "unknown":
        return f"v{info['version']} ({info['commit']})"
    else:
        return f"v{info['version']}"
