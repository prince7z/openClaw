"""Web search orchestrator pipeline."""

import time

from app.tools.search.schemas import SearchResponse
from app.tools.search.tavily import search_tavily
from app.tools.search.fetcher import fetch_all_pages
from app.tools.search.extractor import extract_and_deduplicate
from app.database.vector.chunker import chunk_documents
from app.database.vector.reranker import rerank_chunks
from app.database.vector.embedder import generate_embeddings
from app.tools.search.vectorstore import save_chunks_to_qdrant
from app.tools.search.utils import (
    generate_request_id,
    log_stage,
    log_border,
    console
)


async def search_pipeline(
    query: str,
    max_results: int = 5,
    top_k: int = 5,
    cache: bool = False
) -> SearchResponse:
    """Orchestrate the async search pipeline.

    Args:
        query: The search query.
        max_results: The maximum number of URLs to retrieve from Tavily.
        top_k: The number of top reranked chunks to return.
        cache: Whether to embed and cache chunks in Qdrant.

    Returns:
        A SearchResponse containing the parsed documents, top chunks, aggregated context, and latency metrics.
    """
    request_id = generate_request_id()
    total_start = time.time()

    log_border(request_id)
    log_stage(request_id, "🌍 Search Started", "stage")
    log_border(request_id)
    log_stage(request_id, f"🔎 Query: {query}", "query")

    # 1. Search Tavily
    search_start = time.time()
    sources = await search_tavily(request_id, query, max_results=max_results)
    search_ms = int((time.time() - search_start) * 1000)

    if not sources:
        log_border(request_id)
        log_stage(request_id, "✅ Search Complete (No results found)", "success")
        log_border(request_id)
        return SearchResponse(
            query=query,
            sources=[],
            documents=[],
            chunks=[],
            context="No search results were found for this query.",
            execution={"total_ms": int((time.time() - total_start) * 1000)}
        )

    # 2. Fetch raw HTML pages asynchronously in parallel
    fetch_start = time.time()
    urls = [s.url for s in sources]
    pages = await fetch_all_pages(request_id, urls)
    fetch_ms = int((time.time() - fetch_start) * 1000)

    # 3. Extract Markdown text, clean scripts/ads, and deduplicate page contents
    extract_start = time.time()
    documents = extract_and_deduplicate(request_id, pages)
    extract_ms = int((time.time() - extract_start) * 1000)

    # 4. Chunk Extracted documents
    chunks = chunk_documents(request_id, documents)

    # 5. Rerank Chunks directly (Query vs Chunks cross-encoder comparison)
    rerank_start = time.time()
    reranked_chunks = await rerank_chunks(request_id, query, chunks, top_k=top_k)
    rerank_ms = int((time.time() - rerank_start) * 1000)

    # 6. Conditionally embed and cache all chunks in Qdrant if cache=True
    embedding_ms = 0
    qdrant_ms = 0
    if cache and chunks:
        embed_start = time.time()
        chunk_texts = [c.content for c in chunks]
        embeddings = await generate_embeddings(request_id, chunk_texts)
        embedding_ms = int((time.time() - embed_start) * 1000)

        qdrant_start = time.time()
        save_chunks_to_qdrant(request_id, chunks, embeddings)
        qdrant_ms = int((time.time() - qdrant_start) * 1000)

    # Aggregate top reranked chunks into clean Markdown formatted context for LLM consumption
    context_sections = []
    for chunk in reranked_chunks:
        title = chunk.metadata.get("title") or "Web Source"
        url = chunk.metadata.get("url") or ""
        context_sections.append(
            f"Source: {title} ({url})\nRelevance Score: {chunk.score:.4f}\nContent:\n{chunk.content}"
        )
    context = "\n\n---\n\n".join(context_sections)

    total_ms = int((time.time() - total_start) * 1000)
    execution_metrics = {
        "search_ms": search_ms,
        "fetch_ms": fetch_ms,
        "extract_ms": extract_ms,
        "rerank_ms": rerank_ms,
        "total_ms": total_ms
    }
    if cache:
        execution_metrics["embedding_ms"] = embedding_ms
        execution_metrics["qdrant_ms"] = qdrant_ms

    log_border(request_id)
    log_stage(request_id, "✅ Search Complete", "success")
    log_stage(request_id, f"⏱ [time] Total execution time: {total_ms}ms[/] (Fetch: {fetch_ms}ms, Extract: {extract_ms}ms, Rerank: {rerank_ms}ms)", "time")
    log_border(request_id)

    return SearchResponse(
        query=query,
        sources=sources,
        documents=documents,
        chunks=reranked_chunks,
        context=context,
        execution=execution_metrics
    )
