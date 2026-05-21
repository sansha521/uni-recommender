from pathlib import Path
import boto3
from dotenv import load_dotenv
import json

from sentence_transformers import SentenceTransformer

load_dotenv()

REGION = "us-east-1"
VECTOR_BUCKET = "uni-rec-s3-vector-bucket"
INDEX_NAME = "uni-rec-wikipedia"

DATA_PATH = Path(__file__).parent / "scraping/output/wikipedia_us_universities.jsonl"
COLLECTION_NAME = "universities"
EMBED_MODEL = "multi-qa-mpnet-base-dot-v1"
TEXT_TRUNCATE = 3000

s3vectors = boto3.client("s3vectors", region_name=REGION)

model = SentenceTransformer(EMBED_MODEL)


def main(user_prompt: str) -> None:
    # Embed the prompt
    pass
    embeddings = model.encode(user_prompt).astype("float32").tolist()

    print(type(embeddings))
    print(len(embeddings))
    print(embeddings[:5])

    # Call the Vector Bucket
    response = s3vectors.query_vectors(
        vectorBucketName=VECTOR_BUCKET,
        indexName=INDEX_NAME,
        queryVector={"float32": embeddings},
        topK=5,
        returnDistance=True,
        returnMetadata=True,
    )

    print(json.dumps(response["vectors"], indent=2))


if __name__ == "__main__":
    user_prompt = "Uni in New York City"

    main(user_prompt)
    pass
