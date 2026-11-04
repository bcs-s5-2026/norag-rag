import logging
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.chunking import ChunkSettings, split_text
from app.database import database
from app.embeddings import MODEL_NAME, embed_texts
from app.vector_store import get_collection


router = APIRouter(prefix="/api/indexes", tags=["indexes"])
logger = logging.getLogger(__name__)

# Serializes rebuilding and deletion in our single server process.
index_write_lock = Lock()


class BuildIndexRequest(BaseModel):
    document_id: str = Field(min_length=1)
    settings: ChunkSettings = Field(default_factory=ChunkSettings)


class IndexResponse(BaseModel):
    document_id: str
    index_id: str
    content_hash: str
    model_name: str
    chunk_size: int
    overlap: int
    chunk_count: int
    created_at: datetime


def read_index(document_id: str) -> IndexResponse:
    with database() as connection:
        document = connection.execute(
            "SELECT id FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()

        if document is None:
            raise HTTPException(404, "Document not found.")

        row = connection.execute(
            "SELECT * FROM document_indexes WHERE document_id = ?",
            (document_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(409, "This document has not been indexed.")

    return IndexResponse(**dict(row))


def cleanup_index(index_id: str) -> None:
    try:
        get_collection().delete(where={"index_id": index_id})
    except Exception:
        logger.exception("Could not remove unused index %s", index_id)


@router.post("/rebuild", response_model=IndexResponse)
def rebuild_index(request: BuildIndexRequest) -> IndexResponse:
    if not index_write_lock.acquire(blocking=False):
        raise HTTPException(409, "Another index operation is running. Retry shortly.")

    new_index_id = str(uuid4())
    published = False

    try:
        with database() as connection:
            document = connection.execute(
                "SELECT * FROM documents WHERE id = ?",
                (request.document_id,),
            ).fetchone()

            old_index = connection.execute(
                "SELECT index_id FROM document_indexes WHERE document_id = ?",
                (request.document_id,),
            ).fetchone()

        if document is None:
            raise HTTPException(404, "Document not found.")

        chunks = split_text(document["content"], request.settings)

        if not chunks:
            raise HTTPException(422, "The document contains no usable text.")

        collection = get_collection()

        for offset in range(0, len(chunks), 64):
            batch = chunks[offset:offset + 64]

            try:
                vectors = embed_texts([chunk.text for chunk in batch])
            except ValueError as error:
                raise HTTPException(422, str(error)) from error

            collection.add(
                ids=[f"{new_index_id}:{chunk.index}" for chunk in batch],
                embeddings=vectors,
                documents=[chunk.text for chunk in batch],
                metadatas=[
                    {
                        "document_id": document["id"],
                        "index_id": new_index_id,
                        "content_hash": document["content_hash"],
                        "filename": document["filename"],
                        "chunk_index": chunk.index,
                        "start": chunk.start,
                        "end": chunk.end,
                    }
                    for chunk in batch
                ],
            )

        result = IndexResponse(
            document_id=document["id"],
            index_id=new_index_id,
            content_hash=document["content_hash"],
            model_name=MODEL_NAME,
            chunk_size=request.settings.chunk_size,
            overlap=request.settings.overlap,
            chunk_count=len(chunks),
            created_at=datetime.now(timezone.utc),
        )

        with database() as connection:
            connection.execute(
                """
                INSERT INTO document_indexes (
                    document_id, index_id, content_hash, model_name,
                    chunk_size, overlap, chunk_count, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    index_id = excluded.index_id,
                    content_hash = excluded.content_hash,
                    model_name = excluded.model_name,
                    chunk_size = excluded.chunk_size,
                    overlap = excluded.overlap,
                    chunk_count = excluded.chunk_count,
                    created_at = excluded.created_at
                """,
                (
                    result.document_id,
                    result.index_id,
                    result.content_hash,
                    result.model_name,
                    result.chunk_size,
                    result.overlap,
                    result.chunk_count,
                    result.created_at.isoformat(),
                ),
            )

        published = True

        if old_index is not None:
            cleanup_index(old_index["index_id"])

        return result

    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Indexing failed for document %s", request.document_id)
        raise HTTPException(
            503,
            "Indexing failed. Check the backend logs and retry.",
        ) from error
    finally:
        if not published:
            cleanup_index(new_index_id)
        index_write_lock.release()


@router.get("/{document_id}", response_model=IndexResponse)
def get_index(document_id: str) -> IndexResponse:
    return read_index(document_id)


@router.get("/{document_id}/preview")
def preview_stored_index(document_id: str):
    with index_write_lock:
        index = read_index(document_id)

        try:
            result = get_collection().get(
                ids=[
                    f"{index.index_id}:{number}"
                    for number in range(min(5, index.chunk_count))
                ],
                include=["documents", "metadatas", "embeddings"],
            )

            preview = [
                {
                    "id": chunk_id,
                    "text": result["documents"][position],
                    "metadata": result["metadatas"][position],
                    "embedding_dimension": len(result["embeddings"][position]),
                }
                for position, chunk_id in enumerate(result["ids"])
            ]

            preview.sort(key=lambda item: item["metadata"]["chunk_index"])

            if len(preview) != min(5, index.chunk_count):
                raise RuntimeError("Stored chunks are missing.")

        except Exception as error:
            logger.exception("Could not read index %s", index.index_id)
            raise HTTPException(
                503,
                "The stored index could not be read. Try rebuilding it.",
            ) from error

        return {"index": index, "preview": preview}