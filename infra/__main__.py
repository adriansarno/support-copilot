"""Pulumi IaC: BigQuery, GCS, Vertex AI, Cloud Run, Pub/Sub, Secret Manager."""

import pulumi
import pulumi_gcp as gcp

config = pulumi.Config()
gcp_config = pulumi.Config("gcp")
project = gcp_config.require("project")
region = gcp_config.require("region")
environment = config.get("environment") or "dev"
api_key = config.get_secret("api_key") or config.get("api_key")

# ---------------------------------------------------------------------------
# BigQuery
# ---------------------------------------------------------------------------

bq_dataset = gcp.bigquery.Dataset(
    "support-copilot-dataset",
    dataset_id="support_copilot",
    friendly_name="Support Copilot",
    description="Chunks, embeddings, feedback, and chat data",
    location="US",
    project=project,
)

bq_chunks_table = gcp.bigquery.Table(
    "chunks-table",
    dataset_id=bq_dataset.dataset_id,
    table_id="chunks",
    project=project,
    schema="""[
        {"name": "chunk_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "doc_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "source_type", "type": "STRING"},
        {"name": "title", "type": "STRING"},
        {"name": "content", "type": "STRING"},
        {"name": "metadata", "type": "JSON"},
        {"name": "embedding", "type": "FLOAT64", "mode": "REPEATED"},
        {"name": "created_at", "type": "TIMESTAMP"},
        {"name": "version", "type": "INT64"}
    ]""",
)

bq_feedback_table = gcp.bigquery.Table(
    "feedback-table",
    dataset_id=bq_dataset.dataset_id,
    table_id="feedback",
    project=project,
    schema="""[
        {"name": "feedback_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "chat_id", "type": "STRING"},
        {"name": "message_id", "type": "STRING"},
        {"name": "rating", "type": "INT64"},
        {"name": "comment", "type": "STRING"},
        {"name": "created_at", "type": "TIMESTAMP"}
    ]""",
)

bq_chats_table = gcp.bigquery.Table(
    "chats-table",
    dataset_id=bq_dataset.dataset_id,
    table_id="chats",
    project=project,
    schema="""[
        {"name": "chat_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "messages", "type": "JSON"},
        {"name": "created_at", "type": "TIMESTAMP"},
        {"name": "updated_at", "type": "TIMESTAMP"}
    ]""",
)

# ---------------------------------------------------------------------------
# GCS Buckets
# ---------------------------------------------------------------------------

# Names carry the app name because other apps share the project.
artifacts_bucket = gcp.storage.Bucket(
    "support-copilot-artifacts",
    name=f"{project}-support-copilot-artifacts",
    location="US",
    uniform_bucket_level_access=True,
    project=project,
)

raw_docs_bucket = gcp.storage.Bucket(
    "support-copilot-raw-docs",
    name=f"{project}-support-copilot-raw-docs",
    location="US",
    uniform_bucket_level_access=True,
    project=project,
)

# ---------------------------------------------------------------------------
# Runtime service account
# ---------------------------------------------------------------------------
# The three Cloud Run services run as this account, not as the project's default
# compute account, so the roles below do not extend to other apps in the project.
# All grants are additive (IAMMember): they never remove other members.

runtime_sa = gcp.serviceaccount.Account(
    "runtime-sa",
    account_id="support-copilot-run",
    display_name="support-copilot Cloud Run services",
    project=project,
)
runtime_member = runtime_sa.email.apply(lambda e: f"serviceAccount:{e}")

# Inference: embeddings and Gemini (Vertex AI), and BM25 queries on BigQuery.
for role in ["roles/aiplatform.user", "roles/bigquery.jobUser"]:
    gcp.projects.IAMMember(
        f"runtime-{role.split('/')[1]}",
        project=project,
        role=role,
        member=runtime_member,
    )
# Granted on the table, not the dataset: every update of the Dataset resource
# (for example a label change) rewrites the dataset's access list and removes
# grants made with DatasetIamMember. Table access (bigquery.IamMember) is a separate list.
gcp.bigquery.IamMember(
    "runtime-chunks-reader",
    project=project,
    dataset_id=bq_dataset.dataset_id,
    table_id=bq_chunks_table.table_id,
    role="roles/bigquery.dataViewer",
    member=runtime_member,
)

# API: document uploads to the raw-docs bucket.
gcp.storage.BucketIAMMember(
    "raw-docs-api-upload",
    bucket=raw_docs_bucket.name,
    role="roles/storage.objectCreator",
    member=runtime_member,
)

# ---------------------------------------------------------------------------
# Artifact Registry
# ---------------------------------------------------------------------------

docker_repo = gcp.artifactregistry.Repository(
    "support-copilot-images",
    repository_id="support-copilot-images",
    format="DOCKER",
    location=region,
    project=project,
)

# ---------------------------------------------------------------------------
# Pub/Sub (event bus for pipeline orchestration)
# ---------------------------------------------------------------------------

acquisition_topic = gcp.pubsub.Topic(
    "acquisition-events",
    name="support-copilot-acquisition-events",
    project=project,
)

training_topic = gcp.pubsub.Topic(
    "training-events",
    name="support-copilot-training-events",
    project=project,
)

feedback_topic = gcp.pubsub.Topic(
    "feedback-events",
    name="support-copilot-feedback-events",
    project=project,
)

# ---------------------------------------------------------------------------
# Secret Manager
# ---------------------------------------------------------------------------

secrets = {}
for secret_name in ["openai-api-key", "deepseek-api-key", "wandb-api-key", "jwt-secret", "api-key"]:
    secrets[secret_name] = gcp.secretmanager.Secret(
        f"secret-{secret_name}",
        secret_id=f"support-copilot-{secret_name}",
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        project=project,
    )

# ---------------------------------------------------------------------------
# Cloud Run Services
# ---------------------------------------------------------------------------

# Each service runs the image that the "latest" tag points to, pinned by its digest.
# The /deploy-app CI job pushes new images as "latest" and then runs pulumi up, so
# CI and a local pulumi up always deploy the same images and never undo each other.
# The images must exist before the first pulumi up of a new stack.
def latest_image(name: str) -> pulumi.Output[str]:
    return gcp.artifactregistry.get_docker_image_output(
        project=project,
        location=region,
        repository_id=docker_repo.repository_id,
        image_name=f"{name}:latest",
    ).self_link

inference_service = gcp.cloudrunv2.Service(
    "inference-service",
    name="support-copilot-inference",
    location=region,
    project=project,
    template={
        "service_account": runtime_sa.email,
        "containers": [
            {
                "image": latest_image("inference"),
                "ports": {"container_port": 8001},
                "resources": {
                    "limits": {"memory": "2Gi", "cpu": "2"},
                    "startup_cpu_boost": True,
                },
                "envs": [
                    {"name": "GCP_PROJECT", "value": project},
                    {"name": "GCP_REGION", "value": region},
                    {"name": "PROMPT_VERSION", "value": "v1"},
                    {"name": "SKIP_RERANKER", "value": "true"},
                    # gemini-2.0-flash-001 is not available to projects created
                    # after its cutoff; this preview model is served from "global" only.
                    {"name": "LLM_MODEL", "value": "gemini-3-flash-preview"},
                    {"name": "LLM_LOCATION", "value": "global"},
                ],
                "startup_probe": {
                    "http_get": {"path": "/health", "port": 8001},
                    "initial_delay_seconds": 5,
                    "period_seconds": 10,
                    "failure_threshold": 30,
                    "timeout_seconds": 5,
                },
            }
        ],
        "scaling": {"min_instance_count": 0, "max_instance_count": 5},
        "timeout": "600s",
    },
)

# The API calls inference with an identity token, so it needs invoker on inference.
gcp.cloudrunv2.ServiceIamMember(
    "inference-invoker-runtime",
    project=project,
    location=region,
    name=inference_service.name,
    role="roles/run.invoker",
    member=runtime_member,
)

api_envs = [
    {"name": "GCP_PROJECT", "value": project},
    {"name": "GCS_RAW_DOCS_BUCKET", "value": raw_docs_bucket.name},
    {"name": "INFERENCE_URL", "value": inference_service.uri},
]
if api_key is not None:
    api_envs.append({"name": "API_KEY", "value": api_key})

api_service = gcp.cloudrunv2.Service(
    "api-service",
    name="support-copilot-api",
    location=region,
    project=project,
    template={
        "service_account": runtime_sa.email,
        "containers": [
            {
                "image": latest_image("api"),
                "ports": {"container_port": 8000},
                "resources": {"limits": {"memory": "1Gi", "cpu": "1"}},
                "envs": api_envs,
                "startup_probe": {
                    "http_get": {"path": "/health", "port": 8000},
                    "initial_delay_seconds": 5,
                    "period_seconds": 10,
                    "failure_threshold": 30,
                    "timeout_seconds": 5,
                },
            }
        ],
        "scaling": {"min_instance_count": 0, "max_instance_count": 10},
    },
)

ui_service = gcp.cloudrunv2.Service(
    "ui-service",
    name="support-copilot-ui",
    location=region,
    project=project,
    template={
        "service_account": runtime_sa.email,
        "containers": [
            {
                "image": latest_image("ui"),
                "ports": {"container_port": 3000},
                "resources": {"limits": {"memory": "512Mi", "cpu": "1"}},
                "envs": [
                    {"name": "NEXT_PUBLIC_API_URL", "value": api_service.uri},
                ],
            }
        ],
        "scaling": {"min_instance_count": 0, "max_instance_count": 5},
    },
)

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

pulumi.export("bq_dataset", bq_dataset.dataset_id)
pulumi.export("artifacts_bucket", artifacts_bucket.url)
pulumi.export("raw_docs_bucket", raw_docs_bucket.url)
pulumi.export("docker_repo", docker_repo.id)
pulumi.export("runtime_service_account", runtime_sa.email)
pulumi.export("inference_url", inference_service.uri)
pulumi.export("api_url", api_service.uri)
pulumi.export("ui_url", ui_service.uri)
