"""
filter down results from layer1 using semantic data
Args: layer1 output of 20 universities
filter based on: concentration, degree, user input
vector search function
Output: 5 best universities
"""

import boto3
import pandas as pd
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import chromadb

from ..utils import load_local_data

load_dotenv()

REGION = "us-east-1"
VECTOR_BUCKET = "uni-rec-s3-vector-bucket"
INDEX_NAME_REVIEWS = "uni-rec-index"
INDEX_NAME_WIKIPEDIA = "uni-rec-wikipedia"

NPY_FILE = "../data_processing/rag/reviews/embeddings.npy"
ADD_METADATA = True
BATCH_SIZE = 500

COLLECTION_NAME = "universities"
EMBED_MODEL = "multi-qa-mpnet-base-dot-v1"
TEXT_TRUNCATE = 3000

CHROMA_PATH = "../data_processing/rag/wikipedia"
COLLECTION_NAME = "universities"

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection(COLLECTION_NAME)

model_google = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
model_wikipedia = SentenceTransformer(EMBED_MODEL)

s3vectors = boto3.client("s3vectors", region_name=REGION)


def query_s3_vector(user_prompt: str) -> list[int]:
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

    row_ids = [int(vec["metadata"]["row_id"]) for vec in response["vectors"]]

    return row_ids


def query_s3_wikipedia(user_prompt: str) -> list[str]:
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
    row_ids = [(vec["key"]) for vec in response["vectors"]]
    return row_ids


def layer2(
    layer1_data: pd.DataFrame,
    user_prompt: str,
    concentration: str | None = None,
    degree: str | None = None,
) -> pd.DataFrame:
    reviews_row_ids = query_s3_vector(user_prompt)

    wikipedia_row_ids = query_s3_wikipedia(user_prompt)

    # Review DataFrame
    df_reviews = load_local_data("../datasets/university_reviews_slice_2.csv")

    df_reviews_filtered = df_reviews.iloc[reviews_row_ids]
    df_reviews_name = set(df_reviews_filtered["name"].tolist())

    wikipedia_filered = collection.get(wikipedia_row_ids)
    wikipedia_filered_names = {
        metadata["name"] for metadata in wikipedia_filered["metadatas"]
    }

    layer2_uni_names = list(df_reviews_name | wikipedia_filered_names)

    # The Context For the LLM
    # To Further Filter Layer 1
    layer1_data_filtered = layer1_data[
        layer1_data["school.name"].isin(layer2_uni_names)
    ]

    return layer1_data_filtered
