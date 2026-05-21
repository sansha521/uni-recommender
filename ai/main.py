from fastapi import FastAPI
from pydantic import BaseModel


class UserPromptModel(BaseModel):
    user_prompt: str


app = FastAPI()


@app.post("/prompt/")
async def create_item(user_prompt: UserPromptModel):
    return user_prompt