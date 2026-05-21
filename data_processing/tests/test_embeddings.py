import json

import boto3
import pandas as pd
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


def main(user_prompt: str) -> int:
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

    print(response)
    print(json.dumps(response["vectors"], indent=2))

    row_id = int(response["vectors"][0]["metadata"]["row_id"])
    return row_id


if __name__ == "__main__":
    user_prompt = "Which University in New York City"

    row_id = main(user_prompt)

    # Get the review data
    df = pd.read_csv("./datasets/university_reviews_slice_2.csv")

    row = df.iloc[row_id]
    print(row)
