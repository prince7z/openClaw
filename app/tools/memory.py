"""LangChain tool interface wrapper for retrieve_memory."""

import asyncio
from typing import Literal, List
from langchain.tools import tool
from concurrent.futures import ThreadPoolExecutor


def run_async_sync(coro):
    """Run an async coroutine synchronously, even if an event loop is running in the current thread.

    Useful for executing async DB and Embedding calls inside synchronous LangChain tool executors.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    if loop.is_running():
        # Run in a separate thread to prevent "Event loop is already running" error
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(coro))
            return future.result()
    else:
        return loop.run_until_complete(coro)


@tool("retrieve_memory")
def retrieve_memory(
    query: str,
    sources: List[Literal["conversation", "semantic", "episodic"]] | None = None
) -> str:
    """Retrieve relevant details or context from long-term memory sources.

    Use this tool whenever information may exist in:
    - previous conversations
    - persistent user facts (identity, preferences, skills, habits)
    - project decisions or architecture discussions
    - previous debugging sessions or issues resolved
    - historical discussions

    Do NOT use this tool for information that is already present in the current active conversation history.

    Args:
        query: Concise semantic search query to look for in memory archives.
        sources: Optional but imp to list of target memory sources to search. Can include any of:
                 - "conversation": Summaries of past chat sessions (SQLite).
                 - "semantic": Long-term persistent user details (Qdrant).
                 - "episodic": Logged experiences/debugging sessions (Qdrant).
                 If not provided, searches all sources.think where can data be stored tht u needed.
    """
    from app.conversation.manager import ConversationManager
    manager = ConversationManager()
    return run_async_sync(manager.retrieve_memory_context(query, sources))
