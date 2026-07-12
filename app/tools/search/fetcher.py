"""Asynchronous page fetcher with local HTML caching, binary detection, and concurrency control."""

import asyncio
import hashlib
import os
import time
from pathlib import Path
import httpx

from app.tools.search.utils import log_stage

CACHE_DIR_HTML = Path(__file__).resolve().parent / "cache" / "html"
CACHE_DIR_MARKDOWN = Path(__file__).resolve().parent / "cache" / "markdown"
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours TTL

# Create cache directories
CACHE_DIR_HTML.mkdir(parents=True, exist_ok=True)
CACHE_DIR_MARKDOWN.mkdir(parents=True, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
SEMAPHORE = asyncio.Semaphore(5)


def _get_cache_path(url: str) -> Path:
    """Generate MD5 hash based HTML cache filepath for a given URL."""
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
    return CACHE_DIR_HTML / f"{url_hash}.html"


def get_cached_html(url: str) -> str | None:
    """Retrieve HTML from cache if it exists and is within TTL."""
    cache_path = _get_cache_path(url)
    if cache_path.exists():
        mtime = cache_path.stat().st_mtime
        if (time.time() - mtime) < CACHE_TTL_SECONDS:
            return cache_path.read_text(encoding="utf-8")
        else:
            # Cache expired
            try:
                cache_path.unlink()
            except OSError:
                pass
    return None


def cache_html(url: str, html: str) -> None:
    """Store HTML content in cache, updating the modification time."""
    cache_path = _get_cache_path(url)
    try:
        cache_path.write_text(html, encoding="utf-8")
    except OSError:
        pass


async def _should_skip_binary(request_id: str, client: httpx.AsyncClient, url: str) -> bool:
    """Check if the target URL points to a binary file using a HEAD request."""
    # Fast path check on typical file extensions
    lower_url = url.lower()
    binary_extensions = (".zip", ".exe", ".pdf", ".docx", ".xlsx", ".pptx", ".epub", ".png", ".jpg", ".jpeg", ".gif", ".mp3", ".mp4", ".wav", ".avi")
    if lower_url.endswith(binary_extensions):
        return True

    try:
        response = await client.request("HEAD", url, headers={"User-Agent": USER_AGENT}, timeout=5.0, follow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "").lower()
            if any(t in content_type for t in ("image/", "video/", "audio/", "application/zip", "application/x-", "application/octet-stream")):
                return True
    except Exception:
        # Fall back to GET if HEAD request fails (some sites reject HEAD)
        pass
    return False


async def fetch_page(request_id: str, client: httpx.AsyncClient, url: str, retries: int = 2) -> str | None:
    """Fetch raw HTML content of a single page, respecting caching, TTL, and binary exclusions."""
    # Check cache first
    cached = get_cached_html(url)
    if cached is not None:
        log_stage(request_id, f"Read HTML cache for: {url}", "info")
        return cached

    async with SEMAPHORE:
        # Check if url contains unsupported binary formats
        if await _should_skip_binary(request_id, client, url):
            log_stage(request_id, f"Skipping unsupported binary content: {url}", "warning")
            return None

        for attempt in range(retries + 1):
            try:
                response = await client.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=10.0,
                    follow_redirects=True
                )
                if response.status_code == 200:
                    html_content = response.text
                    cache_html(url, html_content)
                    return html_content
                else:
                    log_stage(request_id, f"Failed fetch {url} (status: {response.status_code})", "warning")
            except (httpx.HTTPError, asyncio.TimeoutError) as exc:
                if attempt == retries:
                    log_stage(request_id, f"Error fetching {url}: {exc}", "error")
                else:
                    await asyncio.sleep(1.0 * (attempt + 1))  # exponential backoff
    return None


async def fetch_all_pages(request_id: str, urls: list[str]) -> dict[str, str]:
    """Fetch HTML pages in parallel with concurrency semaphore limits."""
    log_stage(request_id, "⬇ Fetching Pages...")
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [fetch_page(request_id, client, url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        pages = {}
        for url, html in zip(urls, results):
            if html:
                pages[url] = html
        return pages
