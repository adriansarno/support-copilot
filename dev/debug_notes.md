

# Local tests  (no GCP needed)

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
  
## Docker build smoke test
   
#### Generate the uv lock files for reproducibility  
uv lock --directory acquisition  
uv lock --directory inference  
uv lock --directory api  
uv lock --directory training  
  

docker build -t TAG_NAME SOURCE_FOLDER  
-t: tag  we use the prefix "sc-" for "support copilot"  
SOURCE_FOLDER: path to the folder containing the "Dockerfile" file  

open -a docker  

docker build -t sc-api ./api  
docker build -t sc-inference ./inference  
docker build -t sc-ui ./ui  
docker build -t sc-acquisition ./acquisition  
docker build -t sc-training ./training  
  
### Cleanup
rm -rf api/.venv inference/.venv ui/node_modules ui/.next    

### Initialize git and commit
git init  
git add .  
git commit -m "Customer Support RAG Copilot: 5-module system with hybrid retrieval, answer grading, and React UI"  

gh repo create support-copilot --public --source=. --push



# GCP deployment

## Tasks  
Create the GCP project
Set up .env with your real GCP project and API keys  
Run cd infra && pulumi up to provision BigQuery, GCS, etc.  
Place some test PDFs/tickets in data/ and run make acquire  
make up for the full stack  
Open localhost:3000 and ask a real question  


### Create the GCP project and link it to billing account
gcloud projects create support-copilot-$(date +%s) --name="Support Copilot"  

- project id [support-copilot-1772757287]  

gcloud config set project support-copilot-1772757287  

gcloud billing projects link PROJECT_ID_FROM_ABOVE --billing-account=BILLING_ACCOUNT_ID  


### Create a service account for CI/CD (GitHub Actions)
IAM Admin / Service accounts / Create sevice account  
gcloud org-policies delete iam.  disableServiceAccountKeyCreation --organization=sarno.ai  
  

### disable no-service-account-key-creation policy
  
gcloud org-policies describe iam.disableServiceAccountKeyCreation \  
  --organization=$(gcloud organizations list   --format='value(ID)' --filter='displayName:sarno.ai')  
  
gcloud org-policies delete iam.disableServiceAccountKeyCreation \  
  --organization=$(gcloud organizations list   --format='value(ID)' --filter='displayName:sarno.ai')  

### Create a json key
IAM Admin / Service accounts / Create sevice account /Keys  


### Step 1: Create the .env file
cp .env.example .env  

### Step 2: Enable required GCP APIs

gcloud services enable \  
  bigquery.googleapis.com \  
  storage.googleapis.com \  
  aiplatform.googleapis.com \  
  run.googleapis.com \  
  artifactregistry.googleapis.com \  
  pubsub.googleapis.com \  
  secretmanager.googleapis.com  

gcloud services enable compute.googleapis.com --project=support-copilot-1772757287  


### Step 3: Deploy infrastructure with Pulumi
  
brew install pulumi  

gcloud auth application-default login  
  
cd infra   
python -m venv venv  
source venv/bin/activate  
pip install -r requirements.txt  


###### Set the project in the Pulumi config  
pulumi stack init dev  
pulumi config set gcp:project support-copilot-1772757287  
pulumi config set gcp:region us-central1  
  
###### Preview what will be created
pulumi preview   

####  Deploy

###### 1. Authenticate Docker to Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev  

###### 2. Build and push all 3 images (from the support-copilot root)
<!-- this is huge, 8GB. To shrink it, Install CPU-only PyTorch (saves ~5-6 GB by excluding CUDA). -->
  
docker build --platform linux/amd64 --provenance=false \  
  -t us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:latest \  
  -f inference/Dockerfile .  
docker push us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:latest  
  
docker build --platform linux/amd64 --provenance=false \  
  -t us-central1-docker.pkg.dev/support-copilot-1772757287/images/api:latest \  
  -f api/Dockerfile .  
docker push us-central1-docker.pkg.dev/support-copilot-1772757287/images/api:latest  
  
# Use the same API_KEY as in pulumi config (infra); omit if API uses default
docker build --platform linux/amd64 --provenance=false \  
  --build-arg NEXT_PUBLIC_API_URL=https://support-copilot-api-pmbduk6nhq-uc.a.run.app \  
  --build-arg NEXT_PUBLIC_API_KEY=change-me-in-production \  
  -t us-central1-docker.pkg.dev/support-copilot-1772757287/images/ui:latest \  
  -f ui/Dockerfile .  
docker push us-central1-docker.pkg.dev/support-copilot-1772757287/images/ui:latest  

###### 3. The Cloud Run service agent needs read access to Artifact Registry - give access

PROJECT_NUMBER=$(gcloud projects describe support-copilot-1772757287 --format='value(projectNumber)')  
```
gcloud artifacts repositories add-iam-policy-binding images \
  --location=us-central1 \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/artifactregistry.reader"
```
###### 3. run pulumi
cd infra && pulumi up  

##### FIX an image - first check the logs for errors
it may still be running the old revision (00001-45p — same as before). Check if Cloud Run actually picked up the new image:  
  
```
gcloud logging read \
  'resource.type="cloud_run_revision" resource.labels.service_name="support-copilot-inference" severity>=ERROR' \
  --project=support-copilot-1772757287 \
  --limit=20 \
  --freshness=10m \
  --format="table(timestamp, textPayload)"
```
###### rebuild with a unique tag, push, and deploy:  
```
TAG=$(date +%s)

docker build --platform linux/amd64 --provenance=false --no-cache \
  -t us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:$TAG \
  -f inference/Dockerfile .

docker push us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:$TAG


gcloud artifacts docker images list us-central1-docker.pkg.dev/support-copilot-1772757287/images --include-tags
```


Test the container locally:  
```
docker run --rm -it --platform linux/amd64 \
  -e GCP_PROJECT=test -e GCP_REGION=us-central1 -e PROMPT_VERSION=v1 \
  -p 8001:8001 \
  us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:1772817494
```

```
docker run --rm -it --platform linux/amd64 \
  -e GCP_PROJECT=support-copilot-1772757287 \
  -e GCP_REGION=us-central1 \
  -e PROMPT_VERSION=v1 \
  -e EMBEDDING_PROVIDER=openai \
  -e OPENAI_API_KEY=test-key \
  -p 8001:8001 \
  us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:1772820520 
  ```
```
  # Use whatever tag you just built
docker run --rm -it --platform linux/amd64 \
  -e GCP_PROJECT=test \
  -e GCP_REGION=us-central1 \
  -e PROMPT_VERSION=v1 \
  -e EMBEDDING_PROVIDER=openai \
  -e OPENAI_API_KEY=sk-fake \
  -p 8001:8001 \
  us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:1772820520 
  ```

  ```
  # if you are are going to test locally, tag it as test to simplify  

# build image
docker build --platform linux/amd64 --provenance=false --no-cache \
  -t us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:test \
  -f inference/Dockerfile .

# run container
docker run --rm -it --platform linux/amd64 \
  -e GCP_PROJECT=test -e GCP_REGION=us-central1 -e PROMPT_VERSION=v1 \
  -e EMBEDDING_PROVIDER=openai -e OPENAI_API_KEY=sk-fake \
  -p 8001:8001 \
  us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:test

# test server  from another terminal
curl http://localhost:8001/health  
```

If it works, retag the image and deploy it. You can just re-tag it because it's the same image:  
  
```
TAG=$(date +%s)
echo "Tag: $TAG"

docker tag \
us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:test \
us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:$TAG


docker images | grep inference
```  

Then push it:  

```
docker push us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:$TAG
```  
   
Then update the TAG in infra/__main__.py and run pulumi up.  

Outputs:  
  + api_url         : "https://support-copilot-api-pmbduk6nhq-uc.a.run.app"  
  + artifacts_bucket: "gs://support-copilot-1772757287-artifacts"  
  + bq_dataset      : "support_copilot"  
  + docker_repo     : "projects/support-copilot-1772757287/locations/us-central1/repositories/images"  
  + inference_url   : "https://support-copilot-inference-pmbduk6nhq-uc.a.run.app"  
  + raw_docs_bucket : "gs://support-copilot-1772757287-raw-docs"  
  + ui_url          : "https://support-copilot-ui-pmbduk6nhq-uc.a.run.app"  


  Remove GPU and CUDA to reduce the size of the inference image:  

```
  cd /Users/adrian/study/commitment/job/cloud-ai/portfolio/support-copilot
uv lock --directory inference
```


gcloud org-policies describe constraints/iam.allowedPolicyMemberDomains \
  --organization=332556526363



# Remove the restriction
gcloud org-policies delete constraints/iam.allowedPolicyMemberDomains \
  --project=support-copilot-1772757287

Cloud Run services are private by default. You need to allow unauthenticated access for the UI:  

```gcloud run services add-iam-policy-binding support-copilot-ui \  --region=us-central1 \  --project=support-copilot-1772757287 \  --member="allUsers" \  --role="roles/run.invoker"```  

You'll likely also want to do the same for the API service so the UI can call it:  

```gcloud run services add-iam-policy-binding support-copilot-api \  --region=us-central1 \  --project=support-copilot-1772757287 \  --member="allUsers" \  --role="roles/run.invoker"  ```

The inference service can stay private since only the API calls it internally.  

    The policy isn't set on the project — it's inherited from the organization. Check and delete it at the org level:  

```gcloud org-policies describe constraints/iam.allowedPolicyMemberDomains \
  --organization=332556526363
```

```gcloud org-policies delete constraints/iam.allowedPolicyMemberDomains \
  --organization=332556526363```

Deleted policy [organizations/332556526363/policies/iam.  allowedPolicyMemberDomains].  
  

After that, retry the allUsers IAM bindings for the UI and API services.  

```gcloud run services add-iam-policy-binding support-copilot-ui \
  --region=us-central1 \
  --project=support-copilot-1772757287 \
  --member="allUsers" \
  --role="roles/run.invoker"

gcloud run services add-iam-policy-binding support-copilot-api \
  --region=us-central1 \
  --project=support-copilot-1772757287 \
  --member="allUsers" \
  --role="roles/run.invoker"```



##### test

```
docker run --rm -it --platform linux/amd64 \
  -e GCP_PROJECT=test \
  -e GCP_REGION=us-central1 \
  -e PROMPT_VERSION=v1 \
  -e EMBEDDING_PROVIDER=openai \
  -e OPENAI_API_KEY=sk-fake \
  -p 8001:8001 \
  test
  ```
  curl http://localhost:8001/health

<!-- push -->

TAG=$(date +%s)
docker tag us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:test \
           us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:$TAG
docker push us-central1-docker.pkg.dev/support-copilot-1772757287/images/inference:$TAG
echo "Update TAG in infra/__main__.py to: $TAG"

```
Outputs:
    api_url         : "https://support-copilot-api-pmbduk6nhq-uc.a.run.app"
    artifacts_bucket: "gs://support-copilot-1772757287-artifacts"
    bq_dataset      : "support_copilot"
    docker_repo     : "projects/support-copilot-1772757287/locations/us-central1/repositories/images"
    inference_url   : "https://support-copilot-inference-pmbduk6nhq-uc.a.run.app"
    raw_docs_bucket : "gs://support-copilot-1772757287-raw-docs"
    ui_url          : "https://support-copilot-ui-pmbduk6nhq-uc.a.run.app"

Resources:
    ~ 1 updated
    18 unchanged

Duration: 4m21s
```


---


The full pipeline needs:

1. Documents ingested into BigQuery and Vertex Vector Search (via the acquisition pipeline)
1. LLM API keys set (OpenAI or Gemini) for the inference service to generate answers
1. Vertex AI APIs enabled for embeddings and vector search
But the infrastructure and services are all deployed and communicating correctly:  

- UI → API: working (no more localhost issue)
- API → Inference: working (no more 403)
-Health checks: passing
To get real answers flowing, the next steps would be:

1. Ingest some test documents via the acquisition pipeline
1. Set real API keys as env vars or Secret Manager secrets on the inference service
1. Enable the Vertex AI API in your GCP project


Set up environment variables. You need:

GCP_PROJECT=support-copilot-1772757287
GCP_REGION=us-central1
EMBEDDING_PROVIDER=vertex

# Install acquisition deps
uv sync --directory acquisition


PYTHONPATH=$PWD uv run --directory acquisition python -m acquisition.cli run \
  --source-dir ./sample-docs \
  --chunk-method recursive \
  --chunk-size 512 \
  --version 1 \
  --skip-vertex


Cloud run service needs big query permissions

```
PROJECT_NUMBER=$(gcloud projects describe support-copilot-1772757287 --format='value(projectNumber)')

gcloud projects add-iam-policy-binding support-copilot-1772757287 \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding support-copilot-1772757287 \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"
```   
  
Also grant Vertex AI access for the embedding provider:  

```
gcloud projects add-iam-policy-binding support-copilot-1772757287 \
  --member="serviceAccount:421802028428-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```


Test:  

```
 curl -X POST https://support-copilot-api-pmbduk6nhq-uc.a.run.app/chat/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-in-production" \
  -d '{"message": "How do I reset my password?"}'
```

```
It's working end-to-end! The full RAG pipeline is live:

BM25 retrieval found the password reset document from BigQuery
Gemini LLM generated a cited answer with [Source 1] references
Answer grading scored it 1.0/1.0/1.0 (relevance, faithfulness, completeness)
Citations and source trace are populated
Prompt metadata shows version v1 with hash
```


### Ingest more documents, update the version

```
PYTHONPATH=$PWD uv run --directory acquisition python -m acquisition.cli run \
  --source-dir ./sample-docs \
  --chunk-method recursive \
  --chunk-size 512 \
  --version 2 \
  --skip-vertex
  ```

---
```
Here are improvements organized by priority:

High Impact — Quick Wins

Add more documents — ingest real support docs, FAQs, product guides. More data = better answers.
Change the default API key — change-me-in-production is hardcoded in both the UI and API. Set a real key via Secret Manager.
Enable BigQuery SEARCH index — replace the LIKE-based search with a proper full-text search index for better BM25 quality:
CREATE SEARCH INDEX chunks_search_idx ON `support_copilot.chunks`(content)
Bake the reranker model into the Docker image — add the model download to the Dockerfile build step, then re-enable the reranker for better retrieval quality.
Medium Impact — Production Readiness

Persistent chat storage — chats are currently in-memory (_chats: dict). Store them in BigQuery so they survive restarts.
Streaming responses — the pipeline has a stream() method but the API doesn't use it yet. Wire SSE streaming for real-time token-by-token responses in the UI.
Error handling in the UI — show meaningful error messages instead of "Sorry, an error occurred."
Cost control — set Cloud Run min instances to 0 and max concurrency to avoid surprise bills. Add budget alerts.
Portfolio Polish

Add a demo video/GIF to the README showing the chat in action.
Seed with interesting data — ingest a well-known open-source product's docs (e.g., Stripe API docs, Kubernetes docs) so recruiters see compelling answers.
Add the GitHub Actions CI/CD — the workflows exist but aren't connected to a repo yet. Push to GitHub and wire them up.
Architecture diagram — add a visual diagram to the README showing the flow: UI → API → Inference → BigQuery/Vertex/LLM.
Advanced — Differentiation

Enable hybrid retrieval — create a Vertex Vector Search index so you get BM25 + vector search with RRF fusion.
Fine-tune the reranker — run the training pipeline on your ingested data.
A/B prompt testing — create prompts/v2/ with different templates and compare answer quality.
Observability — add W&B logging for retrieval/generation metrics, latency traces.
Which of these do you want to tackle first?
```
---
---
# Documetn upload features

```
curl -X POST http://127.0.0.1:8000/upload/ \
  -H "X-API-Key:ff87f01d75b7424637bb9f2bf65acb42af4bea66ba1d939e36d5ccf34b3b426a" \
  -F "files=@acquisition/sample-docs/password-reset.html" \
  -F "files=@acquisition/sample-docs/doman-adaptation-ben-david.pdf"
```

To add both files to the knowledge base run:
```
PYTHONPATH=$PWD uv run --directory acquisition python -m acquisition.cli run \
  --source-dir gs://support-copilot-1772757287-raw-docs/uploads/ \
  --chunk-method recursive --version 2 --skip-vertex
```




To debug the crash locally before deploying:   
 - note that this is a macos build and cannot be deployed  

```
docker build -t api-debug -f api/Dockerfile .
docker run --rm -e GCP_PROJECT=support-copilot-1772757287 \
  -e GCS_RAW_DOCS_BUCKET=support-copilot-1772757287-raw-docs \
  -e INFERENCE_URL=https://support-copilot-inference-pmbduk6nhq-uc.a.run.app \
  api-debug
```

cd infra
pulumi config set --secret api_key ff87f01d75b7424637bb9f2bf65acb42af4bea66ba1d939e36d5ccf34b3b426a

Build api
```
TAG=$(date +%s)
echo "API TAG is: "$TAG

docker build --platform linux/amd64 --provenance=false --no-cache \
  -t us-central1-docker.pkg.dev/support-copilot-1772757287/images/api:$TAG \
  -f api/Dockerfile .

docker push us-central1-docker.pkg.dev/support-copilot-1772757287/images/api:$TAG


gcloud artifacts docker images list us-central1-docker.pkg.dev/support-copilot-1772757287/images --include-tags
```


Build ui
```
TAG=$(date +%s)
echo "UI TAG is: "$TAG

docker build --platform linux/amd64 --provenance=false --no-cache \
  --build-arg NEXT_PUBLIC_API_URL=https://support-copilot-api-pmbduk6nhq-uc.a.run.app \
  --build-arg NEXT_PUBLIC_API_KEY=ff87f01d75b7424637bb9f2bf65acb42af4bea66ba1d939e36d5ccf34b3b426a \
  -t us-central1-docker.pkg.dev/support-copilot-1772757287/images/ui:$TAG \
  -f ui/Dockerfile .

docker push us-central1-docker.pkg.dev/support-copilot-1772757287/images/ui:$TAG

gcloud artifacts docker images list us-central1-docker.pkg.dev/support-copilot-1772757287/images --include-tags
```


test

curl https://support-copilot-api-pmbduk6nhq-uc.a.run.app/health

curl -X POST https://support-copilot-api-pmbduk6nhq-uc.a.run.app/chat/ \
  -H "X-API-Key:ff87f01d75b7424637bb9f2bf65acb42af4bea66ba1d939e36d5ccf34b3b426a" \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I reset my password?"}'

Check the logs

```
gcloud logging read \
  'resource.type="cloud_run_revision" resource.labels.service_name="support-copilot-api" severity>=ERROR' \
  --project=support-copilot-1772757287 \
  --limit=20 \
  --freshness=30m \
  --format="table(timestamp, textPayload)"
```