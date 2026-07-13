"""LangChain tool interface wrappers for Browser Automation (Thread-Safe Sync-to-Async dispatcher)."""

from langchain.tools import tool

from app.tools.browser import browser
from app.tools.browser.executor import execute_browser_action_async
from app.tools.browser.memory import get_session_memory
from app.tools.browser.parser import serialize_to_yaml
from app.tools.browser.state import run_in_browser_thread
from app.tools.browser.utils import resolve_locator_from_id


@tool("browser.open")
def browser_open(url: str, session: str = "default") -> str:
    """Navigate the browser session context to the target URL.

    Args:
        url: The web address to open.
        session: Named browser session context. Defaults to 'default'.

    Returns:
        YAML string of the page state diff.
    """
    diff = run_in_browser_thread(
        execute_browser_action_async(
            "Open",
            lambda: browser.open_url(url, session=session),
            details={"URL": url},
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser.click")
def browser_click(element_id: str, session: str = "default") -> str:
    """Click on the visible interactive page element using its semantic visual ID.

    Args:
        element_id: The visual element ID slug (e.g. btn_login, lnk_cart).
        session: Named browser session context. Defaults to 'default'.

    Returns:
        YAML string of the page state diff.
    """
    mem = get_session_memory(session)
    locator = resolve_locator_from_id(mem.last_page_state, element_id)

    diff = run_in_browser_thread(
        execute_browser_action_async(
            "Click",
            lambda: browser.click_element(locator, session=session),
            locator=locator,
            details={"Element ID": element_id},
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser.type")
def browser_type(element_id: str, text: str, session: str = "default") -> str:
    """Type text into an input field or textbox using its semantic visual ID.

    Args:
        element_id: The visual input element ID slug (e.g. inp_search).
        text: String contents to type.
        session: Named browser session context. Defaults to 'default'.

    Returns:
        YAML string of the page state diff.
    """
    mem = get_session_memory(session)
    locator = resolve_locator_from_id(mem.last_page_state, element_id)

    diff = run_in_browser_thread(
        execute_browser_action_async(
            "Type",
            lambda: browser.type_text(locator, text, session=session),
            locator=locator,
            details={"Element ID": element_id, "Text Length": len(text)},
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser.clear")
def browser_clear(element_id: str, session: str = "default") -> str:
    """Clear all text characters from an input field using its semantic visual ID.

    Args:
        element_id: The visual input element ID slug.
        session: Named browser session context. Defaults to 'default'.

    Returns:
        YAML string of the page state diff.
    """
    mem = get_session_memory(session)
    locator = resolve_locator_from_id(mem.last_page_state, element_id)

    diff = run_in_browser_thread(
        execute_browser_action_async(
            "Clear",
            lambda: browser.clear_input(locator, session=session),
            locator=locator,
            details={"Element ID": element_id},
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser.hover")
def browser_hover(element_id: str, session: str = "default") -> str:
    """Hover cursor focus over a page element using its semantic visual ID.

    Args:
        element_id: The visual element ID slug.
        session: Named browser session context. Defaults to 'default'.

    Returns:
        YAML string of the page state diff.
    """
    mem = get_session_memory(session)
    locator = resolve_locator_from_id(mem.last_page_state, element_id)

    diff = run_in_browser_thread(
        execute_browser_action_async(
            "Hover",
            lambda: browser.hover_element(locator, session=session),
            locator=locator,
            details={"Element ID": element_id},
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser.select")
def browser_select(element_id: str, value: str, session: str = "default") -> str:
    """Select a value from a dropdown selection menu using its semantic visual ID.

    Args:
        element_id: The dropdown selector element ID.
        value: The value string or label to select.
        session: Named browser session context. Defaults to 'default'.

    Returns:
        YAML string of the page state diff.
    """
    mem = get_session_memory(session)
    locator = resolve_locator_from_id(mem.last_page_state, element_id)

    diff = run_in_browser_thread(
        execute_browser_action_async(
            "Select",
            lambda: browser.select_option(locator, value, session=session),
            locator=locator,
            details={"Element ID": element_id, "Selected Value": value},
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser.scroll")
def browser_scroll(direction: str, amount: int = 500, session: str = "default") -> str:
    """Scroll the page view vertically.

    Args:
        direction: Direction to scroll ('up' or 'down').
        amount: Scroll distance offset in pixels. Defaults to 500.
        session: Named browser session context. Defaults to 'default'.

    Returns:
        YAML string of the page state diff.
    """
    diff = run_in_browser_thread(
        execute_browser_action_async(
            "Scroll",
            lambda: browser.scroll_page(direction, amount=amount, session=session),
            details={"Direction": direction, "Amount": amount},
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser.wait")
def browser_wait(seconds: float | None = None, time: float | None = None, session: str = "default") -> str:
    """Pause execution for a specific duration.

    Args:
        seconds: Sleep duration in seconds.
        time: Sleep duration (can be in seconds or milliseconds).
        session: Named browser session context. Defaults to 'default'.

    Returns:
        YAML string of the page state diff.
    """
    sec = 1.0
    if seconds is not None:
        sec = seconds
    elif time is not None:
        if time >= 100:
            sec = time / 1000.0
        else:
            sec = time

    diff = run_in_browser_thread(
        execute_browser_action_async(
            "Wait",
            lambda: browser.wait_seconds(sec),
            details={"Duration": f"{sec}s"},
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser.back")
def browser_back(session: str = "default") -> str:
    """Navigate back to the previous page in history.

    Args:
        session: Named browser session context. Defaults to 'default'.

    Returns:
        YAML string of the page state diff.
    """
    diff = run_in_browser_thread(
        execute_browser_action_async(
            "Back",
            lambda: browser.navigate_back(session=session),
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser.forward")
def browser_forward(session: str = "default") -> str:
    """Navigate forward to the next page in history.

    Args:
        session: Named browser session context. Defaults to 'default'.

    Returns:
        YAML string of the page state diff.
    """
    diff = run_in_browser_thread(
        execute_browser_action_async(
            "Forward",
            lambda: browser.navigate_forward(session=session),
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser.reload")
def browser_reload(session: str = "default") -> str:
    """Refresh active page.

    Args:
        session: Named browser session context. Defaults to 'default'.

    Returns:
        YAML string of the page state diff.
    """
    diff = run_in_browser_thread(
        execute_browser_action_async(
            "Reload",
            lambda: browser.reload_page(session=session),
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser.upload_file")
def browser_upload_file(element_id: str, file_path: str, session: str = "default") -> str:
    """Upload a file to the input file element using its semantic visual ID.

    Args:
        element_id: File input element visual ID.
        file_path: Local path string of file to upload.
        session: Named browser session context. Defaults to 'default'.

    Returns:
        YAML string of the page state diff.
    """
    mem = get_session_memory(session)
    locator = resolve_locator_from_id(mem.last_page_state, element_id)

    diff = run_in_browser_thread(
        execute_browser_action_async(
            "Upload",
            lambda: browser.upload_file(locator, file_path, session=session),
            locator=locator,
            details={"Element ID": element_id, "File Path": file_path},
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser.download_file")
def browser_download_file(element_id: str, output_dir: str = ".", session: str = "default") -> str:
    """Click an element that triggers a file download and wait for the file transfer to complete.

    Args:
        element_id: Element visual ID (button/link) triggering the download.
        output_dir: Local path directory to save the file. Defaults to '.'.
        session: Named browser session context. Defaults to 'default'.

    Returns:
        YAML string of the page state diff.
    """
    from app.tools.browser.downloads import wait_for_download_after_action
    mem = get_session_memory(session)
    locator = resolve_locator_from_id(mem.last_page_state, element_id)

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
            details={"Element ID": element_id, "Output Dir": output_dir},
            session=session
        )
    )
    return serialize_to_yaml(diff)


@tool("browser.close")
def browser_close(session: str = "default") -> str:
    """Close the context and active page of the named browser session.

    Args:
        session: Named browser session context. Defaults to 'default'.

    Returns:
        A confirmation status description string.
    """
    run_in_browser_thread(browser.close_session(session=session))
    # Clear cache
    mem = get_session_memory(session)
    mem.reset()
    return f"Browser session '{session}' closed and memory caches flushed."
