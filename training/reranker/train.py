"""Train a cross-encoder reranker using sentence-transformers."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import torch
from datasets import load_dataset
from sentence_transformers import CrossEncoder, InputExample
from sentence_transformers.cross_encoder.evaluation import CERerankingEvaluator
from torch.utils.data import DataLoader

logger = logging.getLogger(__name__)

DEFAULT_BASE_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def train_reranker(
    train_path: Path,
    val_path: Path,
    output_dir: Path,
    *,
    base_model: str = DEFAULT_BASE_MODEL,
    epochs: int = 3,
    batch_size: int = 32,
    learning_rate: float = 2e-5,
    warmup_ratio: float = 0.1,
    wandb_project: str = "",
) -> dict:
    """Fine-tune a cross-encoder on query-document relevance pairs."""
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading base cross-encoder: %s", base_model)
    model = CrossEncoder(base_model, num_labels=1)

    train_ds = load_dataset("json", data_files=str(train_path), split="train")
    val_ds = load_dataset("json", data_files=str(val_path), split="train")

    train_examples = []
    for row in train_ds:
        train_examples.append(
            InputExample(texts=[row["query"], row["positive"]], label=1.0)
        )
        train_examples.append(
            InputExample(texts=[row["query"], row["negative"]], label=0.0)
        )

    train_dataloader = DataLoader(
        train_examples, shuffle=True, batch_size=batch_size
    )

    val_samples: dict[str, dict[str, float]] = {}
    for i, row in enumerate(val_ds):
        query = row["query"]
        if query not in val_samples:
            val_samples[query] = {}
        val_samples[query][row["positive"]] = 1.0
        val_samples[query][row["negative"]] = 0.0

    evaluator = CERerankingEvaluator(val_samples, name="val")

    warmup_steps = int(len(train_dataloader) * epochs * warmup_ratio)

    logger.info(
        "Training for %d epochs, %d steps, warmup=%d",
        epochs, len(train_dataloader) * epochs, warmup_steps,
    )

    model.fit(
        train_dataloader=train_dataloader,
        evaluator=evaluator,
        epochs=epochs,
        warmup_steps=warmup_steps,
        optimizer_params={"lr": learning_rate},
        output_path=str(output_dir),
        evaluation_steps=len(train_dataloader) // 2,
        save_best_model=True,
    )

    metrics = {
        "model_path": str(output_dir),
        "base_model": base_model,
        "epochs": epochs,
        "train_examples": len(train_examples),
    }

    with open(output_dir / "training_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Reranker training complete: %s", metrics)
    return metrics
