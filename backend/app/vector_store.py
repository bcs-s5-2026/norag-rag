from functools import lru_cache

import chromadb

from app.database import DATA_DIR


COLLECTION_NAME = "chapter_chunks_minilm_v1"


@lru_cache(maxsize=1)
def get_collection():
    client = chromadb.PersistentClient(
        path=str(DATA_DIR / "chroma"),
    )

    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
    )