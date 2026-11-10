import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.database import database
from app.embeddings import MODEL_NAME, embed_texts
from app.indexing import index_write_lock
from app.vector_store import get_collection


router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])
logger = logging.getLogger(__name__)


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    question: str = Field(min_length=1, max_length=2000)
    document_ids: list[str] = Field(min_length=1, max_length=50)
    top_k: int = Field(default=5, ge=1, le=20, strict=True)

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]

        if any(not value for value in cleaned):
            raise ValueError("Document IDs cannot be blank.")

        return list(dict.fromkeys(cleaned))


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    index_id: str
    filename: str
    content_hash: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str
    distance: float = Field(allow_inf_nan=False)


class RetrievalResponse(BaseModel):
    question: str
    document_ids: list[str]
    top_k: int
    matches: list[RetrievedChunk]


def retrieve_chunks(request: RetrievalRequest) -> RetrievalResponse:
    if not index_write_lock.acquire(blocking=False):
        raise HTTPException(
            409,
            "Another index operation is running. Retry shortly.",
        )

    try:
        placeholders = ",".join("?" for _ in request.document_ids)

        with database() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    d.id,
                    d.filename,
                    d.content,
                    d.content_hash AS current_hash,
                    i.index_id,
                    i.content_hash AS indexed_hash,
                    i.model_name,
                    i.chunk_count
                FROM documents AS d
                LEFT JOIN document_indexes AS i
                    ON i.document_id = d.id
                WHERE d.id IN ({placeholders})
                """,
                request.document_ids,
            ).fetchall()

        documents = {row["id"]: row for row in rows}

        for document_id in request.document_ids:
            document = documents.get(document_id)

            if document is None:
                raise HTTPException(
                    404,
                    f"Selected document does not exist: {document_id}",
                )

            if document["index_id"] is None:
                raise HTTPException(
                    409,
                    f"Build an index for {document['filename']} first.",
                )

            if (
                document["model_name"] != MODEL_NAME
                or document["current_hash"] != document["indexed_hash"]
            ):
                raise HTTPException(
                    409,
                    f"The index for {document['filename']} is outdated. Rebuild it.",
                )

        try:
            query_vector = embed_texts([request.question])[0]
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

        active_index_ids = [row["index_id"] for row in rows]
        available_chunks = sum(row["chunk_count"] for row in rows)
        result_count = min(request.top_k, available_chunks)

        if result_count < 1:
            raise HTTPException(
                409,
                "The selected indexes contain no chunks. Rebuild them.",
            )

        result = get_collection().query(
            query_embeddings=[query_vector],
            n_results=result_count,
            where={"index_id": {"$in": active_index_ids}},
            include=["documents", "metadatas", "distances"],
        )

        matches: list[RetrievedChunk] = []

        for position, chunk_id in enumerate(result["ids"][0]):
            metadata = result["metadatas"][0][position]
            text = result["documents"][0][position]

            document = documents.get(metadata["document_id"])

            if document is None:
                raise RuntimeError("Retrieval returned an unselected document.")

            if (
                metadata["index_id"] != document["index_id"]
                or metadata["content_hash"] != document["current_hash"]
            ):
                raise RuntimeError("Retrieval returned an outdated chunk.")

            start = metadata["start"]
            end = metadata["end"]

            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or not 0 <= start < end <= len(document["content"])
                or text != document["content"][start:end]
            ):
                raise RuntimeError("Stored chunk does not match its source.")

            expected_id = (
                f"{metadata['index_id']}:{metadata['chunk_index']}"
            )

            if chunk_id != expected_id:
                raise RuntimeError("Stored chunk ID is inconsistent.")

            matches.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=document["id"],
                    index_id=document["index_id"],
                    filename=document["filename"],
                    content_hash=document["current_hash"],
                    start=start,
                    end=end,
                    text=text,
                    distance=result["distances"][0][position],
                )
            )

        if len(matches) != result_count:
            raise RuntimeError("The index returned fewer chunks than expected.")

        return RetrievalResponse(
            question=request.question,
            document_ids=request.document_ids,
            top_k=request.top_k,
            matches=matches,
        )

    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Retrieval failed")
        raise HTTPException(
            503,
            "Retrieval failed. Check the backend logs and index status.",
        ) from error
    finally:
        index_write_lock.release()


@router.post("/search", response_model=RetrievalResponse)
def search(request: RetrievalRequest) -> RetrievalResponse:
    return retrieve_chunks(request)