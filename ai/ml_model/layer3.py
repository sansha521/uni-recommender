"""
Takes layer2 filtered universities and user prompt.
Calls Amazon Nova Micro via Bedrock Converse API to produce 5 ranked recommendations.
Output: list of {name, reasoning} dicts
"""

import json
import boto3
import pandas as pd

MODEL_ID = "amazon.nova-micro-v1:0"
REGION = "us-east-1"

client = boto3.client("bedrock-runtime", region_name=REGION)

SYSTEM_PROMPT = """You are a university admissions advisor. You will be given a list of universities with their data and a student's request. Your job is to recommend the 5 best universities from the list and explain briefly why each one is a good fit for the student.

Respond with valid JSON only — no markdown, no extra text. Use this exact format:
{
  "recommendations": [
    {
      "name": "University Name",
      "reasoning": "One or two sentence explanation of why this university fits the student."
    }
  ]
}"""


def _format_universities(df: pd.DataFrame) -> str:
    lines = []
    for _, row in df.iterrows():
        name = row.get("school.name", "Unknown")
        cost = row.get("latest.cost.attendance.academic_year", "N/A")
        in_state = row.get("latest.cost.tuition.in_state", "N/A")
        out_state = row.get("latest.cost.tuition.out_of_state", "N/A")
        sat = row.get("latest.admissions.sat_scores.average.overall", "N/A")
        act = row.get("latest.admissions.act_scores.midpoint.cumulative", "N/A")
        degree = row.get("school.degrees_awarded.predominant", "N/A")
        lines.append(
            f"- {name} | Cost of attendance: ${cost} | In-state tuition: ${in_state} | "
            f"Out-of-state tuition: ${out_state} | Avg SAT: {sat} | Midpoint ACT: {act} | "
            f"Degree focus: {degree}"
        )
    return "\n".join(lines)


def layer3(layer2_data: pd.DataFrame, user_prompt: str) -> list[dict]:
    uni_context = _format_universities(layer2_data)

    user_message = f"""Student request: {user_prompt}

Universities to consider:
{uni_context}

Pick the 5 best matches and explain your reasoning for each."""

    response = client.converse(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": user_message}]}],
        inferenceConfig={"maxTokens": 1024},
    )

    response_text = response["output"]["message"]["content"][0]["text"]
    result = json.loads(response_text)
    return result["recommendations"]
