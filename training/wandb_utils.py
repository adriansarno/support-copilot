"""Weights & Biases integration: dataset versioning, run tracking, model registry."""

from __future__ import annotations

import logging
from pathlib import Path

import wandb

logger = logging.getLogger(__name__)


def init_wandb(
    project: str,
    run_name: str,
    config: dict | None = None,
    *,
    api_key: str = "",
    tags: list[str] | None = None,
) -> wandb.run:
    """Initialize a W&B run."""
    if api_key:
        wandb.login(key=api_key)

    run = wandb.init(
        project=project,
        name=run_name,
        config=config or {},
        tags=tags or [],
    )
    logger.info("W&B run initialized: %s/%s", project, run_name)
    return run


def log_dataset_artifact(
    name: str,
    data_dir: Path,
    *,
    artifact_type: str = "dataset",
    metadata: dict | None = None,
) -> wandb.Artifact:
    """Version a dataset directory as a W&B Artifact."""
    artifact = wandb.Artifact(name=name, type=artifact_type, metadata=metadata or {})
    artifact.add_dir(str(data_dir))
    wandb.log_artifact(artifact)
    logger.info("Logged dataset artifact: %s", name)
    return artifact


def log_model_artifact(
    name: str,
    model_dir: Path,
    *,
    metadata: dict | None = None,
) -> wandb.Artifact:
    """Version a trained model as a W&B Artifact and link to registry."""
    artifact = wandb.Artifact(name=name, type="model", metadata=metadata or {})
    artifact.add_dir(str(model_dir))
    wandb.log_artifact(artifact)
    logger.info("Logged model artifact: %s", name)
    return artifact


def log_eval_table(
    table_name: str,
    columns: list[str],
    data: list[list],
) -> None:
    """Log an evaluation results table to W&B."""
    table = wandb.Table(columns=columns, data=data)
    wandb.log({table_name: table})
    logger.info("Logged eval table: %s (%d rows)", table_name, len(data))


def finish_wandb() -> None:
    """Finish the current W&B run."""
    wandb.finish()
    logger.info("W&B run finished")
