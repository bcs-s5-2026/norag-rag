import os
import re
import math
from collections import Counter
from openai import OpenAI
from dotenv import load_dotenv

# This script is the same RAG pipeline as ask_rag_google.py, with ONE difference: the retrieval.
#
# ask_rag_google.py finds the chunks whose MEANING is closest to the question (dense retrieval:
# embeddings + vector search in ChromaDB).
# This script finds the chunks that contain the WORDS of the question, giving more weight to rare words
# (sparse, or lexical, retrieval with BM25).
#
# Everything else is unchanged: the document, the chunking, the prompt and the generation.
# There are no embeddings and no ChromaDB here: BM25 only needs to count words.
#
# See bm25_challenge_part2.md.


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

# The document to index and search
DOCUMENT_FILE = "docs/vellora-duo-espresso-machine.txt"

# Chunking settings: the same as in ask_rag_google.py
CHUNK_SIZE = 800
OVERLAP_PERCENT = 10
MIN_PARAGRAPH_LENGTH = 20

# BM25 settings (these are the usual default values)
# BM25_K1: how quickly a word repeated in a chunk stops adding to the score.
# BM25_B: how much longer-than-average chunks are penalised.
BM25_K1 = 1.5
BM25_B = 0.75


# Chunking: exactly the same as in ask_rag_google.py
def chunk_document(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    # Watch out: paragraphs shorter than MIN_PARAGRAPH_LENGTH characters will be ignored
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= MIN_PARAGRAPH_LENGTH]
    text = "\n\n".join(paragraphs)

    # Simple fixed-size chunking with overlap
    overlap = CHUNK_SIZE * OVERLAP_PERCENT // 100
    step = CHUNK_SIZE - overlap
    return [text[i:i + CHUNK_SIZE] for i in range(0, len(text), step)]


# BM25 works on words, not on meaning.
# "What does error E47 mean?" -> ["what", "does", "error", "e47", "mean"]
def tokenize(text):
    return re.findall(r"\w+", text.lower())


# A minimal BM25 index. It is cheap to build, so we rebuild it in memory at every run.
class BM25Index:
    def __init__(self, chunks):
        self.chunks = chunks
        # How many times each word appears in each chunk
        self.word_counts = [Counter(tokenize(chunk)) for chunk in chunks]
        self.chunk_lengths = [sum(counts.values()) for counts in self.word_counts]
        self.average_length = sum(self.chunk_lengths) / len(chunks)
        # In how many chunks each word appears
        self.chunk_frequency = Counter()
        for counts in self.word_counts:
            self.chunk_frequency.update(counts.keys())

    # Inverse document frequency: a word found in only a few chunks gets a high weight,
    # a word found in almost every chunk ("the", "what", "error"...) gets a weight close to zero.
    def idf(self, word):
        n = len(self.chunks)
        df = self.chunk_frequency[word]
        return math.log((n - df + 0.5) / (df + 0.5) + 1)

    # The score of one chunk: the sum, over the words of the query, of
    # (weight of the word) x (how often it appears in the chunk, with diminishing returns and length normalisation)
    def score(self, query, i):
        counts = self.word_counts[i]
        length_ratio = self.chunk_lengths[i] / self.average_length
        total = 0.0
        for word in tokenize(query):
            tf = counts[word]
            if tf == 0:
                continue
            total += self.idf(word) * tf * (BM25_K1 + 1) / (tf + BM25_K1 * (1 - BM25_B + BM25_B * length_ratio))
        return total

    def search(self, query, n_results):
        scores = [self.score(query, i) for i in range(len(self.chunks))]
        best = sorted(range(len(self.chunks)), key=lambda i: scores[i], reverse=True)[:n_results]
        return [(self.chunks[i], scores[i]) for i in best]


# get_rag_context(index, query, n_results=5) performs a BM25 search
# to retrieve the most relevant snippets based on the query.
def get_rag_context(index, query, n_results=5):
    results = index.search(query, n_results)
    print("BM25 scores of the retrieved chunks: " + ", ".join(f"{score:.2f}" for _, score in results))
    return "\n---\n".join(chunk for chunk, _ in results)

# Generation Logic: exactly the same as in ask_rag_google.py
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

    chunks = chunk_document(DOCUMENT_FILE)
    index = BM25Index(chunks)
    print(f"Built a BM25 index of {len(chunks)} chunks from {DOCUMENT_FILE} (in memory).")

    question = "What does error E47 mean and how do I fix it?"

    print(f"\n--- RAG RETRIEVAL START ---")
    context = get_rag_context(index, question, n_results=5)

    # Debug - print the retrieved context to verify it's working
    print(f"Retrieved context:\n{context}")

    continue_processing = True
    if continue_processing:
        print(f"Retrieved relevant snippets. Sending to Gemini...")
        print(f"--- RESPONSE ---\n")

        generate_response(question, context)


if __name__ == "__main__":
  try:
    main()
  except Exception as e:
    print(f"An error occurred: {e}")
