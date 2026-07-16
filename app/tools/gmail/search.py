"""Gmail search tool implementation."""

from typing import Any
from langchain.tools import tool

from app.tools.gmail.executor import execute_gmail_request
from app.tools.gmail.parsers import extract_headers
from app.tools.gmail.schemas import SearchResponse, SearchResult


def _api_search(
    service: Any,
    query: str,
    limit: int,
    page_token: str | None
) -> dict[str, Any]:
    """Execute the raw search API requests to list and load message metadata.

    Args:
        service: Authenticated Gmail service resource.
        query: Gmail query string.
        limit: Limit of results.
        page_token: Page token for pagination.

    Returns:
        A serialized SearchResponse dictionary.
    """
    # List message summaries
    list_res = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=limit,
        pageToken=page_token
    ).execute()

    messages_raw = list_res.get("messages") or []
    next_page_token = list_res.get("nextPageToken")

    messages = []
    for msg in messages_raw:
        msg_id = msg["id"]
        # Fetch metadata headers quickly without downloading full MIME bodies
        detail = service.users().messages().get(
            userId="me",
            id=msg_id,
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]
        ).execute()

        payload = detail.get("payload") or {}
        headers = extract_headers(payload)

        messages.append(
            SearchResult(
                id=msg_id,
                thread_id=detail.get("threadId", ""),
                from_address=headers.get("from", ""),
                to=headers.get("to", ""),
                subject=headers.get("subject", ""),
                date=headers.get("date", ""),
                snippet=detail.get("snippet", "")
            )
        )

    response = SearchResponse(
        success=True,
        messages=messages,
        next_page_token=next_page_token
    )
    return response.model_dump()


@tool("gmail_search")
def gmail_search(
    query: str,
    limit: int = 10,
    page_token: str | None = None
) -> dict[str, Any]:
    """Search Gmail messages using native query syntax.

    Supports Gmail's full native search grammar:
    - from:cisco
    - to:hr
    - label:important
    - category:primary
    - has:attachment
    - older_than:30d
    - newer_than:7d
    - is:unread
    - subject:Interview

    Args:
        query: Native Gmail search query.
        limit: Max results per page. Defaults to 10.
        page_token: Optional token for retrieving next page of results.

    Returns:
        A dict containing success state, list of message metadata, and nextPageToken.
    """
    details = {
        "Query": query,
        "Limit": limit,
        "Page Token": page_token or "None"
    }
    return execute_gmail_request("Search", details, _api_search, query, limit, page_token)
