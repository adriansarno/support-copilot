"""Fine-tune a small answer-style model using DeepSeek API or local LoRA."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, TaskType
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_MODEL = "deepseek-ai/deepseek-llm-7b-chat"


def finetune_lora(
    train_path: Path,
    val_path: Path,
    output_dir: Path,
    *,
    base_model: str = DEFAULT_BASE_MODEL,
    lora_r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
    epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 2e-4,
    max_seq_length: int = 1024,
    wandb_project: str = "",
    wandb_run_name: str = "",
) -> dict:
    """Fine-tune with LoRA using HuggingFace PEFT."""
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading tokenizer and base model: %s", base_model)
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    def format_sample(sample: dict) -> str:
        return (
            f"### Instruction:\n{sample['instruction']}\n\n"
            f"### Input:\n{sample['input']}\n\n"
            f"### Response:\n{sample['output']}"
        )

    train_ds = load_dataset("json", data_files=str(train_path), split="train")
    val_ds = load_dataset("json", data_files=str(val_path), split="train")

    def tokenize(sample):
        text = format_sample(sample)
        return tokenizer(
            text,
            truncation=True,
            max_length=max_seq_length,
            padding="max_length",
        )

    train_ds = train_ds.map(tokenize, remove_columns=train_ds.column_names)
    val_ds = val_ds.map(tokenize, remove_columns=val_ds.column_names)

    report_to = []
    if wandb_project:
        report_to.append("wandb")

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        warmup_ratio=0.1,
        weight_decay=0.01,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        report_to=report_to,
        run_name=wandb_run_name or f"answer-style-{int(time.time())}",
        bf16=torch.cuda.is_available(),
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    logger.info("Starting LoRA fine-tuning...")
    train_result = trainer.train()

    model.save_pretrained(output_dir / "adapter")
    tokenizer.save_pretrained(output_dir / "adapter")

    metrics = {
        "train_loss": train_result.metrics.get("train_loss", 0),
        "train_runtime": train_result.metrics.get("train_runtime", 0),
        "adapter_path": str(output_dir / "adapter"),
    }

    eval_metrics = trainer.evaluate()
    metrics["eval_loss"] = eval_metrics.get("eval_loss", 0)

    with open(output_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Fine-tuning complete: %s", metrics)
    return metrics
