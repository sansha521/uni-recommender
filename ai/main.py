import json
from dotenv import load_dotenv

from fastapi import FastAPI
from pydantic import BaseModel

from .ml_model import layer1, layer2

load_dotenv()

# REGION = "us-east-1"
# VECTOR_BUCKET = "uni-rec-s3-vector-bucket"
# INDEX_NAME_REVIEWS = "uni-rec-index"
# INDEX_NAME_WIKIPEDIA = "uni-rec-wikipedia"
#
# NPY_FILE = "../data_processing/rag/reviews/embeddings.npy"
# ADD_METADATA = True
# BATCH_SIZE = 500
#
# COLLECTION_NAME = "universities"
# EMBED_MODEL = "multi-qa-mpnet-base-dot-v1"
# TEXT_TRUNCATE = 3000
#
# CHROMA_PATH = "../data_processing/rag/wikipedia"
# COLLECTION_NAME = "universities"
#
# client = chromadb.PersistentClient(path=CHROMA_PATH)
# collection = client.get_collection(COLLECTION_NAME)
#
# model_google = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
# model_wikipedia = SentenceTransformer(EMBED_MODEL)
#
# s3vectors = boto3.client("s3vectors", region_name=REGION)
#


class UserPromptModel(BaseModel):
    user_prompt: str


app = FastAPI()


@app.post("/prompt/")
async def query_embeddings(user_prompt: UserPromptModel):

    layer1_data = layer1.layer1(
        budget_range=(0, 100_000_000),
    )

    layer2_data = layer2.layer2(
        layer1_data=layer1_data,
        user_prompt=user_prompt.user_prompt,
        concentration=None,
        degree=None,
    )

    response = layer2_data.to_json(orient="records")
    return response
