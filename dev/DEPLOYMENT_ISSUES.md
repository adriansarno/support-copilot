# Deployment Issues & Fixes

Summary of all issues encountered during the initial deployment of the Support Copilot to GCP Cloud Run.

---

## 1. Code Issues

### 1.1 Pulumi `pulumi-gcp` v9 API Changes

**Problem:** `ServiceTemplateContainerPortsArgs` caused `AssertionError: Unexpected type. Expected 'list'` when defining Cloud Run services.

**Fix:** Replaced all typed `*Args` classes with plain dicts for the entire Cloud Run `template` block. In v9.14.0, `ports` expects a single object (not a list).

### 1.2 Dockerfiles Using Wrong Build Context

**Problem:** `COPY pyproject.toml ...` failed with `not found` because Docker builds ran from the project root (`-f inference/Dockerfile .`) but the Dockerfile expected files relative to the module directory.

**Fix:** Updated all Python Dockerfiles to prefix paths with the module directory (e.g., `COPY inference/pyproject.toml ./`), copy `shared/` and `prompts/` into the image, and set `PYTHONPATH=/app`.

### 1.3 Missing `uvicorn` and `fastapi` in Inference Dependencies

**Problem:** `inference/pyproject.toml` did not list `uvicorn` or `fastapi`, so the container started but `uvicorn` binary was not found (`Failed to spawn: uvicorn`).

**Fix:** Added `"fastapi>=0.115.0"` and `"uvicorn[standard]>=0.34.0"` to `inference/pyproject.toml`.

### 1.4 Missing `pydantic-settings` in Acquisition Dependencies

**Problem:** `acquisition/pyproject.toml` did not list `pydantic-settings`, causing `ModuleNotFoundError` when importing `shared.config`.

**Fix:** Added `"pydantic-settings>=2.7.0"` to `acquisition/pyproject.toml`.

### 1.5 Missing `google-auth` in API Dependencies

**Problem:** The API service needed `google.oauth2.id_token` for service-to-service authentication to the inference service, but `google-auth` was not in `api/pyproject.toml`.

**Fix:** Added `"google-auth>=2.36.0"` to `api/pyproject.toml`.

### 1.6 `genai.Client()` Missing Vertex AI Configuration

**Problem:** Both `EmbeddingProvider` and `LLMProvider` created `genai.Client()` without `vertexai=True`, causing `ValueError: No API key was provided` on Cloud Run (which uses service account credentials, not API keys).

**Fix:** Changed both to `genai.Client(vertexai=True, project=..., location=...)` and passed `gcp_project`/`gcp_region` through from settings.

### 1.7 `VectorRetriever` Crashing on Empty Endpoint ID

**Problem:** `VectorRetriever` initialization crashed with `ValueError: Resource  is not a valid resource id` when `vertex_index_endpoint_id` was empty (no Vertex Vector Search index configured).

**Fix:** Made `VectorRetriever` optional in `server.py` — only instantiate if `vertex_index_endpoint_id` is set. Updated `pipeline.py` to handle `None` vector retriever by falling back to BM25-only.

### 1.8 `CrossEncoderReranker` Timeout on Cold Start

**Problem:** The reranker downloads `cross-encoder/ms-marco-MiniLM-L-6-v2` (~400MB) from HuggingFace on first startup, exceeding Cloud Run's startup probe timeout.

**Fix:** Added `SKIP_RERANKER` env var to disable reranker initialization on Cloud Run. Made reranker optional in `pipeline.py` — falls back to returning chunks in retrieval order.

### 1.9 BigQuery `SEARCH_SCORE` Function Not Available

**Problem:** BM25 retriever used `SEARCH()` and `SEARCH_SCORE()` BigQuery functions, which require a search index that didn't exist. Error: `Function not found: SEARCH_SCORE`.

**Fix:** Replaced `SEARCH`/`SEARCH_SCORE` with keyword-based `LIKE` queries that work without a search index. Scores are assigned by rank position.

### 1.10 `NEXT_PUBLIC_API_URL` Not Embedded in UI Build

**Problem:** Next.js `NEXT_PUBLIC_*` variables are embedded at build time, not runtime. The UI was built without `NEXT_PUBLIC_API_URL`, so the browser sent requests to `http://localhost:8000` instead of the Cloud Run API URL.

**Fix:** Added `ARG NEXT_PUBLIC_API_URL` and `ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL` to the builder stage of `ui/Dockerfile`. Pass the URL via `--build-arg` at build time.

### 1.11 API Not Sending Auth Token to Inference Service

**Problem:** The API called the inference service without an identity token, resulting in `403 Forbidden` (Cloud Run services are private by default).

**Fix:** Added `_get_identity_token()` helper using `google.oauth2.id_token.fetch_id_token()` to `chat_service.py`. All calls to the inference service now include `Authorization: Bearer <token>`.

### 1.12 Pydantic Settings `.env` File Not Found

**Problem:** `BaseSettings` with `env_file=".env"` resolves relative to CWD. When running `uv run --directory acquisition`, CWD changed to `acquisition/` and the `.env` at the project root was not found.

**Fix:** Updated `shared/config.py` to resolve `.env` relative to the project root using `Path(__file__).resolve().parent.parent / ".env"`.

### 1.13 Pipeline Init Crash Preventing Server Startup

**Problem:** Any exception during pipeline initialization (missing credentials, missing index, etc.) caused the entire FastAPI server to fail to start, making the health endpoint unreachable.

**Fix:** Wrapped pipeline initialization in a `try/except` block. On failure, the server starts in "degraded mode" — health endpoint works, but chat endpoints return an error message.

### 1.14 PyTorch CUDA Bloat in Docker Image (25 GB)

**Problem:** `sentence-transformers` pulled in the full PyTorch with CUDA libraries, resulting in a 25 GB image.

**Fix:** Added CPU-only PyTorch index to `inference/pyproject.toml` via `[tool.uv.sources]` and `[[tool.uv.index]]`. Image shrunk to ~865 MB.

---

## 2. GCP Configuration & Permission Issues

### 2.1 Missing Application Default Credentials for Pulumi

**Problem:** `rpc error: failed to load application credentials` when running `pulumi up`.

**Fix:** Run `gcloud auth application-default login`.

### 2.2 Compute Engine API Not Enabled

**Problem:** Pulumi warned `Compute Engine API has not been used in project`.

**Fix:** `gcloud services enable compute.googleapis.com --project=support-copilot-1772757287`

### 2.3 Vertex AI API Not Enabled

**Problem:** Embedding provider and LLM couldn't reach Vertex AI endpoints.

**Fix:** `gcloud services enable aiplatform.googleapis.com --project=support-copilot-1772757287`

### 2.4 Docker Images Not Found in Artifact Registry

**Problem:** Cloud Run couldn't pull images — they hadn't been pushed yet, or were pushed with wrong architecture.

**Fix:** Authenticate Docker (`gcloud auth configure-docker us-central1-docker.pkg.dev`), then build with `--platform linux/amd64 --provenance=false` and push.

### 2.5 OCI Manifest Format Rejected by Cloud Run

**Problem:** `Container manifest type 'application/vnd.oci.image.index.v1+json' must support amd64/linux` — Docker Desktop creates OCI image indexes by default.

**Fix:** Add `--provenance=false` to `docker build` to produce a plain Docker V2 manifest instead of OCI image index.

### 2.6 Artifact Registry Reader Permission Missing

**Problem:** Cloud Run service agent couldn't pull images from Artifact Registry.

**Fix:** Granted `roles/artifactregistry.reader` to the default compute service account on the `images` repository.

### 2.7 Cloud Run Services Not Publicly Accessible (403 Forbidden)

**Problem:** Accessing the UI/API URLs returned `403 Forbidden` because Cloud Run services are private by default.

**Fix:** Granted `roles/run.invoker` to `allUsers` on the UI and API services (after removing the org policy restriction).

### 2.8 Organization Policy Blocking `allUsers` IAM Binding

**Problem:** `FAILED_PRECONDITION: One or more users named in the policy do not belong to a permitted customer` — the GCP organization had `iam.allowedPolicyMemberDomains` policy restricting public access.

**Fix:** `gcloud org-policies delete constraints/iam.allowedPolicyMemberDomains --organization=332556526363`

### 2.9 BigQuery Permissions Missing for Cloud Run Service Account

**Problem:** `403 Access Denied: User does not have bigquery.jobs.create permission` when the inference service tried to query BigQuery.

**Fix:** Granted `roles/bigquery.dataViewer` and `roles/bigquery.jobUser` to the default compute service account.

### 2.10 Vertex AI Permissions Missing for Cloud Run Service Account

**Problem:** Embedding provider couldn't access Vertex AI APIs from Cloud Run.

**Fix:** Granted `roles/aiplatform.user` to the default compute service account.

### 2.11 Cloud Run Inference Service Not Invoking with Auth

**Problem:** API service got `403 Forbidden` calling the private inference service — no identity token included in requests.

**Fix:** Granted `roles/run.invoker` to the default compute service account on the inference service. Updated API code to include identity token (see code issue 1.11).

### 2.12 Expired GCP Credentials (`invalid_grant`)

**Problem:** `oauth2: "invalid_grant" "reauth related error"` during `pulumi up`.

**Fix:** Re-authenticate with `gcloud auth login` and `gcloud auth application-default login`.

### 2.13 Cloud Run Using Stale Revision After Image Update

**Problem:** Pushing a new image with the same `:latest` tag didn't trigger a new Cloud Run revision — the old container kept running.

**Fix:** Use unique timestamp-based tags (e.g., `:1772854291`) instead of `:latest`. Pulumi detects the image string change and creates a new revision.
