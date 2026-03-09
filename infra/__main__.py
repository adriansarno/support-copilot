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

artifacts_bucket = gcp.storage.Bucket(
    "artifacts-bucket",
    name=f"{project}-artifacts",
    location="US",
    uniform_bucket_level_access=True,
    project=project,
)

raw_docs_bucket = gcp.storage.Bucket(
    "raw-docs-bucket",
    name=f"{project}-raw-docs",
    location="US",
    uniform_bucket_level_access=True,
    project=project,
)

# Grant API service (Cloud Run default compute SA) objectCreator for uploads
proj = gcp.organizations.get_project(project_id=project)
api_compute_sa = f"{proj.number}-compute@developer.gserviceaccount.com"
gcp.storage.BucketIAMMember(
    "raw-docs-api-upload",
    bucket=raw_docs_bucket.name,
    role="roles/storage.objectCreator",
    member=f"serviceAccount:{api_compute_sa}",
)

# ---------------------------------------------------------------------------
# Artifact Registry
# ---------------------------------------------------------------------------

docker_repo = gcp.artifactregistry.Repository(
    "docker-repo",
    repository_id="images",
    format="DOCKER",
    location=region,
    project=project,
)

# ---------------------------------------------------------------------------
# Pub/Sub (event bus for pipeline orchestration)
# ---------------------------------------------------------------------------

acquisition_topic = gcp.pubsub.Topic(
    "acquisition-events",
    name="acquisition-events",
    project=project,
)

training_topic = gcp.pubsub.Topic(
    "training-events",
    name="training-events",
    project=project,
)

feedback_topic = gcp.pubsub.Topic(
    "feedback-events",
    name="feedback-events",
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

INFERENCE_TAG = "1772991990" # unix epoch - is the timestamp of the image
API_TAG= "1773020117"
UI_TAG = "1773020117" 

inference_service = gcp.cloudrunv2.Service(
    "inference-service",
    name="support-copilot-inference",
    location=region,
    project=project,
    template={
        "containers": [
            {
                "image": f"{region}-docker.pkg.dev/{project}/images/inference:{INFERENCE_TAG}",
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
        "containers": [
            {
                "image": f"{region}-docker.pkg.dev/{project}/images/api:{API_TAG}",
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
        "containers": [
            {
                "image": f"{region}-docker.pkg.dev/{project}/images/ui:{UI_TAG}",
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
pulumi.export("inference_url", inference_service.uri)
pulumi.export("api_url", api_service.uri)
pulumi.export("ui_url", ui_service.uri)
