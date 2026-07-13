"""Playwright Browser Automation semantic tool suite for the OpenClaw agent."""

from app.tools.browser.tool import (
    browser_open,
    browser_click,
    browser_type,
    browser_clear,
    browser_hover,
    browser_select,
    browser_scroll,
    browser_wait,
    browser_back,
    browser_forward,
    browser_reload,
    browser_upload_file,
    browser_download_file,
    browser_close
)

# Standardized tools list for agent binding
tools = [
    browser_open,
    browser_click,
    browser_type,
    browser_clear,
    browser_hover,
    browser_select,
    browser_scroll,
    browser_wait,
    browser_back,
    browser_forward,
    browser_reload,
    browser_upload_file,
    browser_download_file,
    browser_close
]

__all__ = [
    "browser_open",
    "browser_click",
    "browser_type",
    "browser_clear",
    "browser_hover",
    "browser_select",
    "browser_scroll",
    "browser_wait",
    "browser_back",
    "browser_forward",
    "browser_reload",
    "browser_upload_file",
    "browser_download_file",
    "browser_close",
    "tools"
]
