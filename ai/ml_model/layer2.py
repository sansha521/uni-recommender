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
# from sentence_transformers import SentenceTransformer

import chromadb

from ..utils import load_local_data

load_dotenv()

import numpy as np
from transformers import AutoTokenizer
import onnxruntime as ort

session_google = ort.InferenceSession("ai/ml_model/models/google_embeddings.onnx")
session_wikipedia = ort.InferenceSession("ai/ml_model/models/wikipedia_embeddings.onnx")

tokenizer_google = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
tokenizer_wikipedia = AutoTokenizer.from_pretrained("sentence-transformers/multi-qa-mpnet-base-dot-v1")

def _encode(session, tokenizer, text: str) -> list:
    inputs = tokenizer(text, return_tensors="np", truncation=True, padding=True)
    outputs = session.run(None, dict(inputs))
    embedding = outputs[0].mean(axis=1).squeeze()
    return embedding.astype("float32").tolist()


REGION = "us-east-1"
VECTOR_BUCKET = "uni-rec-s3-vector-bucket"
INDEX_NAME_REVIEWS = "uni-rec-index"
INDEX_NAME_WIKIPEDIA = "uni-rec-wikipedia"

NPY_FILE = "./data_source/embeddings.npy"
ADD_METADATA = True
BATCH_SIZE = 500

COLLECTION_NAME = "universities"
EMBED_MODEL = "multi-qa-mpnet-base-dot-v1"
TEXT_TRUNCATE = 3000

CHROMA_PATH = "./data_source/wikipedia/"
COLLECTION_NAME = "universities"

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection(COLLECTION_NAME)

# model_google = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
# model_wikipedia = SentenceTransformer(EMBED_MODEL)

s3vectors = boto3.client("s3vectors", region_name=REGION)


def query_s3_vector(user_prompt: str) -> list[int]:
    # Embed the prompt
    embeddings = _encode(session_google, tokenizer_google, user_prompt)

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
    embeddings = _encode(session_wikipedia, tokenizer_wikipedia, user_prompt)

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
    df_reviews = load_local_data("./data_source/university_reviews_slice_2.csv")

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
