"""Evaluate answer-style model with ROUGE, BERTScore, and LLM-as-judge."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import numpy as np
from rouge_score import rouge_scorer
from bert_score import score as bert_score_fn

logger = logging.getLogger(__name__)


def evaluate_rouge(predictions: list[str], references: list[str]) -> dict:
    """Compute ROUGE-1, ROUGE-2, ROUGE-L."""
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    scores = {"rouge1": [], "rouge2": [], "rougeL": []}

    for pred, ref in zip(predictions, references):
        result = scorer.score(ref, pred)
        for key in scores:
            scores[key].append(result[key].fmeasure)

    return {k: float(np.mean(v)) for k, v in scores.items()}


def evaluate_bert_score(predictions: list[str], references: list[str]) -> dict:
    """Compute BERTScore (P, R, F1)."""
    P, R, F1 = bert_score_fn(predictions, references, lang="en", verbose=False)
    return {
        "bertscore_precision": float(P.mean()),
        "bertscore_recall": float(R.mean()),
        "bertscore_f1": float(F1.mean()),
    }


async def evaluate_llm_judge(
    llm_provider,
    predictions: list[str],
    references: list[str],
    questions: list[str],
    *,
    max_samples: int = 50,
) -> dict:
    """Use an LLM to judge answer quality (accuracy, helpfulness, style)."""
    samples = min(len(predictions), max_samples)
    scores = {"accuracy": [], "helpfulness": [], "style": []}

    for i in range(samples):
        prompt = f"""Rate the following generated answer on three dimensions (0-10 each).

Question: {questions[i]}

Reference answer: {references[i]}

Generated answer: {predictions[i]}

Return JSON: {{"accuracy": <int>, "helpfulness": <int>, "style": <int>}}"""

        messages = [
            {"role": "system", "content": "You are an expert evaluator."},
            {"role": "user", "content": prompt},
        ]

        try:
            parsed = await llm_provider.generate_json(messages, temperature=0.0)
            scores["accuracy"].append(parsed.get("accuracy", 0))
            scores["helpfulness"].append(parsed.get("helpfulness", 0))
            scores["style"].append(parsed.get("style", 0))
        except Exception as e:
            logger.warning("LLM judge failed for sample %d: %s", i, e)

    return {
        f"llm_judge_{k}": float(np.mean(v)) if v else 0.0
        for k, v in scores.items()
    }


def run_full_eval(
    predictions: list[str],
    references: list[str],
    questions: list[str],
    *,
    output_path: Path | None = None,
    llm_provider=None,
) -> dict:
    """Run ROUGE + BERTScore + optional LLM judge evaluation."""
    metrics = {}
    metrics.update(evaluate_rouge(predictions, references))
    metrics.update(evaluate_bert_score(predictions, references))

    if llm_provider:
        llm_metrics = asyncio.run(
            evaluate_llm_judge(llm_provider, predictions, references, questions)
        )
        metrics.update(llm_metrics)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(metrics, f, indent=2)

    logger.info("Evaluation metrics: %s", metrics)
    return metrics
