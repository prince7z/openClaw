"""Utility helpers for resolving semantic references and layout queries."""

import logging
from app.tools.browser.schemas import PageState

logger = logging.getLogger("openclaw-agent")


def resolve_locator_from_id(state: PageState | None, element_id: str) -> str:
    """Find the stable locator mapped to a visual semantic ID in the PageState.

    If the ID is not found, falls back to returning the ID string itself as a direct selector.

    Args:
        state: The current PageState page structure reference.
        element_id: The visual element ID slug (e.g. btn_login, inp_search).

    Returns:
        The matched stable locator selector string.
    """
    if not state:
        logger.warning("No page state available in memory to resolve semantic visual ID.")
        return element_id

    # Search buttons, inputs, links, and products
    for elem in state.inputs:
        if elem.id == element_id:
            return elem.locator

    for elem in state.buttons:
        if elem.id == element_id:
            return elem.locator

    for elem in state.links:
        if elem.id == element_id:
            return elem.locator

    for elem in state.products:
        if elem.id == element_id:
            return elem.locator

    # Check if element_id is a semantic ID (starts with btn_, inp_, lnk_, prod_)
    if element_id.startswith(("btn_", "inp_", "lnk_", "prod_")):
        available = []
        if element_id.startswith("btn_"):
            available = [e.id for e in state.buttons]
        elif element_id.startswith("inp_"):
            available = [e.id for e in state.inputs]
        elif element_id.startswith("lnk_"):
            available = [e.id for e in state.links]
        elif element_id.startswith("prod_"):
            available = [e.id for e in state.products]
            
        err_msg = f"Element ID '{element_id}' is not visible on the current page."
        if available:
            err_msg += f" Available visible IDs of this type: {', '.join(available)}"
        else:
            err_msg += " No visible elements of this type were found on the page."
        raise ValueError(err_msg)

    # Fallback to direct string selector if no semantic match exists
    return element_id
