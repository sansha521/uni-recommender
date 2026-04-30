### Create text embeddings for university reviews
import csv
import numpy as np
import pandas as pd
from pathlib import Path

from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

DATA_PATH = Path(__file__).parent.parent.parent / "datasets/university_reviews.csv"
OUT_PATH = Path(__file__).parent.parent.parent / "rag/reviews"
COLLECTION_NAME = "reviews"
TEXT_TRUNCATE = 3000
BATCH_SIZE = 32

def main():
    df = pd.read_csv(DATA_PATH)
    names = df["name"]
    reviews = df["reviews"]

    print(f"Embedding {len(names)} universities n batches of {BATCH_SIZE}...")
    all_embeddings = []
    for i in range(0, len(names), BATCH_SIZE):
        batch = reviews[i : i + BATCH_SIZE].tolist()
        embeddings = model.encode(batch)
        all_embeddings.extend(embeddings.tolist())
        done = min(i + BATCH_SIZE, len(names))
        print(f"  {done}/{len(names)}", end="\r")

    print()
    print("Storing in output folder...")
    OUT_PATH.mkdir(parents=True, exist_ok=True)
    np.save(OUT_PATH / "embeddings.npy", all_embeddings)
    print(f"Saved {len(all_embeddings)} embeddings to {OUT_PATH}")

    print(f"Done. {len(names)} universities stored.")



if __name__ == "__main__":
    main()