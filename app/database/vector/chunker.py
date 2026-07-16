"""Markdown document chunker using RecursiveCharacterTextSplitter."""

import hashlib
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.tools.search.schemas import ExtractedDocument, Chunk
from app.tools.search.utils import log_stage


def chunk_documents(request_id: str, documents: list[ExtractedDocument]) -> list[Chunk]:
    """Split extracted Markdown documents into overlapping chunks.

    Args:
        request_id: Unique request session identifier.
        documents: A list of ExtractedDocument models.

    Returns:
        A list of Chunk models containing chunk content and page metadata.
    """
    log_stage(request_id, "✂ Chunking Documents...")

    # Initialize standard RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        length_function=len
    )

    chunks = []
    for doc in documents:
        # Split document text into chunks
        split_texts = splitter.split_text(doc.markdown)
        
        doc_hash = hashlib.md5(doc.url.encode("utf-8")).hexdigest()[:8]
        
        for idx, text in enumerate(split_texts):
            chunk_id = f"{doc_hash}_{idx}"
            metadata = {
                "url": doc.url,
                "title": doc.title,
                "language": doc.language,
                "published": doc.published
            }
            chunks.append(
                Chunk(
                    id=chunk_id,
                    content=text,
                    metadata=metadata,
                    score=0.0
                )
            )

    log_stage(request_id, f"✂ Generated {len(chunks)} Chunks")
    return chunks
