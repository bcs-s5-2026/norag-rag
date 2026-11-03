from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(
    title="RAG Project API",
    description="Question answering over selected document passages.",
    version="0.1.0",
)


class HealthResponse(BaseModel):
    status: Literal["ok"]


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def get_health() -> HealthResponse:
    return HealthResponse(status="ok")