from dotenv import load_dotenv

from fastapi import FastAPI
from pydantic import BaseModel

from .ml_model import layer1, layer2

load_dotenv()


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
