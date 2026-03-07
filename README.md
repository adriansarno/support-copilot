# Customer Support RAG Copilot

AI-powered customer support assistant with RAG retrieval, hybrid search, citations, answer grading, and a modern React UI.

## Architecture

```
Data Sources (PDF, HTML, Confluence, Tickets)
        │
        ▼
┌─────────────────┐     ┌──────────────────┐
│   Acquisition    │────▶│  BigQuery + GCS   │
│   Pipeline       │     │  Vertex Vector    │
│                  │     │  Search Index     │
└─────────────────┘     └────────┬─────────┘
                                 │
┌─────────────────┐              │
│    Training      │              │
│  (LoRA + Reranker)│◀────────────┘
│  → W&B Tracking  │
└─────────────────┘
                                 │
                        ┌────────▼─────────┐
                        │   Inference       │
                        │  BM25 + Vector    │
                        │  → RRF → Rerank  │
                        │  → LLM → Cite    │
                        │  → Grade         │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │   FastAPI API     │
                        │  /chat            │
                        │  /suggest-reply   │
                        │  /feedback        │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │   Next.js UI      │
                        │  Agent Chat       │
                        │  Source Trace     │
                        │  Doc Viewer      │
                        │  Feedback        │
                        └──────────────────┘
```

## Modules

| Module | Description | Port |
|--------|-------------|------|
| `acquisition/` | Ingest PDFs, HTML, Confluence, tickets → chunk → embed → store | CLI |
| `training/` | Fine-tune answer-style model (LoRA) + cross-encoder reranker | CLI |
| `inference/` | Hybrid retrieval (BM25 + vector) → rerank → generate → grade | 8001 |
| `api/` | FastAPI service: chat, suggest-reply, feedback endpoints | 8000 |
| `ui/` | Next.js 14 React app: chat, document viewer, source trace | 3000 |

## Quick Start

### 1. Configure

```bash
cp .env.example .env
# Edit .env with your GCP project, API keys, etc.
```

### 2. Local Development

```bash
# Start API + inference + UI
make up

# View logs
make logs

# Stop
make down
```

### 3. Run Acquisition Pipeline

```bash
# Place documents in ./data/ (PDFs, HTML, JSONL tickets)
make acquire
```

### 4. Run Training Pipeline

```bash
make train
```

## Stack

- **Compute**: Cloud Run, GKE, Docker
- **Storage**: BigQuery (chunks + BM25), Vertex Vector Search, GCS
- **LLM**: OpenAI / Gemini / DeepSeek (swappable via `LLM_PROVIDER` env)
- **Embeddings**: Vertex AI text-embedding-004 / OpenAI (swappable)
- **Training**: HuggingFace PEFT (LoRA), sentence-transformers (cross-encoder)
- **Tracking**: Weights & Biases (datasets, runs, eval tables, model registry)
- **CI/CD**: GitHub Actions → Artifact Registry → Cloud Run
- **IaC**: Pulumi (BigQuery, GCS, Pub/Sub, Secret Manager, Cloud Run)
- **Frontend**: Next.js 14, Tailwind CSS, TypeScript

## CI/CD

Commit-message triggers (following cheese-app-v4 pattern):

| Trigger | Workflow | Action |
|---------|----------|--------|
| `/run-acquisition` | `acquisition-ci.yml` | Build + run acquisition pipeline |
| `/run-training` | `training-ci.yml` | Build + run training pipeline |
| `/deploy-app` | `app-ci-cd.yml` | Build + deploy API, inference, UI to Cloud Run |
| Push to `infra/` | `deploy-infra.yml` | Pulumi preview (+ deploy with `/deploy-infra`) |

## API Endpoints

All endpoints require `X-API-Key` header.

### Chat

- `POST /chat/` — Send a message (creates or continues a chat)
- `GET /chat/` — List all chats
- `GET /chat/{chat_id}` — Get chat history

### Suggest Reply

- `POST /suggest-reply/` — Generate a customer-facing reply from ticket context

### Feedback

- `POST /feedback/` — Submit thumbs up/down + optional comment

## Prompt Versioning

Templates in `prompts/v{N}/` using Jinja2 + YAML. Each API response includes prompt metadata (name, version, hash) for A/B tracking.

## Project Structure

```
support-copilot/
├── .github/workflows/     CI/CD pipelines
├── acquisition/           Ingest → chunk → embed → store
├── training/              Fine-tune + reranker training
├── inference/             RAG pipeline (retrieve → rerank → generate → grade)
├── api/                   FastAPI service
├── ui/                    Next.js React frontend
├── shared/                Shared config + LLM/embedding providers
├── prompts/               Versioned prompt templates
├── infra/                 Pulumi IaC
├── docker-compose.yml     Local orchestration
└── Makefile               Common commands
```

Pulumi.dev.yaml:  
config:  
  gcp:project: your-gcp-project  
  gcp:region: us-central1  
  support-copilot-infra:environment: dev  
# Run: pulumi config set --secret api_key <your-key>  