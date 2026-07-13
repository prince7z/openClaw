"""Browser download manager wrapper handling asynchronous file transfers."""

import asyncio
import logging
import os
from typing import Callable, Any, Coroutine
from app.tools.browser.state import state_manager

logger = logging.getLogger("openclaw-agent")


async def wait_for_download_after_action(
    action_callable: Callable[[], Coroutine[Any, Any, Any]],
    output_dir: str = ".",
    timeout_ms: int = 30000,
    session: str = "default"
) -> str:
    """Execute a page action and wait for the resulting browser file download to complete.

    Args:
        action_callable: Callable coroutine representing the page action (e.g. click).
        output_dir: Local path to save the completed file download.
        timeout_ms: Wait timeout limit.
        session: Named browser session.

    Returns:
        The final absolute file path of the downloaded file.
    """
    s = await state_manager.get_session(session)
    os.makedirs(output_dir, exist_ok=True)

    async with s.page.expect_download(timeout=timeout_ms) as download_info:
        await action_callable()

    download = await download_info.value
    # Wait for file download to complete
    await download.path()

    save_path = os.path.join(output_dir, download.suggested_filename)
    await download.save_as(save_path)
    logger.info(f"[DownloadsSession '{session}'] Saved download to: {save_path}")
    return os.path.abspath(save_path)


async def wait_for_latest_download(
    output_dir: str = ".",
    timeout_seconds: float = 30.0,
    session: str = "default"
) -> str:
    """Wait for the most recently initiated browser file download to finish.

    Args:
        output_dir: Directory where the file should be saved.
        timeout_seconds: Max seconds to wait for download to start.
        session: Named browser session.

    Returns:
        The local path of the saved download.
    """
    s = await state_manager.get_session(session)
    os.makedirs(output_dir, exist_ok=True)

    # Poll for download capture if not immediately present
    elapsed = 0.0
    while not s.downloads and elapsed < timeout_seconds:
        await asyncio.sleep(0.5)
        elapsed += 0.5

    if not s.downloads:
        raise TimeoutError("No browser downloads detected within the wait window.")

    download = s.downloads[-1]
    # Wait for background task completion
    await download.path()

    save_path = os.path.join(output_dir, download.suggested_filename)
    await download.save_as(save_path)
    return os.path.abspath(save_path)


def list_downloads(session: str = "default") -> list[str]:
    """List the filenames of files downloaded during this named browser session.

    Args:
        session: Named browser session.

    Returns:
        A list of filename strings.
    """
    s = state_manager.sessions.get(session)
    if not s:
        return []
    return [d.suggested_filename for d in s.downloads]


def clear_downloads(session: str = "default") -> None:
    """Clear all download reference records for the named session.

    Args:
        session: Named browser session.
    """
    s = state_manager.sessions.get(session)
    if s:
        s.downloads.clear()
