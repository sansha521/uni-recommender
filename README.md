# CampusMatch

**Find the right university for you — not just based on the ranking, but also based on the foods, people, and vibes.**

Find the right university based on your budget, grades, degree, specialization, weather, big city vs. small city — you name it.

**🌐 Live at [www.campus-match.org](https://www.campus-match.org/)**

---

## Overview

CampusMatch is a university recommendation system. You describe yourself with a short
profile — budget, SAT/ACT score, and preferred region — plus a free-text description of the
qualities and "vibes" you're looking for. CampusMatch returns five ranked universities,
each with a short explanation of *why* it fits, and lets you keep the conversation going to
refine the results.

Instead of relying on rankings alone, recommendations are grounded in real signal about each
school — cost and admissions data, Wikipedia articles, and student reviews — retrieved
semantically and ranked by an LLM.

The typical flow:

1. **Profile + prompt** — the user fills out the form (budget, score, region, free-text qualities).
2. **Recommendations** — the AI service returns five ranked schools with reasoning.
3. **Chat** — the user asks follow-up questions to refine or re-rank the recommendations.

## Features

- **Profile-based filtering** — hard filters on budget, SAT/ACT score, and US region.
- **Semantic "vibes" matching** — retrieves relevant schools from Wikipedia articles and
  student reviews using vector search over text embeddings.
- **LLM-ranked recommendations** — a language model ranks the candidates and explains the fit.
- **Conversational refinement** — a chat endpoint that adjusts or re-ranks recommendations
  based on follow-up messages.

## Tech Stack & Tools

| Area | Technologies |
| --- | --- |
| **Frontend** | Astro (static SSG), `free-astro-components`, plain scoped CSS, Node ≥ 22 |
| **AI service** | Python 3.13, FastAPI, Uvicorn, Pydantic, pandas, ONNX Runtime, tokenizers, ChromaDB, boto3 |
| **API server** | Go 1.26, go-chi (scaffold / in progress) |
| **Embeddings** | SentenceTransformers (`all-MiniLM-L6-v2`, `multi-qa-mpnet-base-dot-v1`) exported to int8-quantized ONNX |
| **LLMs** | Amazon Bedrock Nova Micro (`amazon.nova-micro-v1:0`, production); Anthropic Claude & Gemini Flash via OpenRouter (offline pipeline) |
| **Data / vectors** | AWS S3 Vectors, ChromaDB, CSV datasets |
| **Infrastructure** | AWS ECR, Lambda (container image + Lambda Web Adapter), S3, CloudFront, ALB, CloudWatch, Bedrock |
| **CI/CD** | GitHub Actions |
| **External data sources** | Wikipedia (MediaWiki API), Reddit JSON API, Niche.com (Playwright), Google Places / Maps |

## Architecture

The frontend is a static Astro site served from S3 behind CloudFront. It calls the FastAPI
AI service (deployed as a container image on AWS Lambda) at two endpoints:

- `POST /prompt/` — main recommendation flow (runs the 3-layer pipeline).
- `POST /chat/` — conversational refinement over existing recommendations (calls Bedrock directly).
- `GET /health` — health check.

The recommendation pipeline (`ai/ml_model/`) has three layers:

- **Layer 1 — filtering** (`layer1.py`): pandas hard-filtering over
  `ai/data_source/us_uni_data_filtered.csv` by cost, SAT/ACT score, and region.
- **Layer 2 — retrieval** (`layer2.py`): embeds the user prompt locally with ONNX, then
  retrieves semantically similar schools from **AWS S3 Vectors** (`uni-rec-index` for
  reviews, `uni-rec-wikipedia` for Wikipedia), using a local **ChromaDB** store for
  Wikipedia metadata. Results are intersected with Layer 1 and padded to five candidates.
- **Layer 3 — ranking** (`layer3.py`): ranks the candidates and generates reasoning via
  **Amazon Bedrock Nova Micro**.

An offline data pipeline (`data_processing/`) produces the datasets and vector indexes the
AI service consumes — it is not part of the live request path.

```
                    ┌─────────────────────────────┐
   Browser  ───────▶│  Astro frontend (S3 + CDN)  │
                    └──────────────┬──────────────┘
                       POST /prompt/ , /chat/
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │  FastAPI AI service (Lambda) │
                    │                              │
                    │  Layer 1 → pandas filter     │
                    │  Layer 2 → S3 Vectors +      │
                    │            ChromaDB (ONNX)   │
                    │  Layer 3 → Bedrock Nova Micro│
                    └─────────────────────────────┘
                                   ▲
                                   │ builds datasets + vector indexes
                    ┌─────────────────────────────┐
                    │  Offline data pipeline       │
                    │  (scrapers, RAG ingest,      │
                    │   embeddings → S3 Vectors)   │
                    └─────────────────────────────┘
```

## Project Structure

```
uni-recommender/
├── ai/                          FastAPI recommendation service
│   ├── main.py                  FastAPI app: /prompt/, /chat/, /health
│   ├── ml_model/
│   │   ├── layer1.py            Hard filtering (budget, score, region) via pandas
│   │   ├── layer2.py            Semantic retrieval (ONNX + S3 Vectors + ChromaDB)
│   │   └── layer3.py            LLM ranking + reasoning (Bedrock Nova Micro)
│   ├── export_model.py          Export/quantize SentenceTransformers → ONNX
│   ├── utils.py                 Shared helpers
│   ├── data_source/             CSVs, embeddings.npy, local ChromaDB store
│   ├── pyproject.toml           Entry point config (main:app)
│   ├── requirements.txt         AI service dependencies
│   └── Dockerfile               Multi-stage build (+ AWS Lambda Web Adapter)
│
├── fe/frontend/                 Astro frontend (the live UI)
│   ├── src/
│   │   ├── pages/               index / query / results / behind (.astro, file routing)
│   │   ├── components/          Header, Navigation, Welcome
│   │   ├── layouts/Layout.astro Base HTML shell
│   │   └── styles/global.css    Shared styles
│   ├── public/                  Static assets (icon, favicons)
│   ├── astro.config.mjs         Astro config + typed API_URL env
│   └── package.json             Scripts & dependencies
│
├── server/                      Go / go-chi API service (scaffold, in progress)
│   ├── cmd/
│   │   ├── main.go              Server bootstrap + graceful shutdown
│   │   └── api.go               Router, middleware, /api/v1 mounts
│   ├── internal/
│   │   ├── university/          router.go, handler.go, service.go
│   │   └── jsonresponse/        JSON response helper
│   ├── Makefile                 run / build / start targets
│   ├── Dockerfile               Multi-stage Go build
│   └── go.mod
│
├── data_processing/             Offline pipeline (builds datasets + vector indexes)
│   ├── scraping/                wikipedia_scraper.py, wikipedia_pipeline[_parallel].py,
│   │                            reddit_scraper.py, niche_scraper.py, generate_profiles.py,
│   │                            universities.txt, output/ (raw scrape dumps)
│   ├── rag/                     ingest.py (embed → ChromaDB), recommend.py (HyDE + Claude CLI)
│   ├── scripts/                 s3_vector.py, s3_vector_wikipedia.py,
│   │                            vector_embeddings/reviews_embeddings.py, *.ipynb notebooks
│   └── tests/                   test_embeddings.py, test_wikipedia_embeddings.py
│
├── datasets/                    University CSVs, student reviews, Wikipedia JSONL
│   ├── baseline_df*.csv         Global university records + name lists
│   ├── us_uni_*.csv             US cost / admissions metrics
│   ├── university_reviews*.csv  Student reviews
│   └── wikipedia_us_universities.jsonl
│
├── .github/
│   ├── workflows/               ai-service-deployment, fe-deployment, datasync,
│   │                            wikipedia_sync, infra-setup
│   └── ecs/                     ECS task definitions (legacy deploy path)
│
├── requirements.txt             Root deps for the data pipeline
├── baseline_df_names.ipynb      One-off name-cleaning notebook
└── client/                      Placeholder (empty)
```

## Getting Started

Run each component from its own directory.

### AI service (`ai/`)

```bash
cd ai
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Requires AWS credentials (for Bedrock and S3 Vectors) and `ALLOWED_ORIGINS` in the
environment. Serves on `http://localhost:8000`.

### Frontend (`fe/frontend/`)

```bash
cd fe/frontend
npm install
npm run dev
```

Serves on `http://localhost:4321`. Set `API_URL` to point at the AI service
(defaults to `http://localhost:8000`).

### API server (`server/`)

```bash
cd server
make run
```

Serves on `http://localhost:8080`.

### Data pipeline (`data_processing/`)

```bash
pip install -r requirements.txt   # from the repo root
# then run the scripts under data_processing/
```

## Environment Variables

Only key names are listed — never commit secret values.

| Location | Keys |
| --- | --- |
| Root `.env` | `GOOGLE_PLACES_API_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| `ai/` | `ALLOWED_ORIGINS`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| `fe/frontend/` | `API_URL` |
| Offline pipeline | `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY` |

## Deployment

Pushes to `main` trigger GitHub Actions workflows, scoped by the paths they touch:

| Path | Action |
| --- | --- |
| `ai/**` | Build image → push to ECR → deploy to AWS Lambda |
| `fe/frontend/**` | Build Astro → sync to S3 → invalidate CloudFront |
| `datasets/**` | Sync datasets to S3 |
| `data_processing/rag/**` | Rebuild S3 Vectors indexes |
