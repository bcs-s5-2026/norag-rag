from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChunkSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_size: int = Field(default=800, ge=100, le=2000, strict=True)
    overlap: int = Field(default=80, ge=0, strict=True)

    @model_validator(mode="after")
    def validate_overlap(self) -> Self:
        if self.overlap >= self.chunk_size:
            raise ValueError("Overlap must be smaller than chunk size.")
        return self


class Chunk(BaseModel):
    index: int
    start: int
    end: int
    text: str


def split_text(text: str, settings: ChunkSettings) -> list[Chunk]:
    if not text.strip():
        return []

    chunks: list[Chunk] = []
    start = 0
    step = settings.chunk_size - settings.overlap

    while start < len(text):
        end = min(start + settings.chunk_size, len(text))

        chunks.append(
            Chunk(
                index=len(chunks),
                start=start,
                end=end,
                text=text[start:end],
            )
        )

        if end == len(text):
            break

        start += step

    return chunks