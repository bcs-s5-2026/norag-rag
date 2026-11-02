import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# This script demonstrates a simple "Needle in a Haystack" scenario,
# where we have a large context of text (the "haystack")
# and we want to see if the model can find a specific piece of information (the "needle")
# when asked a question about it.

# In that scenario, we will use the full text of 'Crime and Punishment' by Fyodor Dostoevsky as our haystack,
# in which we have already injected a specific piece of information about a character named Denis.


# for this to work, you need to set the GOOGLE_API_KEY environment variable
# with your API key from https://aistudio.google.com/api-keys

# Setup OpenAI client pointing to Google's OpenAI-compatible endpoint
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = OpenAI(api_key=api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

# Gemini model used for generation. Any model listed at https://ai.google.dev/gemini-api/docs/models
# (or returned by list_available_models() below) should work. Models get retired over time.
# Validated as working on 2026-10-19: gemini-2.5-flash-lite, gemini-2.5-flash, gemini-3-flash-preview, gemini-3.5-flash-lite.
# Free tier quotas are per model: if you get a 429 error, switching to another model is a quick workaround.
MODEL = "gemini-3.5-flash-lite"
STREAM_ON = True

# Use this function to list available models and their details
def list_available_models():
    print("Available models:")
    models = client.models.list()
    for m in models:
        print(f"  id: {m.id}")

# Setup ChromaDB with LOCAL Embeddings.
# The model used to generate embeddings is "all-MiniLM-L6-v2", which is a small but effective model for many tasks.
# See https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 for more details.
# This model runs on your machine. No API calls, no quotas, and very fast.
local_ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# The document to index and search
DOCUMENT_FILE = "docs/CrimeAndPunishment.txt"

# Chunking settings
# CHUNK_SIZE is in characters. 800 characters are about 190 tokens, which stays under the
# 256-token limit of the embedding model (text beyond that limit is silently ignored when embedding).
CHUNK_SIZE = 800
# Each chunk starts with the last OVERLAP_PERCENT % of the previous chunk,
# so that a sentence cut at the end of a chunk can still be found complete in the next one.
OVERLAP_PERCENT = 10
# Paragraphs shorter than this (in characters) are ignored: chapter headings, "He scowled.", ...
MIN_PARAGRAPH_LENGTH = 20

# We'll use a persistent client so you don't have to re-index every time you run the script
chroma_client = chromadb.PersistentClient(path="./chroma_db")
# One collection per document and chunking configuration: if you change the document or the settings above,
# the script will offer to build a new index for them.
# Note: the name depends on the document's file NAME, not on its content.
DOCUMENT_NAME = os.path.splitext(os.path.basename(DOCUMENT_FILE))[0]
COLLECTION_NAME = f"{DOCUMENT_NAME}_{CHUNK_SIZE}_{OVERLAP_PERCENT}_{MIN_PARAGRAPH_LENGTH}"

# Create or get the collection where we will store our document chunks and their embeddings
collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME, 
    embedding_function=local_ef
)

# RAG Logic: Processing the file
# The idea is to index the text of 'Crime and Punishment'
# into a local ChromaDB collection, and then perform a similarity search 
# to retrieve relevant snippets based on a question, which will then be sent to the model 
# for generating a response.
def index_document(filepath):
    if collection.count() > 0:
        print("Collection already indexed. Skipping...")
        return

    print(f"Indexing {filepath} locally (this will take a moment)...")
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    
    # Watch out: paragraphs shorter than MIN_PARAGRAPH_LENGTH characters will be ignored
    # Question: (when) does it make sense to ignore very short paragraphs?
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= MIN_PARAGRAPH_LENGTH]
    text = "\n\n".join(paragraphs)

    # Simple fixed-size chunking with overlap:
    # a window of CHUNK_SIZE characters slides over the text, moving forward by (CHUNK_SIZE - overlap)
    # characters each time. Chunks can start or end in the middle of a word or a sentence.
    overlap = CHUNK_SIZE * OVERLAP_PERCENT // 100
    step = CHUNK_SIZE - overlap
    chunks = [text[i:i + CHUNK_SIZE] for i in range(0, len(text), step)]

    # Indexing locally is much faster—no batching for quotas needed!
    # But ChromaDB accepts at most ~5000 chunks per call, so with small chunk sizes we add them in batches.
    BATCH_SIZE = 5000
    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]
        collection.add(
            documents=batch,
            ids=[f"id_{i}" for i in range(start, start + len(batch))]
        )
    print(f"Indexed {len(chunks)} chunks locally.")


# get_rag_context(query, n_results=5) performs a similarity search in the ChromaDB collection 
# to retrieve the most relevant snippets based on the query.
def get_rag_context(query, n_results=5):
    # Search the vector DB for the most relevant snippets
    results = collection.query(query_texts=[query], n_results=n_results)
    # Flatten the list of documents retrieved
    return "\n---\n".join(results['documents'][0])

# Generation Logic
# Build a prompt that includes the retrieved context and the question,
# and send it to the model to generate a response.
def generate_response(question, context):
    full_prompt = f"""
    You are a literary analyst. Using only the following excerpts from the book,
    answer the question provided. If the information is not in the excerpts, say you don't know.

    EXCERPTS:
    {context}

    QUESTION:
    {question}
    """

    if STREAM_ON:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end='', flush=True)
    else:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": full_prompt}]
        )
        print(response.choices[0].message.content)

# Execution
def main():

    # Optional: List Google models
    # list_available_models()

    # Only index once per document and chunking configuration, and only if the user agrees
    if collection.count() == 0:
        answer = input(f"No index found for this document and these chunking settings (collection '{COLLECTION_NAME}').\n"
                       f"Index {DOCUMENT_FILE} now? [y/N] ")
        if answer.strip().lower() != "y":
            print("Indexing cancelled. Nothing to search in, exiting.")
            return
        index_document(DOCUMENT_FILE)
    else:
        print(f"Using existing index '{COLLECTION_NAME}' ({collection.count()} chunks).")

    question = "What does this say about Denis?"
    
    print(f"\n--- RAG RETRIEVAL START ---")
    context = get_rag_context(question, n_results=5)

    # Debug - print the retrieved context to verify it's working
    print(f"Retrieved context:\n{context}")

    continue_processing = True
    if continue_processing:
        print(f"Retrieved relevant snippets. Sending to Gemini...")
        print(f"--- RESPONSE ---\n")
    
        generate_response(question, context)


# Note: You can run this script multiple times without re-indexing, 
# since the ChromaDB client is persistent and checks if the collection already has data before indexing again.

if __name__ == "__main__":
  try:
    main()
  except Exception as e:
    print(f"An error occurred: {e}")