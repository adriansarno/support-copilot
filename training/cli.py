"""Training pipeline CLI: build datasets, fine-tune, train reranker, evaluate."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import typer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training.answer_style.dataset import build_qa_dataset
from training.answer_style.finetune import finetune_lora
from training.answer_style.eval import run_full_eval
from training.reranker.dataset import build_reranker_dataset
from training.reranker.train import train_reranker
from training.reranker.eval import evaluate_reranker
from training import wandb_utils

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

app = typer.Typer(help="Support Copilot Training Pipeline")


def _settings():
    from shared.config import get_settings
    return get_settings()


@app.command()
def build_dataset(
    output_dir: Path = typer.Option(Path("./datasets"), help="Output directory"),
    max_samples: int = typer.Option(5000, help="Max Q&A pairs"),
):
    """Build Q&A and reranker datasets from BigQuery."""
    s = _settings()

    wandb_utils.init_wandb(
        project=s.wandb_project,
        run_name="build-dataset",
        config={"max_samples": max_samples},
        api_key=s.wandb_api_key,
        tags=["dataset"],
    )

    qa_stats = build_qa_dataset(
        s.gcp_project, s.bq_dataset, s.bq_chunks_table,
        output_dir / "answer_style",
        max_samples=max_samples,
    )
    wandb_utils.log_dataset_artifact(
        "answer-style-dataset", output_dir / "answer_style",
        metadata=qa_stats,
    )

    rr_stats = build_reranker_dataset(
        s.gcp_project, s.bq_dataset, s.bq_chunks_table,
        output_dir / "reranker",
        max_triples=max_samples,
    )
    wandb_utils.log_dataset_artifact(
        "reranker-dataset", output_dir / "reranker",
        metadata=rr_stats,
    )

    wandb_utils.finish_wandb()
    typer.echo(f"Datasets built: QA={qa_stats['total_pairs']}, Reranker={rr_stats['total_triples']}")


@app.command()
def finetune(
    dataset_dir: Path = typer.Option(Path("./datasets/answer_style"), help="Dataset directory"),
    output_dir: Path = typer.Option(Path("./models/answer_style"), help="Model output"),
    epochs: int = typer.Option(3, help="Training epochs"),
    batch_size: int = typer.Option(4, help="Batch size"),
    learning_rate: float = typer.Option(2e-4, help="Learning rate"),
):
    """Fine-tune the answer-style model with LoRA."""
    s = _settings()

    wandb_utils.init_wandb(
        project=s.wandb_project,
        run_name="answer-style-finetune",
        config={"epochs": epochs, "batch_size": batch_size, "lr": learning_rate},
        api_key=s.wandb_api_key,
        tags=["finetune", "answer-style"],
    )

    metrics = finetune_lora(
        train_path=dataset_dir / "train.jsonl",
        val_path=dataset_dir / "val.jsonl",
        output_dir=output_dir,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        wandb_project=s.wandb_project,
    )

    wandb_utils.log_model_artifact(
        "answer-style-model", output_dir / "adapter",
        metadata=metrics,
    )
    wandb_utils.finish_wandb()
    typer.echo(f"Fine-tuning complete: eval_loss={metrics.get('eval_loss', 'N/A')}")


@app.command()
def train_rr(
    dataset_dir: Path = typer.Option(Path("./datasets/reranker"), help="Reranker dataset"),
    output_dir: Path = typer.Option(Path("./models/reranker"), help="Model output"),
    epochs: int = typer.Option(3, help="Training epochs"),
    batch_size: int = typer.Option(32, help="Batch size"),
):
    """Train the cross-encoder reranker."""
    s = _settings()

    wandb_utils.init_wandb(
        project=s.wandb_project,
        run_name="reranker-training",
        config={"epochs": epochs, "batch_size": batch_size},
        api_key=s.wandb_api_key,
        tags=["training", "reranker"],
    )

    metrics = train_reranker(
        train_path=dataset_dir / "train.jsonl",
        val_path=dataset_dir / "val.jsonl",
        output_dir=output_dir,
        epochs=epochs,
        batch_size=batch_size,
    )

    wandb_utils.log_model_artifact(
        "reranker-model", output_dir,
        metadata=metrics,
    )
    wandb_utils.finish_wandb()
    typer.echo(f"Reranker training complete: {metrics}")


@app.command()
def eval_reranker(
    model_path: str = typer.Option(..., help="Path to trained reranker"),
    val_path: Path = typer.Option(Path("./datasets/reranker/val.jsonl"), help="Validation data"),
    output_path: Path = typer.Option(Path("./eval/reranker_metrics.json"), help="Output metrics"),
):
    """Evaluate the trained reranker."""
    metrics = evaluate_reranker(model_path, val_path, output_path=output_path)
    typer.echo(f"nDCG@10={metrics['ndcg@10']:.4f}  MRR={metrics['mrr']:.4f}")


@app.command()
def run(
    dataset_dir: Path = typer.Option(Path("./datasets"), help="Root dataset dir"),
    model_dir: Path = typer.Option(Path("./models"), help="Root model dir"),
    max_samples: int = typer.Option(5000, help="Max dataset samples"),
    epochs: int = typer.Option(3, help="Training epochs"),
):
    """Run full training pipeline: build datasets → finetune → train reranker → evaluate."""
    s = _settings()

    build_qa_dataset(
        s.gcp_project, s.bq_dataset, s.bq_chunks_table,
        dataset_dir / "answer_style",
        max_samples=max_samples,
    )
    build_reranker_dataset(
        s.gcp_project, s.bq_dataset, s.bq_chunks_table,
        dataset_dir / "reranker",
        max_triples=max_samples,
    )

    train_reranker(
        train_path=dataset_dir / "reranker" / "train.jsonl",
        val_path=dataset_dir / "reranker" / "val.jsonl",
        output_dir=model_dir / "reranker",
        epochs=epochs,
    )

    metrics = evaluate_reranker(
        str(model_dir / "reranker"),
        dataset_dir / "reranker" / "val.jsonl",
    )

    typer.echo(f"Pipeline complete. Reranker nDCG@10={metrics['ndcg@10']:.4f}")


if __name__ == "__main__":
    app()
