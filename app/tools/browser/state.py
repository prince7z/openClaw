"""Playwright browser session state store and event emitter (Asynchronous / Thread-Safe)."""

import asyncio
import logging
import threading
from typing import Any, Coroutine
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Dialog,
    Download
)

logger = logging.getLogger("openclaw-agent")

_LOOP: asyncio.AbstractEventLoop | None = None
_THREAD: threading.Thread | None = None


def get_browser_loop() -> asyncio.AbstractEventLoop:
    """Retrieve or spawn the dedicated background event loop running the Playwright thread."""
    global _LOOP, _THREAD
    if _LOOP is None:
        _LOOP = asyncio.new_event_loop()
        _THREAD = threading.Thread(
            target=_LOOP.run_forever,
            name="PlaywrightBrowserThread",
            daemon=True
        )
        _THREAD.start()
        logger.info("Spawned dedicated PlaywrightBrowserThread event loop.")
    return _LOOP


def run_in_browser_thread(coroutine: Coroutine[Any, Any, Any]) -> Any:
    """Execute an asynchronous browser operation thread-safe on the dedicated background thread.

    Blocks the calling thread until execution completes and returns the result.
    """
    loop = get_browser_loop()
    future = asyncio.run_coroutine_threadsafe(coroutine, loop)
    return future.result()


class SessionState:
    """Stores page context, active page, and captured browser events for a named session."""

    def __init__(self, name: str):
        self.name: str = name
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.events: list[str] = []
        self.dialogs: list[str] = []
        self.downloads: list[Download] = []
        self.file_choosers: list[Any] = []

    def clear_events(self) -> None:
        """Flush the logged browser events."""
        self.events.clear()
        self.dialogs.clear()


class BrowserStateManager:
    """Singleton/global manager of active Playwright browser sessions."""

    def __init__(self):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self.sessions: dict[str, SessionState] = {}
        self.active_session_name: str = "default"

    async def get_playwright(self) -> Playwright:
        """Retrieve or initialize the async Playwright instance."""
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        return self._playwright

    async def get_browser(self, headless: bool = True) -> Browser:
        """Retrieve or launch the browser instance."""
        pw = await self.get_playwright()
        if self._browser is None:
            self._browser = await pw.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
        return self._browser

    async def get_session(self, name: str, headless: bool = True) -> SessionState:
        """Fetch or spawn a browser session page context and register events."""
        if name not in self.sessions:
            self.sessions[name] = SessionState(name)

        session = self.sessions[name]
        if session.context is None:
            browser = await self.get_browser(headless=headless)
            session.context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            session.page = await session.context.new_page()
            self._register_event_handlers(session)

        self.active_session_name = name
        return session

    def get_active_session(self) -> SessionState | None:
        """Get the currently selected session, if initialized."""
        return self.sessions.get(self.active_session_name)

    def _register_event_handlers(self, session: SessionState) -> None:
        """Bind event listeners to Playwright page callbacks."""
        page = session.page
        if not page:
            return

        # Setup standard navigation & load hooks
        page.on("load", lambda: session.events.append("PageLoaded"))
        page.on("framenavigated", lambda frame: session.events.append("NavigationFinished") if frame == page.main_frame else None)

        # Dialog/alert handlers
        async def on_dialog(dialog: Dialog):
            session.dialogs.append(dialog.message)
            session.events.append("DialogOpened")
            logger.info(f"[BrowserSession '{session.name}'] Dialog opened: {dialog.message}")
            await dialog.dismiss()

        page.on("dialog", lambda dialog: asyncio.create_task(on_dialog(dialog)))

        # Download hooks
        def on_download(download: Download):
            session.downloads.append(download)
            session.events.append("DownloadStarted")
            logger.info(f"[BrowserSession '{session.name}'] Download started: {download.suggested_filename}")

        page.on("download", on_download)

        # FileChooser hooks
        page.on("filechooser", lambda fc: session.file_choosers.append(fc) or session.events.append("FileChooserOpened"))

        # Popup hooks
        page.on("popup", lambda p: session.events.append("PopupOpened"))

    async def close_all(self) -> None:
        """Close contexts and stop Playwright."""
        for name, session in list(self.sessions.items()):
            if session.context:
                await session.context.close()
            session.context = None
            session.page = None
        self.sessions.clear()

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


# Global active browser manager instance
state_manager = BrowserStateManager()
