"""
filter down results from layer1 using semantic data
Args: layer1 output of 20 universities
filter based on: concentration, degree, user input
vector search function
Output: 5 best universities
"""

import json

import boto3
import pandas as pd
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import chromadb

load_dotenv()

REGION = "us-east-1"
VECTOR_BUCKET = "uni-rec-s3-vector-bucket"
INDEX_NAME_REVIEWS = "uni-rec-index"
INDEX_NAME_WIKIPEDIA = "uni-rec-wikipedia"

NPY_FILE = "../../data_processing/rag/reviews/embeddings.npy"
ADD_METADATA = True
BATCH_SIZE = 500

COLLECTION_NAME = "universities"
EMBED_MODEL = "multi-qa-mpnet-base-dot-v1"
TEXT_TRUNCATE = 3000

CHROMA_PATH = "../../data_processing/rag/wikipedia"
COLLECTION_NAME = "universities"

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection(COLLECTION_NAME)

model_google = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
model_wikipedia = SentenceTransformer(EMBED_MODEL)

s3vectors = boto3.client("s3vectors", region_name=REGION)


def query_s3_vector(user_prompt: str) -> int:
    # Embed the prompt
    embeddings = model_google.encode(user_prompt).astype("float32").tolist()

    # Call the Vector Bucket
    response = s3vectors.query_vectors(
        vectorBucketName=VECTOR_BUCKET,
        indexName=INDEX_NAME_REVIEWS,
        queryVector={"float32": embeddings},
        topK=5,
        returnDistance=True,
        returnMetadata=True,
    )

    row_id = int(response["vectors"][0]["metadata"]["row_id"])
    return row_id

def query_s3_wikipedia(user_prompt: str) -> int:
    # Embed the prompt
    embeddings = model_wikipedia.encode(user_prompt).astype("float32").tolist()

    # Call the Vector Bucket
    response = s3vectors.query_vectors(
        vectorBucketName=VECTOR_BUCKET,
        indexName=INDEX_NAME_WIKIPEDIA,
        queryVector={"float32": embeddings},
        topK=5,
        returnDistance=True,
        returnMetadata=True,
    )

    # print(json.dumps(response["vectors"], indent=2))
    row_id = response["vectors"][0]["key"]
    return row_id


