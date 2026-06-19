import json
import os

from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .ml_model import layer1, layer2, layer3
from .ml_model.layer3 import MODEL_ID, client

load_dotenv()


class UserPromptModel(BaseModel):
    user_prompt: str
    budget_min: float = 0
    budget_max: float = 100_000_000
    score_type: str | None = None
    score: int | None = None
    region: str | None = None


class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    original_context: dict
    current_recommendations: list[dict]
    conversation_history: list[ChatMessage]
    new_message: str


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


@app.post("/chat/")
async def chat(request: ChatRequest):
    recs_text = "\n".join(
        f"{i + 1}. {r['name']}: {r['reasoning']}"
        for i, r in enumerate(request.current_recommendations)
    )

    ctx = request.original_context
    score_info = (
        f"{ctx.get('score_type')} {ctx.get('score')}"
        if ctx.get("score_type") and ctx.get("score")
        else "not specified"
    )
    profile_text = (
        f"Budget: ${ctx.get('budget_min', 0):,} – ${ctx.get('budget_max', 100_000_000):,}\n"
        f"Test scores: {score_info}\n"
        f"Region preference: {ctx.get('region') or 'no preference'}\n"
        f"Interests / qualities: {ctx.get('user_prompt', '')}"
    )

    system_prompt = f"""You are a university admissions advisor helping a student refine their options.

The student's current 5 recommendations are:
{recs_text}

Student's profile:
{profile_text}

Based on the student's new message, respond in exactly one of two JSON formats:

If the student is asking a question or wants more information, answer conversationally:
{{"type": "message", "content": "your response"}}

If the student wants to re-prioritize or re-rank these same universities based on a new preference, return a fresh ranking of all 5:
{{"type": "recommendations", "recommendations": [{{"name": "...", "reasoning": "..."}}]}}

Respond with valid JSON only — no markdown, no extra text."""

    messages = [
        {"role": msg.role, "content": [{"text": msg.content}]}
        for msg in request.conversation_history
    ]
    messages.append({"role": "user", "content": [{"text": request.new_message}]})

    response = client.converse(
        modelId=MODEL_ID,
        system=[{"text": system_prompt}],
        messages=messages,
        inferenceConfig={"maxTokens": 1024},
    )

    response_text = response["output"]["message"]["content"][0]["text"]
    return json.loads(response_text)
