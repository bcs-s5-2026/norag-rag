from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.database import DATA_DIR


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    cache_directory = DATA_DIR / "models"
    cache_directory.mkdir(parents=True, exist_ok=True)

    return SentenceTransformer(
        MODEL_NAME,
        device="cpu",
        cache_folder=str(cache_directory),
        trust_remote_code=False,
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    model = get_embedding_model()

    for index, text in enumerate(texts):
        if not text.strip():
            raise ValueError(f"Text at position {index} is empty.")

        token_ids = model.tokenizer(
            text,
            add_special_tokens=True,
            truncation=False,
        )["input_ids"]

        if len(token_ids) > model.max_seq_length:
            raise ValueError(
                f"Text at position {index} contains {len(token_ids)} tokens; "
                f"the embedding limit is {model.max_seq_length}. "
                "Reduce the chunk size or shorten the question."
            )

    vectors = model.encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    expected_shape = (len(texts), EMBEDDING_DIMENSION)

    if vectors.shape != expected_shape:
        raise RuntimeError(
            f"Unexpected embedding shape: {vectors.shape}; "
            f"expected {expected_shape}."
        )

    if not np.isfinite(vectors).all():
        raise RuntimeError("The embedding model returned non-finite values.")

    return vectors.tolist()