import os
import sys
from pathlib import Path

import anthropic
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "universities"
EMBED_MODEL = "multi-qa-mpnet-base-dot-v1"
TOP_K = 8
MODEL = "claude-sonnet-4-6"


def generate_hypothetical_document(user_query: str, client: anthropic.Anthropic) -> str:
    """HyDE: generate a fake Wikipedia excerpt describing the ideal university,
    then embed that instead of the raw user query for better semantic match."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": (
                    "Write a 3-4 sentence excerpt in the style of a Wikipedia article "
                    "describing a US university that perfectly matches these student preferences:\n\n"
                    f"{user_query}\n\n"
                    "Write only the excerpt — no intro, no commentary. "
                    "Include concrete details: location, size, setting, programs, campus environment."
                ),
            }
        ],
    )
    return response.content[0].text


def retrieve(query: str, model: SentenceTransformer, collection, client: anthropic.Anthropic) -> list[dict]:
    print("Generating hypothetical document (HyDE)...")
    hypothetical_doc = generate_hypothetical_document(query, client)
    print(f"  → {hypothetical_doc[:120]}...\n")

    query_embedding = model.encode(hypothetical_doc).tolist()
    results = collection.query(query_embeddings=[query_embedding], n_results=TOP_K)
    universities = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        universities.append({"name": meta["name"], "text": doc, "score": 1 - distance})
    return universities


def recommend(user_query: str, universities: list[dict], client: anthropic.Anthropic) -> str:
    context_parts = []
    for u in universities:
        snippet = u["text"][:1500].strip()
        context_parts.append(f"**{u['name']}**\n{snippet}")
    context = "\n\n---\n\n".join(context_parts)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": (
                    "You are an expert university admissions advisor. "
                    "Your job is to recommend universities that best match a student's preferences. "
                    "Be specific, honest, and concise. Only recommend universities from the provided list."
                ),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"""A student described their ideal university as follows:

"{user_query}"

Here are the most semantically relevant universities retrieved from the database:

{context}

Based on the student's preferences, recommend the top 3-5 universities from this list. For each pick, give a brief (2-3 sentence) explanation of why it fits. Rank them from best to worst match.""",
            }
        ],
    )
    return response.content[0].text


def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Describe what you're looking for in a university:\n> ").strip()

    if not query:
        print("No query provided.")
        sys.exit(1)

    print("\nLoading models...")
    embed_model = SentenceTransformer(EMBED_MODEL)
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = chroma_client.get_collection(COLLECTION_NAME)

    ai_client = anthropic.Anthropic()

    print(f"Searching across {collection.count()} universities...\n")
    universities = retrieve(query, embed_model, collection, ai_client)

    print(f"Top {len(universities)} matches retrieved. Asking Claude for recommendations...\n")
    print("=" * 60)
    result = recommend(query, universities, ai_client)
    print(result)
    print("=" * 60)


if __name__ == "__main__":
    main()
