from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


INSUFFICIENT_EVIDENCE_MESSAGE = (
    "The selected document excerpts do not contain enough information "
    "to answer this question."
)


class DraftAnswer(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    status: Literal["answered", "insufficient_evidence"]
    answer: str = Field(min_length=1, max_length=8000)
    citation_ids: list[str] = Field(max_length=20)

    @model_validator(mode="after")
    def validate_status_and_citations(self) -> Self:
        if self.status == "answered" and not self.citation_ids:
            raise ValueError("An answered response must cite evidence.")

        if self.status == "insufficient_evidence" and self.citation_ids:
            raise ValueError(
                "An insufficient-evidence response must have no citations."
            )

        if len(self.citation_ids) != len(set(self.citation_ids)):
            raise ValueError("Citation IDs must be unique.")

        return self


def validate_answer(
    raw_response: str,
    allowed_citation_ids: set[str],
) -> DraftAnswer:
    answer = DraftAnswer.model_validate_json(raw_response)

    unknown_ids = set(answer.citation_ids) - allowed_citation_ids

    if unknown_ids:
        raise ValueError("The model cited evidence that was not retrieved.")

    return answer