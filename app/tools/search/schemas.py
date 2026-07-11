"""Pydantic schemas for the Search Tool."""

from typing import Any
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """A raw search result from the web search provider."""
    title: str = Field(description="Title of the search result page")
    url: str = Field(description="URL of the page")
    content: str = Field(description="Brief snippet or description returned by search")


class ExtractedDocument(BaseModel):
    """An extracted page document converted into clean Markdown."""
    title: str = Field(default="", description="Title of the webpage")
    url: str = Field(description="URL of the webpage")
    markdown: str = Field(description="Extracted clean Markdown content")
    language: str | None = Field(default=None, description="Inferred language of the page content")
    published: str | None = Field(default=None, description="Inferred publication date/time of the page content")


class Chunk(BaseModel):
    """A chunk of text split from an extracted document."""
    id: str = Field(description="Unique identifier of the chunk")
    content: str = Field(description="Content text of the chunk")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata associated with the chunk (e.g. source url)")
    score: float = Field(default=0.0, description="Rerank or relevance score of the chunk")


class SearchResponse(BaseModel):
    """The structured output format returned by the Search Tool."""
    query: str = Field(description="Original search query")
    sources: list[SearchResult] = Field(description="List of search result sources")
    documents: list[ExtractedDocument] = Field(description="List of successfully fetched and extracted documents")
    chunks: list[Chunk] = Field(description="List of top reranked chunks")
    context: str = Field(description="Aggregated Markdown text context for the agent planner")
    execution: dict[str, float] = Field(description="Execution latency metrics in milliseconds")
