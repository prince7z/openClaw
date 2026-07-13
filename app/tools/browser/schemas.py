"""Pydantic schemas for Google Playwright Browser Automation tool."""

from pydantic import BaseModel, Field


class BrowserElement(BaseModel):
    """A semantic reference to an interactive DOM element."""
    id: str = Field(description="A short visual ID used by the planner (e.g. btn_login)")
    text: str = Field(description="Text label, placeholder, or value of the element")
    role: str = Field(description="ARIA/HTML role (e.g. button, textbox, link, select)")
    locator: str = Field(description="A stable Playwright locator selector")
    description: str | None = Field(default=None, description="Additional context or surrounding label text")

    class Config:
        populate_by_name = True


class PageState(BaseModel):
    """Pydantic representation of the parsed page state."""
    url: str = Field(description="Active page URL")
    title: str = Field(description="Active page title")
    inputs: list[BrowserElement] = Field(default_factory=list, description="Text fields, checkboxes, selects, and textareas")
    buttons: list[BrowserElement] = Field(default_factory=list, description="Clickable buttons and input submissions")
    links: list[BrowserElement] = Field(default_factory=list, description="Navigation links and anchors")
    products: list[BrowserElement] = Field(default_factory=list, description="Identified product items, prices, and cards")
    dialogs: list[str] = Field(default_factory=list, description="Text of visible dialog alerts, popups, and confirmations")
    notifications: list[str] = Field(default_factory=list, description="Toast notifications and temporary banners")
    errors: list[str] = Field(default_factory=list, description="Error messages and validation warnings detected on the page")
    scroll_position: dict = Field(default_factory=lambda: {"x": 0, "y": 0}, description="Current page scroll coordinates")
    actions: list[str] = Field(default_factory=list, description="Semantic actions suggested for the page (e.g., Login, Search, Add to Cart)")
    page_summary: str = Field(default="", description="A short structural description of the active page layout")


class StateDiff(BaseModel):
    """Represents changes relative to a previous PageState context to optimize token context usage."""
    url: str = Field(description="Active page URL")
    title: str = Field(description="Active page title")
    added_elements: list[BrowserElement] = Field(default_factory=list, description="Interactive elements added since the last check")
    removed_elements: list[BrowserElement] = Field(default_factory=list, description="Interactive elements removed since the last check")
    inputs: list[BrowserElement] = Field(default_factory=list, description="All current text inputs")
    buttons: list[BrowserElement] = Field(default_factory=list, description="All current buttons")
    links: list[BrowserElement] = Field(default_factory=list, description="All current links")
    products: list[BrowserElement] = Field(default_factory=list, description="All current products")
    dialogs: list[str] = Field(default_factory=list, description="Active dialogs")
    notifications: list[str] = Field(default_factory=list, description="Active notifications")
    errors: list[str] = Field(default_factory=list, description="Active errors")
    actions: list[str] = Field(default_factory=list, description="Available semantic actions")
    page_summary: str = Field(default="", description="Short structural summary")
