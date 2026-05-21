import numpy as np
import boto3
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

REGION = "us-east-1"
VECTOR_BUCKET = "uni-rec-s3-vector-bucket"
INDEX_NAME = "uni-rec-index"
NPY_FILE = "rag/reviews/embeddings.npy"
ADD_METADATA = True
BATCH_SIZE = 500


model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
s3vectors = boto3.client("s3vectors", region_name=REGION)


def main(user_prompt: str) -> None:
    # Embed the prompt
    pass
    embeddings = model.encode(user_prompt)

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
