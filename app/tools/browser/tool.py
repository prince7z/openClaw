"""LangChain tool interface wrappers for Browser Automation (Thread-Safe Sync-to-Async dispatcher)."""

from typing import Any, Literal
from langchain.tools import tool

from app.tools.browser import browser
from app.tools.browser.executor import execute_browser_action_async
from app.tools.browser.memory import get_session_memory
from app.tools.browser.parser import serialize_to_yaml
from app.tools.browser.state import run_in_browser_thread
from app.tools.browser.utils import resolve_locator_from_id


@tool("browser_open")
def browser_open(url: str) -> str:
    """Open a webpage."""
    session = "default"
    diff = run_in_browser_thread(
        execute_browser_action_async(
            "Open",
            lambda: browser.open_url(url, session=session),
            details={"URL": url},
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser_interact")
def browser_interact(
    action: Literal["click", "type", "select"],
    element: str,
    value: str | None = None,
) -> str:
    """Interact with page elements."""
    session = "default"
    mem = get_session_memory(session)
    locator = resolve_locator_from_id(mem.last_page_state, element)

    if action == "click":
        diff = run_in_browser_thread(
            execute_browser_action_async(
                "Click",
                lambda: browser.click_element(locator, session=session),
                locator=locator,
                details={"Element ID": element},
                session=session
            )
        )
    elif action == "type":
        if value is None:
            raise ValueError("value is required for type action")
        diff = run_in_browser_thread(
            execute_browser_action_async(
                "Type",
                lambda: browser.type_text(locator, value, session=session),
                locator=locator,
                details={"Element ID": element, "Text Length": len(value)},
                session=session
            )
        )
    elif action == "select":
        if value is None:
            raise ValueError("value is required for select action")
        diff = run_in_browser_thread(
            execute_browser_action_async(
                "Select",
                lambda: browser.select_option(locator, value, session=session),
                locator=locator,
                details={"Element ID": element, "Selected Value": value},
                session=session
            )
        )
    else:
        raise ValueError(f"Unsupported action: {action}")

    return serialize_to_yaml(diff)


@tool("browser_navigate")
def browser_navigate(
    action: Literal["back", "forward", "reload"],
) -> str:
    """Navigate the current page."""
    session = "default"
    if action == "back":
        diff = run_in_browser_thread(
            execute_browser_action_async(
                "Back",
                lambda: browser.navigate_back(session=session),
                session=session
            )
        )
    elif action == "forward":
        diff = run_in_browser_thread(
            execute_browser_action_async(
                "Forward",
                lambda: browser.navigate_forward(session=session),
                session=session
            )
        )
    elif action == "reload":
        diff = run_in_browser_thread(
            execute_browser_action_async(
                "Reload",
                lambda: browser.reload_page(session=session),
                session=session
            )
        )
    else:
        raise ValueError(f"Unsupported action: {action}")

    return serialize_to_yaml(diff)


@tool("browser_scroll")
def browser_scroll(
    direction: Literal["up", "down"] = "down",
    amount: int | None = None,
) -> str:
    """Scroll the page."""
    session = "default"
    scroll_amount = amount if amount is not None else 500
    diff = run_in_browser_thread(
        execute_browser_action_async(
            "Scroll",
            lambda: browser.scroll_page(direction, amount=scroll_amount, session=session),
            details={"Direction": direction, "Amount": scroll_amount},
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser_file")
def browser_file(
    action: Literal["upload", "download"],
    element: str,
    file: str | None = None,
) -> str:
    """Upload or download files."""
    session = "default"
    mem = get_session_memory(session)
    locator = resolve_locator_from_id(mem.last_page_state, element)

    if action == "upload":
        if not file:
            raise ValueError("file parameter is required for upload action")
        diff = run_in_browser_thread(
            execute_browser_action_async(
                "Upload",
                lambda: browser.upload_file(locator, file, session=session),
                locator=locator,
                details={"Element ID": element, "File Path": file},
                session=session
            )
        )
    elif action == "download":
        from app.tools.browser.downloads import wait_for_download_after_action
        output_dir = "."
        def do_download():
            return wait_for_download_after_action(
                lambda: browser.click_element(locator, session=session),
                output_dir=output_dir,
                session=session
            )

        diff = run_in_browser_thread(
            execute_browser_action_async(
                "Download",
                do_download,
                locator=locator,
                details={"Element ID": element, "Output Dir": output_dir},
                session=session
            )
        )
    else:
        raise ValueError(f"Unsupported action: {action}")

    return serialize_to_yaml(diff)


@tool("browser_close")
def browser_close() -> str:
    """Close the browser."""
    session = "default"
    run_in_browser_thread(browser.close_session(session=session))
    mem = get_session_memory(session)
    mem.reset()
    return f"Browser session '{session}' closed and memory caches flushed."
