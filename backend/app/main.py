from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.database import initialize_database
from app.documents import router as documents_router


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

app.include_router(documents_router)


class HealthResponse(BaseModel):
    status: Literal["ok"]


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def get_health() -> HealthResponse:
    return HealthResponse(status="ok")