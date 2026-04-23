#!/usr/bin/env python3
"""
Converts raw Reddit JSON data into clean structured university profile .txt files
using Claude to summarize and organize the content.
"""

import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

REDDIT_DIR = Path(__file__).parent / "output" / "reddit"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "universities"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

SYSTEM_PROMPT = """You are building a university profile database for a recommendation system.
Your job is to read raw Reddit posts and comments about a university and produce a clean,
structured text profile covering qualitative/lifestyle aspects of the university.

Be factual and balanced. Quote or paraphrase actual student opinions where useful.
If information on a section is sparse, say so briefly rather than fabricating details.
Write in plain prose — no bullet points, no markdown. Each section should be 3-6 sentences."""

PROFILE_TEMPLATE = """Based on the Reddit posts and comments below about {name}, write a structured university profile.

Cover these sections exactly, with the section header in ALL CAPS followed by a colon:

OVERVIEW: General character of the university — size, location type (urban/suburban/college town), overall vibe.
ACADEMIC CULTURE: How students describe the academic intensity, collaboration vs competition, workload.
SOCIAL LIFE: Parties, events, things to do on campus and nearby. Greek life presence.
CAMPUS CULTURE: School spirit, student identity, what students are passionate about, diversity of interests.
CITY AND SURROUNDINGS: The city or town the campus is in, what's nearby, how students feel about the location.
SAFETY: Student perceptions of campus and neighborhood safety.
FEMALE FRIENDLY: Experiences of women on campus — safety, culture, inclusion.
HOUSING AND FOOD: Dorms, off-campus options, campus food quality.
STUDENT REVIEWS: 3-5 direct quotes or paraphrases from students that capture the vibe authentically.

---
RAW REDDIT DATA FOR {name}:

{reddit_content}
"""


def build_reddit_content(data: dict, max_chars: int = 15000) -> str:
    """Flatten Reddit posts and comments into a single text block."""
    lines = []

    for post in data.get("posts", []):
        title = post.get("title", "").strip()
        body = post.get("selftext", "").strip()
        score = post.get("score", 0)

        if not title:
            continue

        lines.append(f"POST (score:{score}): {title}")
        if body and len(body) > 50:
            lines.append(f"  {body[:500]}")

        for comment in post.get("comments", []):
            comment_body = comment.get("body", "").strip()
            comment_score = comment.get("score", 0)
            if comment_body and comment_score > 1:
                lines.append(f"  COMMENT (score:{comment_score}): {comment_body[:300]}")

        lines.append("")

    for post in data.get("search_results", []):
        title = post.get("title", "").strip()
        body = post.get("selftext", "").strip()
        if title:
            lines.append(f"SEARCH RESULT: {title}")
            if body and len(body) > 50:
                lines.append(f"  {body[:400]}")
            lines.append("")

    content = "\n".join(lines)
    # Truncate to stay within context limits
    return content[:max_chars]


def generate_profile(data: dict) -> str:
    name = data["name"]
    reddit_content = build_reddit_content(data)

    print(f"  Sending {len(reddit_content)} chars to model...")

    prompt = PROFILE_TEMPLATE.format(
        name=name,
        reddit_content=reddit_content,
    )

    response = client.chat.completions.create(
        model="google/gemini-flash-1.5",
        max_tokens=2000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    return response.choices[0].message.content


def main():
    json_files = sorted(REDDIT_DIR.glob("*.json"))
    # Skip the combined file
    json_files = [f for f in json_files if f.name != "all.json"]

    print(f"Generating profiles for {len(json_files)} universities...\n")

    for json_file in json_files:
        data = json.loads(json_file.read_text())
        name = data["name"]
        slug = data["slug"]

        print(f"Processing: {name}")
        profile = generate_profile(data)

        out_path = OUTPUT_DIR / f"{slug}.txt"
        header = f"=== {name} ===\n\n"
        out_path.write_text(header + profile + "\n")
        print(f"  Saved to data/universities/{slug}.txt\n")

    print("Done.")


if __name__ == "__main__":
    main()
