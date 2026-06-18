import os

from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .ml_model import layer1, layer2, layer3

load_dotenv()


class UserPromptModel(BaseModel):
    user_prompt: str
    budget_min: float = 0
    budget_max: float = 100_000_000
    score_type: str | None = None
    score: int | None = None
    region: str | None = None


app = FastAPI()

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:4321")
allowed_origins = [o.strip() for o in _raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
async def health_check():
    return {"stauts": "running!"}


@app.post("/prompt/")
async def query_embeddings(user_prompt: UserPromptModel):

    layer1_data = layer1.layer1(
        budget_range=(user_prompt.budget_min, user_prompt.budget_max),
        score_type=user_prompt.score_type,
        score=user_prompt.score,
        region=user_prompt.region,
    )

    layer2_data = layer2.layer2(
        layer1_data=layer1_data,
        user_prompt=user_prompt.user_prompt,
        concentration=None,
        degree=None,
    )

    recommendations = layer3.layer3(
        layer2_data=layer2_data,
        user_prompt=user_prompt.user_prompt,
    )

    return {"recommendations": recommendations}
