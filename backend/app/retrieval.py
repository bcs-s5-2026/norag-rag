import os
from functools import lru_cache
from typing import Any, Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# CHECK: these three must match what your indexing code uses.
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "documents")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
# Metadata key that stores which document a chunk came from (used for filtering).
DOC_KEY = os.getenv("DOC_METADATA_KEY", "document_id")

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The user's question")
    top_k: int = Field(5, ge=1, le=50)
    document_ids: Optional[list[str]] = Field(
        None, description="Only search these documents (omit to search all)"
    )


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    distance: float
    score: float  # similarity, higher = closer (NOT a confidence)
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    top_k: int
    results: list[RetrievedChunk]


@lru_cache(maxsize=1)
def _embedding_function() -> SentenceTransformerEmbeddingFunction:
    # Same model as indexing: queries and chunks must share one embedding space.
    return SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)


def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        return client.get_collection(
            name=COLLECTION_NAME, embedding_function=_embedding_function()
        )
    except Exception:
        raise HTTPException(
            status_code=409,
            detail=f"Collection '{COLLECTION_NAME}' not found. Index documents first.",
        )


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query must not be empty.")

    collection = _get_collection()
    total = collection.count()
    if total == 0:
        return SearchResponse(query=query, top_k=req.top_k, results=[])

    where = {DOC_KEY: {"$in": req.document_ids}} if req.document_ids else None

    try:
        raw = collection.query(
            query_texts=[query],
            n_results=min(req.top_k, total),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {exc}")

    ids = raw["ids"][0]
    docs = raw["documents"][0]
    metas = raw["metadatas"][0]
    dists = raw["distances"][0]

    results = [
        RetrievedChunk(
            chunk_id=cid,
            text=doc,
            distance=float(dist),
            score=1.0 - float(dist),  # valid for cosine space; see note below
            metadata=meta or {},
        )
        for cid, doc, meta, dist in zip(ids, docs, metas, dists)
    ]
    return SearchResponse(query=query, top_k=req.top_k, results=results)