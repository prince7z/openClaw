"""Playwright low-level action execution wrappers (Asynchronous)."""

import asyncio
import logging
from app.tools.browser.state import state_manager

logger = logging.getLogger("openclaw-agent")


async def open_url(url: str, session: str = "default", headless: bool = False) -> str:
    """Navigate to the target URL inside the specified browser session context.

    Args:
        url: The web URL to load.
        session: Named browser session context to utilize.
        headless: Whether to start the browser in headless mode.

    Returns:
        The actual loaded URL.
    """
    s = await state_manager.get_session(session, headless=headless)
    await s.page.goto(url, wait_until="load", timeout=30000)
    return s.page.url


async def close_session(session: str = "default") -> None:
    """Close context and active page of the named session.

    Args:
        session: Name of the session to terminate.
    """
    s = state_manager.sessions.get(session)
    if s and s.context:
        await s.context.close()
    if s:
        s.context = None
        s.page = None


async def click_element(locator: str, session: str = "default") -> None:
    """Click on the target element using its Playwright locator.

    Args:
        locator: Playwright selector path.
        session: Named browser session.
    """
    s = await state_manager.get_session(session)
    await s.page.locator(locator).first.click(timeout=10000)


async def type_text(locator: str, text: str, session: str = "default") -> None:
    """Type text into the target element input field.

    Args:
        locator: Playwright textbox/textarea selector.
        text: Text contents to write.
        session: Named browser session.
    """
    s = await state_manager.get_session(session)
    loc = s.page.locator(locator).first
    await loc.click(timeout=5000)
    await loc.fill("")
    await loc.type(text, delay=20)


async def clear_input(locator: str, session: str = "default") -> None:
    """Clear all characters from the target input element.

    Args:
        locator: Playwright input selector.
        session: Named browser session.
    """
    s = await state_manager.get_session(session)
    await s.page.locator(locator).first.fill("")


async def hover_element(locator: str, session: str = "default") -> None:
    """Move cursor hover focus over the target element.

    Args:
        locator: Target element selector.
        session: Named browser session.
    """
    s = await state_manager.get_session(session)
    await s.page.locator(locator).first.hover(timeout=5000)


async def select_option(locator: str, value: str, session: str = "default") -> None:
    """Select option value in an HTML dropdown selection element.

    Args:
        locator: Select element selector.
        value: The dropdown option label or value.
        session: Named browser session.
    """
    s = await state_manager.get_session(session)
    await s.page.locator(locator).first.select_option(value=value, timeout=5000)


async def scroll_page(direction: str, amount: int = 500, session: str = "default") -> None:
    """Scroll vertical scroll position by a relative offset.

    Args:
        direction: 'up' or 'down'.
        amount: Pixel distance offset.
        session: Named browser session.
    """
    s = await state_manager.get_session(session)
    delta = amount if direction.lower() == "down" else -amount
    await s.page.evaluate(f"window.scrollBy(0, {delta})")


async def wait_seconds(seconds: float) -> None:
    """Halt execution flow.

    Args:
        seconds: Sleep duration.
    """
    await asyncio.sleep(seconds)


async def navigate_back(session: str = "default") -> None:
    """Go back to the previous history page state in navigation history.

    Args:
        session: Named browser session.
    """
    s = await state_manager.get_session(session)
    await s.page.go_back(wait_until="load")


async def navigate_forward(session: str = "default") -> None:
    """Go forward to the next page in navigation history.

    Args:
        session: Named browser session.
    """
    s = await state_manager.get_session(session)
    await s.page.go_forward(wait_until="load")


async def reload_page(session: str = "default") -> None:
    """Reload/refresh active page state.

    Args:
        session: Named browser session.
    """
    s = await state_manager.get_session(session)
    await s.page.reload(wait_until="load")


async def take_screenshot(save_path: str, session: str = "default") -> None:
    """Capture full visible page screenshot and save to disk.

    Args:
        save_path: File system storage path.
        session: Named browser session.
    """
    s = await state_manager.get_session(session)
    await s.page.screenshot(path=save_path, full_page=True)


async def current_url(session: str = "default") -> str:
    """Retrieve active page URL.

    Args:
        session: Named browser session.
    """
    s = await state_manager.get_session(session)
    return s.page.url


async def current_title(session: str = "default") -> str:
    """Retrieve active page title.

    Args:
        session: Named browser session.
    """
    s = await state_manager.get_session(session)
    return await s.page.title()


async def upload_file(locator: str, file_path: str, session: str = "default") -> None:
    """Upload a file to the input file element selector.

    Args:
        locator: Playwright file input selector.
        file_path: Local file path string.
        session: Named browser session.
    """
    s = await state_manager.get_session(session)
    await s.page.locator(locator).first.set_input_files(file_path, timeout=10000)
