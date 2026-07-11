"""HTML text extractor utilizing Trafilatura, with metadata preservation, length filtering, and content deduplication."""

import hashlib
import json
import os
import time
from pathlib import Path
import trafilatura
from trafilatura.metadata import extract_metadata

from app.tools.search.schemas import ExtractedDocument
from app.tools.search.utils import log_stage

CACHE_DIR_MARKDOWN = Path(__file__).resolve().parent / "cache" / "markdown"
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours TTL


def _get_cache_path(url: str) -> Path:
    """Generate MD5 hash based markdown metadata cache filepath for a given URL."""
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
    return CACHE_DIR_MARKDOWN / f"{url_hash}.json"


def get_cached_document(url: str) -> ExtractedDocument | None:
    """Retrieve extracted document from cache if it exists and is within TTL."""
    cache_path = _get_cache_path(url)
    if cache_path.exists():
        try:
            mtime = cache_path.stat().st_mtime
            if (time.time() - mtime) < CACHE_TTL_SECONDS:
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                return ExtractedDocument(**data)
            else:
                # Cache expired
                cache_path.unlink()
        except Exception:
            pass
    return None


def cache_document(url: str, doc: ExtractedDocument) -> None:
    """Store extracted document in cache, updating modification time."""
    cache_path = _get_cache_path(url)
    try:
        cache_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    except OSError:
        pass


def extract_document(request_id: str, url: str, html_content: str) -> ExtractedDocument | None:
    """Extract metadata and clean Markdown from raw HTML."""
    # Check cache first
    cached = get_cached_document(url)
    if cached is not None:
        log_stage(request_id, f"Read extracted Markdown cache for: {url}", "info")
        return cached

    # Extract Markdown content
    markdown = trafilatura.extract(
        html_content,
        output_format="markdown",
        include_links=True,
        include_images=False,
        include_tables=True
    )
    
    if not markdown or len(markdown.strip()) < 100:
        log_stage(request_id, f"Discarded page due to insufficient content (< 100 chars): {url}", "warning")
        return None

    # Extract metadata
    meta = extract_metadata(html_content)
    title = (meta.title if meta and meta.title else "").strip()
    language = (meta.language if meta and meta.language else None)
    published = (meta.date if meta and meta.date else None)

    doc = ExtractedDocument(
        title=title,
        url=url,
        markdown=markdown.strip(),
        language=language,
        published=published
    )

    cache_document(url, doc)
    return doc


def extract_and_deduplicate(request_id: str, pages: dict[str, str]) -> list[ExtractedDocument]:
    """Extract content from pages, discarding duplicates and short pages."""
    log_stage(request_id, "📄 Extracting Page Content...")
    
    documents = []
    seen_hashes = set()

    for url, html in pages.items():
        doc = extract_document(request_id, url, html)
        if not doc:
            continue

        # Compute SHA-256 hash of the extracted Markdown text for content deduplication
        content_hash = hashlib.sha256(doc.markdown.encode("utf-8")).hexdigest()
        if content_hash in seen_hashes:
            log_stage(request_id, f"Skipped duplicate page content: {url}", "info")
            continue

        seen_hashes.add(content_hash)
        documents.append(doc)

    return documents
