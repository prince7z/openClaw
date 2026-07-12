"""LangChain tool interface wrapper for the Web Search tool."""

import asyncio
import concurrent.futures
from typing import Any
from langchain_core.tools import StructuredTool

from app.tools.search.pipeline import search_pipeline


def _search_sync(
    query: str,
    max_results: int = 5,
    top_k: int = 5,
    cache: bool = False
) -> dict[str, Any]:
    """Search the web for fresh information.

    Retrieves fresh web search results for the given query, downloads the pages in parallel,
    extracts clean Markdown, chunks the content, and reranks the chunks to return the most relevant context.

    Args:
        query: The search query string.
        max_results: Maximum number of search result URLs to fetch. Defaults to 5.
        top_k: Number of final reranked chunks to return. Defaults to 5.
        cache: Set to True to generate embeddings and save extracted chunks to the Qdrant vector database. Defaults to False.

    Returns:
        A structured dict response containing sources, extracted document metadata, reranked chunks, context, and latency metrics.
    """
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Run in a separate thread if an event loop is already running
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    search_pipeline(
                        query=query,
                        max_results=max_results,
                        top_k=top_k,
                        cache=cache
                    )
                )
                response = future.result()
        else:
            response = asyncio.run(
                search_pipeline(
                    query=query,
                    max_results=max_results,
                    top_k=top_k,
                    cache=cache
                )
            )
        return response.model_dump()
    except Exception as exc:
        return {
            "query": query,
            "sources": [],
            "documents": [],
            "chunks": [],
            "context": f"Error running search pipeline: {exc}",
            "execution": {"error": str(exc)}
        }


async def _search_async(
    query: str,
    max_results: int = 5,
    top_k: int = 5,
    cache: bool = False
) -> dict[str, Any]:
    """Search the web for fresh information.

    Retrieves fresh web search results for the given query, downloads the pages in parallel,
    extracts clean Markdown, chunks the content, and reranks the chunks to return the most relevant context.

    Args:
        query: The search query string.
        max_results: Maximum number of search result URLs to fetch. Defaults to 5.
        top_k: Number of final reranked chunks to return. Defaults to 5.
        cache: Set to True to generate embeddings and save extracted chunks to the Qdrant vector database. Defaults to False.

    Returns:
        A structured dict response containing sources, extracted document metadata, reranked chunks, context, and latency metrics.
    """
    try:
        response = await search_pipeline(
            query=query,
            max_results=max_results,
            top_k=top_k,
            cache=cache
        )
        return response.model_dump()
    except Exception as exc:
        return {
            "query": query,
            "sources": [],
            "documents": [],
            "chunks": [],
            "context": f"Error running search pipeline: {exc}",
            "execution": {"error": str(exc)}
        }


web_search = StructuredTool.from_function(
    func=_search_sync,
    coroutine=_search_async,
    name="web_search",
    description=_search_sync.__doc__
)
