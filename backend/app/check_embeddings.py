from math import isclose, sqrt

from app.chunking import ChunkSettings, split_text
from app.embeddings import (
    EMBEDDING_DIMENSION,
    MODEL_NAME,
    embed_texts,
    get_embedding_model,
)


def dot_product(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def main() -> None:
    print(f"Loading {MODEL_NAME}...")

    passages = [
        "A raven carried a message to the castle.",
        "The baker mixed flour and water to prepare bread.",
    ]
    question = "Which bird delivered the message?"

    vectors = embed_texts(passages + [question])

    assert len(vectors) == 3
    assert all(len(vector) == EMBEDDING_DIMENSION for vector in vectors)

    for vector in vectors:
        length = sqrt(sum(value * value for value in vector))
        assert isclose(length, 1.0, abs_tol=1e-5)

    question_vector = vectors[-1]
    relevant_score = dot_product(question_vector, vectors[0])
    unrelated_score = dot_product(question_vector, vectors[1])

    print(f"Vectors: {len(vectors)}")
    print(f"Dimensions per vector: {len(vectors[0])}")
    print(f"Raven passage similarity: {relevant_score:.4f}")
    print(f"Bread passage similarity: {unrelated_score:.4f}")

    assert relevant_score > unrelated_score, (
        "The relevant passage did not rank above the unrelated passage."
    )

    source = (
        "A raven carried a message to the castle. "
        "The guards watched the northern gate. "
    ) * 20

    chunks = split_text(
        source,
        ChunkSettings(chunk_size=400, overlap=40),
    )
    chunk_vectors = embed_texts([chunk.text for chunk in chunks])

    assert len(chunk_vectors) == len(chunks)
    print(f"Successfully embedded {len(chunks)} chunks.")

    assert embed_texts([]) == []

    try:
        embed_texts(["raven " * 1000])
    except ValueError as error:
        print(f"Oversized input rejected: {error}")
    else:
        raise AssertionError("Oversized input was silently accepted.")

    assert get_embedding_model() is get_embedding_model()

    print("All embedding checks passed.")


if __name__ == "__main__":
    main()