"""
filter down results from layer1 using semantic data
Args: layer1 output of 20 universities
filter based on: concentration, degree, user input
vector search function
Output: 5 best universities
"""

from pathlib import Path
from functools import lru_cache

import boto3
import chromadb
import onnxruntime as ort
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from tokenizers import Tokenizer

from utils import load_local_data

load_dotenv()


_MODELS_DIR = Path(__file__).parent / "models"


@lru_cache(maxsize=1)
def get_google_session():
    return ort.InferenceSession(str(_MODELS_DIR / "google_embeddings.onnx"))


@lru_cache(maxsize=1)
def get_wikipedia_session():
    return ort.InferenceSession(str(_MODELS_DIR / "wikipedia_embeddings.onnx"))


@lru_cache(maxsize=1)
def get_google_tokenizer():
    t = Tokenizer.from_file(str(_MODELS_DIR / "google_tokenizer.json"))
    t.enable_truncation(max_length=256)
    return t


@lru_cache(maxsize=1)
def get_wikipedia_tokenizer():
    t = Tokenizer.from_file(str(_MODELS_DIR / "wikipedia_tokenizer.json"))
    t.enable_truncation(max_length=512)
    return t


@lru_cache(maxsize=1)
def get_chroma_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(COLLECTION_NAME)


@lru_cache(maxsize=1)
def get_s3vectors():
    return boto3.client("s3vectors", region_name=REGION)


def _encode(session, tokenizer: Tokenizer, text: str, pooling: str) -> list:
    enc = tokenizer.encode(text)
    input_ids = np.array([enc.ids], dtype=np.int64)
    attention_mask = np.array([enc.attention_mask], dtype=np.int64)
    inputs = {"input_ids": input_ids, "attention_mask": attention_mask}

    expected = {i.name for i in session.get_inputs()}
    if "token_type_ids" in expected:
        inputs["token_type_ids"] = np.array([enc.type_ids], dtype=np.int64)

    outputs = session.run(None, inputs)

    if pooling == "cls":
        embedding = outputs[0][:, 0].squeeze()
    elif pooling == "mean":
        mask = attention_mask[..., None].astype("float32")
        summed = (outputs[0] * mask).sum(axis=1)
        counts = np.clip(mask.sum(axis=1), 1e-9, None)
        embedding = (summed / counts).squeeze()
    else:
        raise ValueError(f"unknown pooling: {pooling}")

    # NO normalization — both indexes built with normalize_embeddings=False
    return embedding.astype("float32").tolist()


REGION = "us-east-1"
VECTOR_BUCKET = "uni-rec-s3-vector-bucket"
INDEX_NAME_REVIEWS = "uni-rec-index"
INDEX_NAME_WIKIPEDIA = "uni-rec-wikipedia"

_DATA_DIR = Path(__file__).parent.parent / "data_source"

NPY_FILE = str(_DATA_DIR / "embeddings.npy")
ADD_METADATA = True
BATCH_SIZE = 500

COLLECTION_NAME = "universities"
EMBED_MODEL = "multi-qa-mpnet-base-dot-v1"
TEXT_TRUNCATE = 3000

CHROMA_PATH = str(_DATA_DIR / "wikipedia")
COLLECTION_NAME = "universities"

# model_google = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
# model_wikipedia = SentenceTransformer(EMBED_MODEL)

s3vectors = boto3.client("s3vectors", region_name=REGION)


def query_s3_vector(user_prompt: str) -> list[int]:
    # Embed the prompt
    embeddings = _encode(
        get_google_session(), get_google_tokenizer(), user_prompt, "mean"
    )

    # Call the Vector Bucket
    response = get_s3vectors().query_vectors(
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
    embeddings = _encode(
        get_wikipedia_session(), get_wikipedia_tokenizer(), user_prompt, "cls"
    )

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
    df_reviews = load_local_data(str(_DATA_DIR / "university_reviews_slice_2.csv"))

    df_reviews_filtered = df_reviews.iloc[reviews_row_ids]
    df_reviews_name = set(df_reviews_filtered["name"].tolist())

    wikipedia_filered = get_chroma_collection().get(wikipedia_row_ids)
    wikipedia_filered_names = {
        metadata["name"] for metadata in wikipedia_filered["metadatas"]
    }

    layer2_uni_names = list(df_reviews_name | wikipedia_filered_names)

    # The Context For the LLM
    # To Further Filter Layer 1
    layer1_data_filtered = layer1_data[
        layer1_data["school.name"].isin(layer2_uni_names)
    ]

    # Ensure at least 5 universities reach layer3; pad with top layer1 results
    if len(layer1_data_filtered) < 5:
        extras = layer1_data[~layer1_data["school.name"].isin(layer2_uni_names)]
        layer1_data_filtered = pd.concat([layer1_data_filtered, extras]).head(5)

    return layer1_data_filtered
