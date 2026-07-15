"""Playwright Browser Automation semantic tool suite for the OpenClaw agent."""

from app.tools.browser.tool import (
    browser_open,
    browser_interact,
    browser_navigate,
    browser_scroll,
    browser_file,
    browser_close,
)

# Standardized tools list for agent binding
tools = [
    browser_open,
    browser_interact,
    browser_navigate,
    browser_scroll,
    browser_file,
    browser_close,
]

__all__ = [
    "browser_open",
    "browser_interact",
    "browser_navigate",
    "browser_scroll",
    "browser_file",
    "browser_close",
    "tools",
]
