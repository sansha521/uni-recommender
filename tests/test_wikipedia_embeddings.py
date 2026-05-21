from pathlib import Path
import boto3
from dotenv import load_dotenv

from sentence_transformers import SentenceTransformer
import chromadb

load_dotenv()

REGION = "us-east-1"
VECTOR_BUCKET = "uni-rec-s3-vector-bucket"
INDEX_NAME = "uni-rec-index"

DATA_PATH = Path(__file__).parent / "scraping/output/wikipedia_us_universities.jsonl"
COLLECTION_NAME = "universities"
EMBED_MODEL = "multi-qa-mpnet-base-dot-v1"
TEXT_TRUNCATE = 3000


s3vectors = boto3.client("s3vectors", region_name=REGION)


def main(user_prompt: str) -> None:
    # Embed the prompt
    pass
    embeddings = EMBED_MODEL.encode(user_prompt)

    # Call the Vector Bucket
    response = s3vectors.query_vectors(
        vectorBucketName=VECTOR_BUCKET,
        indexName=INDEX_NAME,
        queryVector=embeddings,
        topK=5,
    )

    for match in response["Matches"]:
        print(f"Key: {match['Key']}, Score: {match['Distance']}")


if __name__ == "__main__":
    user_prompt = "Uni in New York City"

    main(user_prompt)
    pass
