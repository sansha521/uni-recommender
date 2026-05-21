from pathlib import Path
import json

import boto3
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

REGION = "us-east-1"
VECTOR_BUCKET = "uni-rec-s3-vector-bucket"
INDEX_NAME = "uni-rec-wikipedia"

# DATA_PATH = Path(__file__).parent / "scraping/output/wikipedia_us_universities.jsonl"
# DATA_PATH = Path(__file__).parent / "scraping/output/wikipedia_us_universities.jsonl"
COLLECTION_NAME = "universities"
EMBED_MODEL = "multi-qa-mpnet-base-dot-v1"
TEXT_TRUNCATE = 3000


CHROMA_PATH = "../rag/wikipedia"
COLLECTION_NAME = "universities"

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection(COLLECTION_NAME)

s3vectors = boto3.client("s3vectors", region_name=REGION)

model = SentenceTransformer(EMBED_MODEL)


def main(user_prompt: str) -> str:
    # Embed the prompt
    embeddings = model.encode(user_prompt).astype("float32").tolist()

    # Call the Vector Bucket
    response = s3vectors.query_vectors(
        vectorBucketName=VECTOR_BUCKET,
        indexName=INDEX_NAME,
        queryVector={"float32": embeddings},
        topK=5,
        returnDistance=True,
        returnMetadata=True,
    )

    # print(json.dumps(response["vectors"], indent=2))
    row_id = response["vectors"][0]["key"]
    return row_id


if __name__ == "__main__":
    user_prompt = "Uni in New York City"

    id_from_s3 = main(user_prompt)
    results = collection.get(ids=id_from_s3)
    print(results)

    for doc_id, doc, meta in zip(
        results["ids"], results["documents"], results["metadatas"]
    ):
        print(f"ID: {doc_id}")
        print(f"Document: {doc}")
        print(f"Metadata: {meta}")
        print("---")
