from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.chunking import Chunk, ChunkSettings, split_text
from app.database import database


router = APIRouter(prefix="/api/chunks", tags=["chunks"])


class ChunkPreviewRequest(BaseModel):
    document_id: str = Field(min_length=1)
    settings: ChunkSettings = Field(default_factory=ChunkSettings)


class ChunkPreviewResponse(BaseModel):
    document_id: str
    filename: str
    content_hash: str
    settings: ChunkSettings
    total_chunks: int
    preview: list[Chunk]


@router.post("/preview", response_model=ChunkPreviewResponse)
def preview_chunks(request: ChunkPreviewRequest) -> ChunkPreviewResponse:
    with database() as connection:
        document = connection.execute(
            """
            SELECT id, filename, content, content_hash
            FROM documents
            WHERE id = ?
            """,
            (request.document_id,),
        ).fetchone()

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    chunks = split_text(document["content"], request.settings)

    return ChunkPreviewResponse(
        document_id=document["id"],
        filename=document["filename"],
        content_hash=document["content_hash"],
        settings=request.settings,
        total_chunks=len(chunks),
        preview=chunks[:5],
    )