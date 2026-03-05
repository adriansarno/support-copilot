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


# How to test

## API
From root:  
cd api  
uv sync  
cd ..  
PYTHONPATH=$PWD uv run --directory api pytest tests/ -v  
  
  
## Inference 

PYTHONPATH=$PWD uv run --directory inference python -c "
from inference.generation.prompt_manager import PromptManager
pm = PromptManager(prompts_dir='$PWD/prompts', version='v1')
rendered = pm.render('answer', chunks=[{'source_type': 'pdf', 'title': 'Test', 'content': 'Hello world'}], history=[], question='How does it work?')
print(rendered[:300])
print('---')
print('Metadata:', pm.get_metadata('answer'))"  
  
 

PYTHONPATH=$PWD uv run --directory inference python -c "
from inference.generation.citations import CitationExtractor
from inference.retrieval.bm25 import RetrievedChunk
chunks = [
    RetrievedChunk(chunk_id='a1', doc_id='d1', title='Return Policy', content='30 day returns...', source_type='pdf'),
    RetrievedChunk(chunk_id='a2', doc_id='d2', title='Shipping FAQ', content='Free shipping...', source_type='html'),
]
text, citations = CitationExtractor().extract('Per [Source 1], returns are 30 days. See also [Source 2].', chunks)
print('Citations found:', len(citations))
for c in citations:
    print(f'  [{c.source_index}] {c.title} ({c.source_type}) -> {c.chunk_id}')
"  
  

PYTHONPATH=$PWD uv run --directory inference python -c "
from inference.retrieval.hybrid import reciprocal_rank_fusion
from inference.retrieval.bm25 import RetrievedChunk
bm25 = [RetrievedChunk(chunk_id=f'c{i}', doc_id='d', title=f'Doc {i}', content='...', source_type='pdf', score=1.0/(i+1)) for i in range(5)]
vec  = [RetrievedChunk(chunk_id=f'c{4-i}', doc_id='d', title=f'Doc {4-i}', content='...', source_type='pdf', score=1.0/(i+1)) for i in range(5)]
fused = reciprocal_rank_fusion(bm25, vec, k=60)
print(f'Merged {len(fused)} unique chunks from 2 lists:')
for c in fused:
    print(f'  {c.chunk_id}: RRF score={c.score:.6f}')
"  
  
## UI
  
cd ui && npm install && npm run dev  
   
Then open http://localhost:3000 in your browser. You should see:  
Landing page with the "Support Copilot" heading, 4 feature cards, and a "Start Chatting" button  
Click "Start Chatting" to go to /chat -- you'll see the three-panel layout (sidebar, chat window, source trace panel)  
The dark/light theme toggle in the header should work  
API calls will fail (no backend running) but the UI structure, navigation, and styling should all render correctly  
  
## Docker build smoke test (no GCP needed)
   
docker build -t TAG_NAME SOURCE_FOLDER  
-t: tag  
SOURCE_FOLDER: path to the folder containing the "Dockerfile" file  

open -a docker  
   
docker build -t sc-api ./api
docker build -t sc-inference ./inference
docker build -t sc-ui ./ui
docker build -t sc-acquisition ./acquisition
docker build -t sc-training ./training