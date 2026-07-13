"""Stabilization engine and dangerous action safety guardrail executor (Asynchronous)."""

import asyncio
import logging
import os
import sys
import time
from typing import Any, Callable, Coroutine

from app.tools.browser import logger as rich_logger
from app.tools.browser.browser import take_screenshot
from app.tools.browser.extractor import extract_page_state
from app.tools.browser.memory import calculate_state_diff, get_session_memory
from app.tools.browser.state import state_manager

logger = logging.getLogger("openclaw-agent")

# Keywords that trigger the human approval prompt
DANGEROUS_KEYWORDS = [
    "place order", "delete repository", "transfer money", "pay",
    "delete account", "buy now", "confirm purchase",
    "remove repository", "destroy", "checkout", "subscribe"
]

# Registered global hook for human approval (e.g. from Telegram)
HUMAN_APPROVAL_CALLBACK: Callable[[str, str, str], Coroutine[Any, Any, bool]] | None = None
MAIN_LOOP: asyncio.AbstractEventLoop | None = None


def register_approval_callback(callback: Callable[[str, str, str], Coroutine[Any, Any, bool]] | None, loop: asyncio.AbstractEventLoop | None = None) -> None:
    """Register a custom callback to prompt the user for dangerous actions.

    Args:
        callback: Async callback.
        loop: Main event loop reference if the callback is async and called from worker threads.
    """
    global HUMAN_APPROVAL_CALLBACK, MAIN_LOOP
    HUMAN_APPROVAL_CALLBACK = callback
    MAIN_LOOP = loop


async def _inspect_for_danger_async(page: Any, action_name: str, locator: str) -> str | None:
    """Inspect element text and attributes for dangerous keywords.

    Returns the triggering keyword text if dangerous, else None.
    """
    if action_name.lower() not in ("click", "submit"):
        return None

    try:
        el = page.locator(locator).first
        if await el.count() == 0:
            return None

        # Gather inner text and common attributes
        text = (await el.inner_text() or "").strip().lower()
        attrs = await el.evaluate("""el => {
            return [
                el.getAttribute('value'),
                el.getAttribute('name'),
                el.getAttribute('aria-label'),
                el.getAttribute('id'),
                el.getAttribute('class')
            ].join(' ').toLowerCase();
        }""")

        combined = f"{text} {attrs}"
        for kw in DANGEROUS_KEYWORDS:
            if kw in combined:
                return f"Element text/attribute matches dangerous keyword: '{kw}'"
    except Exception as exc:
        logger.debug(f"Danger check inspection failed: {exc}")

    return None


async def wait_for_dom_stabilization_async(
    page: Any,
    quiet_window_ms: int = 500,
    timeout_ms: int = 8000
) -> float:
    """Wait until page DOM mutations settle for the specified quiet window.

    Args:
        page: Playwright Page instance.
        quiet_window_ms: Miliseconds duration of no-mutation silence required.
        timeout_ms: Max execution ceiling limits.

    Returns:
        The total elapsed stabilization wait duration in milliseconds.
    """
    start_time = time.time()

    # Inject MutationObserver into the browser window context
    init_script = """
    () => {
        window.__lastDomMutation = Date.now();
        if (window.__domObserver) {
            window.__domObserver.disconnect();
        }
        const observer = new MutationObserver(() => {
            window.__lastDomMutation = Date.now();
        });
        observer.observe(document, { attributes: true, childList: true, subtree: true });
        window.__domObserver = observer;
    }
    """
    try:
        await page.evaluate(init_script)
    except Exception as exc:
        logger.debug(f"Failed to inject DOM observer: {exc}")
        return 0.0

    # Poll status
    poll_interval = 0.05
    while (time.time() - start_time) < (timeout_ms / 1000.0):
        try:
            last_mutation = await page.evaluate("window.__lastDomMutation")
            now = await page.evaluate("Date.now()")
            if last_mutation and (now - last_mutation) > quiet_window_ms:
                break
        except Exception:
            # Page navigated away or context destroyed
            break
            
        # Asynchronous wait on the browser thread
        await asyncio.sleep(poll_interval)

    # Disconnect observer
    try:
        await page.evaluate("if (window.__domObserver) window.__domObserver.disconnect()")
    except Exception:
        pass

    duration_ms = (time.time() - start_time) * 1000.0
    return duration_ms


async def execute_browser_action_async(
    action_name: str,
    action_callable: Callable[[], Coroutine[Any, Any, Any]],
    locator: str | None = None,
    details: dict[str, Any] | None = None,
    session: str = "default",
    quiet_window_ms: int = 500
) -> dict[str, Any]:
    """Wrap browser action execution, performing safety reviews, stabilization, and state diff compilation.

    Args:
        action_name: Name of the action (e.g. Open, Click).
        action_callable: Execution callable coroutine block.
        locator: Playwright selector (if targeting an element).
        details: Metadata for logging.
        session: Named browser session.
        quiet_window_ms: Stabilization DOM settlement duration.

    Returns:
        A dictionary representation of the StateDiff model.
    """
    s = await state_manager.get_session(session)
    mem = get_session_memory(session)

    # 1. Log action details
    log_details = details or {}
    if locator:
        log_details["Locator"] = locator
    log_details["Session"] = session
    rich_logger.log_browser_action(action_name, log_details)

    # 2. Safety Review Confirmation Guardrail
    if locator:
        danger_reason = await _inspect_for_danger_async(s.page, action_name, locator)
        if danger_reason:
            logger.warning(f"[Warning] DANGEROUS ACTION TRIGGERED: {danger_reason}")
            approved = False

            if HUMAN_APPROVAL_CALLBACK:
                if MAIN_LOOP:
                    # Run the async approval callback threadsafe on the main event loop
                    future = asyncio.run_coroutine_threadsafe(
                        HUMAN_APPROVAL_CALLBACK(session, action_name, danger_reason),
                        MAIN_LOOP
                    )
                    # Convert concurrent.futures.Future to awaitable asyncio Future
                    approved = await asyncio.wrap_future(future)
                else:
                    approved = await HUMAN_APPROVAL_CALLBACK(session, action_name, danger_reason)
            else:
                # Fallback to console prompt (run in executor executor threadpool executor to prevent loop block)
                def prompt_user():
                    print(f"\n[Warning] [Browser Safety Guardrail] DANGEROUS ACTION DETECTED in session '{session}':", file=sys.stderr)
                    print(f"   Reason: {danger_reason}", file=sys.stderr)
                    print(f"   Command: {action_name} on element {locator}", file=sys.stderr)
                    ans = input(" > Approve execution? (yes/no): ")
                    return ans.strip().lower() in ("y", "yes")

                approved = await asyncio.to_thread(prompt_user)

            if not approved:
                rich_logger.log_browser_error(action_name, "Action rejected by user safety review.")
                raise PermissionError("Dangerous action rejected by human safety review.")

    # 3. Dispatch Playwright action
    try:
        await action_callable()
    except Exception as exc:
        # Action failed: save failure snapshot
        filename = f"failure_{session}_{int(time.time())}.png"
        os.makedirs("screenshots", exist_ok=True)
        screenshot_path = os.path.join("screenshots", filename)
        try:
            await take_screenshot(screenshot_path, session=session)
            logger.info(f"Saved failure screenshot to {screenshot_path}")
        except Exception as s_exc:
            logger.debug(f"Failed to capture failure screenshot: {s_exc}")

        rich_logger.log_browser_error(action_name, str(exc))
        raise exc

    # 4. Stabilize DOM changes
    stabilization_ms = await wait_for_dom_stabilization_async(s.page, quiet_window_ms=quiet_window_ms)
    rich_logger.log_stabilization(stabilization_ms, "DOM settlement / Navigation completed")

    # 5. Extract updated PageState
    new_state = await extract_page_state(session)
    rich_logger.log_extraction(
        {
            "inputs": len(new_state.inputs),
            "buttons": len(new_state.buttons),
            "links": len(new_state.links),
            "products": len(new_state.products)
        }
    )

    # 6. Compute and cache state diff
    diff = calculate_state_diff(mem.last_page_state, new_state)

    # Save to session memory history
    mem.last_page_state = new_state
    mem.log_navigation(s.page.url)
    mem.last_action = f"{action_name} on {locator}" if locator else action_name

    return diff.model_dump()
