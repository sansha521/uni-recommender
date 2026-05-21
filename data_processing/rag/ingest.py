import json
import os
import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer
import chromadb

DATA_PATH = Path(__file__).parent.parent / "scraping/output/wikipedia_us_universities.jsonl"
CHROMA_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "universities"
EMBED_MODEL = "multi-qa-mpnet-base-dot-v1"
TEXT_TRUNCATE = 3000
BATCH_SIZE = 32

_EXCLUDE_KEYWORDS = [
    "community college", "junior college", "technical college",
    "vocational college", "trade school",
]


def load_universities(path):
    universities = []
    with open(path) as f:
        for line in f:
            entry = json.loads(line.strip())
            if len(entry["text"]) < 300:
                continue
            combined = (entry["name"] + " " + entry["text"][:200]).lower()
            if any(kw in combined for kw in _EXCLUDE_KEYWORDS):
                continue
            universities.append(entry)
    return universities


def main():
    print(f"Loading universities from {DATA_PATH}...")
    universities = load_universities(DATA_PATH)
    print(f"  {len(universities)} valid entries found")

    print(f"Loading embedding model ({EMBED_MODEL})...")
    model = SentenceTransformer(EMBED_MODEL)

    print(f"Setting up ChromaDB at {CHROMA_PATH}...")
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    try:
        client.delete_collection(COLLECTION_NAME)
        print("  Dropped existing collection")
    except Exception:
        pass

    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    texts = [u["text"][:TEXT_TRUNCATE] for u in universities]
    names = [u["name"] for u in universities]

    print(f"Embedding {len(texts)} universities in batches of {BATCH_SIZE}...")
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        embeddings = model.encode(batch, show_progress_bar=False)
        all_embeddings.extend(embeddings.tolist())
        done = min(i + BATCH_SIZE, len(texts))
        print(f"  {done}/{len(texts)}", end="\r")

    print()
    print("Storing in ChromaDB...")
    collection.add(
        ids=[str(i) for i in range(len(universities))],
        embeddings=all_embeddings,
        documents=texts,
        metadatas=[{"name": n} for n in names],
    )

    print(f"Done. {len(universities)} universities stored.")


if __name__ == "__main__":
    main()
