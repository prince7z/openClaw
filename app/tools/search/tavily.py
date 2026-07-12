"""Tavily search API client wrapper."""

import httpx
from app.config import Tavily_api_key
from app.tools.search.schemas import SearchResult
from app.tools.search.utils import log_stage, log_border


async def search_tavily(request_id: str, query: str, max_results: int = 5) -> list[SearchResult]:
    """Search Tavily for the given query and return parsed results.

    Args:
        request_id: The request session identifier.
        query: The search text query.
        max_results: The maximum number of results to retrieve.

    Returns:
        A list of SearchResult models containing title, url, and content.
    """
    log_stage(request_id, "Searching Tavily...")

    if not Tavily_api_key:
        log_stage(request_id, "Warning: TAVILY_API_KEY is not configured.", "warning")
        return []

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": Tavily_api_key,
        "query": query,
        "max_results": max_results,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = client.post(url, json=payload)
        response = await response

        if response.status_code != 200:
            log_stage(request_id, f"Error: Tavily API returned status code {response.status_code}", "error")
            return []

        data = response.json()
        raw_results = data.get("results") or []
        
        results = []
        for item in raw_results:
            results.append(
                SearchResult(
                    title=item.get("title") or "",
                    url=item.get("url") or "",
                    content=item.get("content") or ""
                )
            )
            
        log_stage(request_id, f"🌐 {len(results)} URLs Found")
        return results
