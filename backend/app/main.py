from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.database import initialize_database
from app.documents import router as documents_router
from app.chunk_preview import router as chunk_preview_router

from app.indexing import router as indexing_router
from app.retrieval import router as retrieval_router

from app.questions import router as questions_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="RAG Project API",
    description="Question answering over selected document passages.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(retrieval_router)
app.include_router(documents_router)
app.include_router(chunk_preview_router)
app.include_router(indexing_router)
app.include_router(questions_router)

class HealthResponse(BaseModel):
    status: Literal["ok"]


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def get_health() -> HealthResponse:
    return HealthResponse(status="ok")