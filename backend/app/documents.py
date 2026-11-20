import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response, UploadFile
from pydantic import BaseModel

from app.database import database


router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILE_BYTES = 2 * 1024 * 1024
ALLOWED_EXTENSIONS = {".md", ".txt"}


class DocumentResponse(BaseModel):
    id: str
    filename: str
    content_hash: str
    character_count: int
    created_at: datetime
    status: Literal["uploaded"] = "uploaded"


def document_response(row: sqlite3.Row) -> DocumentResponse:
    return DocumentResponse(
        id=row["id"],
        filename=row["filename"],
        content_hash=row["content_hash"],
        character_count=row["character_count"],
        created_at=row["created_at"],
    )


@router.get("", response_model=list[DocumentResponse])
def list_documents() -> list[DocumentResponse]:
    with database() as connection:
        rows = connection.execute(
            """
            SELECT id, filename, content_hash, character_count, created_at
            FROM documents
            ORDER BY created_at DESC, id
            """
        ).fetchall()

    return [document_response(row) for row in rows]


@router.post("", response_model=DocumentResponse, status_code=201)
def upload_document(file: UploadFile) -> DocumentResponse:
    try:
        filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]

        if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail="Upload a .md or .txt file.",
            )

        raw_content = file.file.read(MAX_FILE_BYTES + 1)

        if len(raw_content) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="The file must be 2 MiB or smaller.",
            )

        try:
            content = raw_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=422,
                detail="Save the document using UTF-8 encoding.",
            ) from None

        content = content.replace("\r\n", "\n").replace("\r", "\n")

        if not content.strip():
            raise HTTPException(
                status_code=422,
                detail="The document contains no text.",
            )

        if "\x00" in content:
            raise HTTPException(
                status_code=422,
                detail="The document contains unsupported null characters.",
            )

        document = DocumentResponse(
            id=str(uuid4()),
            filename=filename,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            character_count=len(content),
            created_at=datetime.now(timezone.utc),
        )

        try:
            with database() as connection:
                connection.execute(
                    """
                    INSERT INTO documents (
                        id, filename, content, content_hash,
                        character_count, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document.id,
                        document.filename,
                        content,
                        document.content_hash,
                        document.character_count,
                        document.created_at.isoformat(),
                    ),
                )
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=409,
                detail="A document with the same content already exists.",
            ) from None

        return document
    finally:
        file.file.close()


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str) -> Response:
    with database() as connection:
        cursor = connection.execute(
            "DELETE FROM documents WHERE id = ?",
            (document_id,),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Document not found.",
            )

    return Response(status_code=204)