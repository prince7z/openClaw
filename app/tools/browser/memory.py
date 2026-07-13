"""Browser session context memory and state diff generator."""

from typing import Any
from app.tools.browser.schemas import BrowserElement, PageState, StateDiff


class SessionMemory:
    """Maintains sequential page logs, action history, and context caches for a single named session."""

    def __init__(self, name: str):
        self.name: str = name
        self.history: list[str] = []
        self.last_page_state: PageState | None = None
        self.last_action: str | None = None
        self.selected_product: str | None = None
        self.selected_form: str | None = None
        self.cookies: list[dict] = []
        self.storage: dict[str, Any] = {}

    def log_navigation(self, url: str) -> None:
        """Add target URL to navigation history logs."""
        if not self.history or self.history[-1] != url:
            self.history.append(url)

    def reset(self) -> None:
        """Wipe session caches."""
        self.history.clear()
        self.last_page_state = None
        self.last_action = None
        self.selected_product = None
        self.selected_form = None
        self.cookies.clear()
        self.storage.clear()


# Global cache mapping session key strings to memories
session_memories: dict[str, SessionMemory] = {}


def get_session_memory(name: str) -> SessionMemory:
    """Retrieve or instantiate a SessionMemory object for the named session.

    Args:
        name: Name of the session.

    Returns:
        SessionMemory instance.
    """
    if name not in session_memories:
        session_memories[name] = SessionMemory(name)
    return session_memories[name]


def calculate_state_diff(old_state: PageState | None, new_state: PageState) -> StateDiff:
    """Compare elements between current and previous PageState to compute element addition/removal logs.

    Args:
        old_state: Previous PageState context (if any).
        new_state: Updated PageState.

    Returns:
        StateDiff instance.
    """
    if old_state is None:
        # Initial state: treat all elements as newly added elements
        added = []
        for element_list in (new_state.inputs, new_state.buttons, new_state.links, new_state.products):
            added.extend(element_list)

        return StateDiff(
            url=new_state.url,
            title=new_state.title,
            added_elements=added,
            removed_elements=[],
            inputs=new_state.inputs,
            buttons=new_state.buttons,
            links=new_state.links,
            products=new_state.products,
            dialogs=new_state.dialogs,
            notifications=new_state.notifications,
            errors=new_state.errors,
            actions=new_state.actions,
            page_summary=new_state.page_summary
        )

    # Compile lookups keyed by locator selectors
    old_elements = {}
    for element_list in (old_state.inputs, old_state.buttons, old_state.links, old_state.products):
        for element in element_list:
            old_elements[element.locator] = element

    new_elements = {}
    for element_list in (new_state.inputs, new_state.buttons, new_state.links, new_state.products):
        for element in element_list:
            new_elements[element.locator] = element

    added_elements = [el for loc, el in new_elements.items() if loc not in old_elements]
    removed_elements = [el for loc, el in old_elements.items() if loc not in new_elements]

    return StateDiff(
        url=new_state.url,
        title=new_state.title,
        added_elements=added_elements,
        removed_elements=removed_elements,
        inputs=new_state.inputs,
        buttons=new_state.buttons,
        links=new_state.links,
        products=new_state.products,
        dialogs=new_state.dialogs,
        notifications=new_state.notifications,
        errors=new_state.errors,
        actions=new_state.actions,
        page_summary=new_state.page_summary
    )
