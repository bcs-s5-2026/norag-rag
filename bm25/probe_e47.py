# Demo 1: why does embedding search miss error E47?
# Run from the norag-rag folder, with the virtual environment activated:
#   python bm25/probe_e47.py
import re
from pathlib import Path
from sentence_transformers import SentenceTransformer, util

MANUAL = Path(__file__).resolve().parents[1] / "docs" / "vellora-duo-espresso-machine.txt"
QUESTION = "What does error E47 mean and how do I fix it?"
TOP_K = 5  # Matches the default number of chunks retrieved by ask_rag_google.py.
model = SentenceTransformer("all-MiniLM-L6-v2")

# 1. What the embedding model sees
print("1. Tokens:", model.tokenizer.tokenize(QUESTION))

# 2. The code swap: does the question's vector depend on the code?
print("\n2. Same question, different code:")
q = model.encode(QUESTION)
swap_similarities = []
for code in ["E74", "E12", "E99", "E48"]:
    other = QUESTION.replace("E47", code)
    similarity = util.cos_sim(q, model.encode(other)).item()
    swap_similarities.append(similarity)
    print(f"   sim(E47 question, {code} question) = {similarity:.3f}")
print(
    f"   Conclusion: Changing only the code produced similarities from "
    f"{min(swap_similarities):.3f} to {max(swap_similarities):.3f} "
    "(1.0 means the same vector direction).\n"
    "   Similar vectors for different codes can make exact-identifier retrieval unreliable.\n"
    "   This test compares questions, not manual entries."
)

# 3. The real question against every error entry of the manual (one entry per line)
text = open(MANUAL, encoding="utf-8").read()
entries = [line.strip() for line in text.split("\n") if re.match(r"^E\d\d - ", line.strip())]
sims = util.cos_sim(q, model.encode(entries))[0].tolist()
ranked = sorted(zip(sims, entries), reverse=True)
rank = next(i + 1 for i, (_, e) in enumerate(ranked) if e.startswith("E47 "))
print(f"\n3. Question vs the {len(entries)} error entries: the E47 entry ranks #{rank}")
for position, (similarity, entry) in enumerate(ranked[:5], start=1):
    print(f"   #{position}  {similarity:.3f}  {entry[:70]}")
print(
    f"   Conclusion: E47 scores {ranked[rank - 1][0]:.3f}; "
    f"{rank - 1} entries rank ahead of it."
)
if rank <= TOP_K:
    print(f"   A top-{TOP_K} search over individual entries would include E47.")
else:
    print(f"   A top-{TOP_K} search over individual entries would miss E47.")
print("   Entries are ranked by embedding similarity, not by an exact-code match.")

# 4. The real question against the real chunks (same chunking as ask_rag_google.py)
CHUNK_SIZE, OVERLAP_PERCENT, MIN_PARAGRAPH_LENGTH = 800, 10, 20
paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= MIN_PARAGRAPH_LENGTH]
joined = "\n\n".join(paragraphs)
step = CHUNK_SIZE - CHUNK_SIZE * OVERLAP_PERCENT // 100
chunks = [joined[i:i + CHUNK_SIZE] for i in range(0, len(joined), step)]
csims = util.cos_sim(q, model.encode(chunks))[0].tolist()
order = sorted(range(len(chunks)), key=lambda i: csims[i], reverse=True)
e47 = [r + 1 for r, i in enumerate(order) if "E47" in chunks[i]]
print(f"\n4. Question vs the {len(chunks)} chunks: the chunk(s) containing E47 rank {e47}")
for position, i in enumerate(order[:e47[0]], start=1):
    codes = sorted(set(re.findall(r"\bE\d\d\b", chunks[i])))
    print(f"   #{position:2}  {csims[i]:.3f}  codes in chunk: {', '.join(codes) or '-'}")
print(
    f"   Conclusion: The first chunk containing E47 ranks #{e47[0]}; "
    f"at least {e47[0]} results are needed to include it."
)
if e47[0] <= TOP_K:
    print(f"   A top-{TOP_K} search would include an E47-containing chunk.")
else:
    print(f"   A top-{TOP_K} search would miss all E47-containing chunks.")
print(
    "   A chunk containing the code may not contain the complete answer.\n"
    "   This is a cosine ranking of recreated chunks, not a ChromaDB query;\n"
    "   the database's distance metric or index may produce a different ranking."
)
