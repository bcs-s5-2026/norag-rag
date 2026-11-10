from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.answer_contract import INSUFFICIENT_EVIDENCE_MESSAGE
from app.generation import generate_answer
from app.retrieval import (
    RetrievalRequest,
    RetrievedChunk,
    retrieve_chunks,
)


router = APIRouter(prefix="/api/questions", tags=["questions"])


class QuestionResponse(BaseModel):
    question: str
    status: Literal["answered", "insufficient_evidence"]
    answer: str
    citations: list[RetrievedChunk]
    model: str | None


@router.post("", response_model=QuestionResponse)
def ask_question(request: RetrievalRequest) -> QuestionResponse:
    retrieval = retrieve_chunks(request)

    if not retrieval.matches:
        return QuestionResponse(
            question=request.question,
            status="insufficient_evidence",
            answer=INSUFFICIENT_EVIDENCE_MESSAGE,
            citations=[],
            model=None,
        )

    evidence = [
        {
            "chunk_id": chunk.chunk_id,
            "text": chunk.text,
        }
        for chunk in retrieval.matches
    ]

    draft, model_name = generate_answer(
        question=request.question,
        evidence=evidence,
    )

    if draft.status == "insufficient_evidence":
        return QuestionResponse(
            question=request.question,
            status=draft.status,
            answer=INSUFFICIENT_EVIDENCE_MESSAGE,
            citations=[],
            model=model_name,
        )

    chunks_by_id = {
        chunk.chunk_id: chunk
        for chunk in retrieval.matches
    }

    return QuestionResponse(
        question=request.question,
        status="answered",
        answer=draft.answer,
        citations=[
            chunks_by_id[chunk_id]
            for chunk_id in draft.citation_ids
        ],
        model=model_name,
    )