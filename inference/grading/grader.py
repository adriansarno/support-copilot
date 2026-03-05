"""Post-generation answer quality grading using LLM-as-judge."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from inference.retrieval.bm25 import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass
class GradeResult:
    relevance: float
    faithfulness: float
    completeness: float
    explanation: str
    low_confidence: bool

    def to_dict(self) -> dict:
        return {
            "relevance": self.relevance,
            "faithfulness": self.faithfulness,
            "completeness": self.completeness,
            "explanation": self.explanation,
            "low_confidence": self.low_confidence,
        }


class AnswerGrader:
    """Grade answers using the grading prompt + LLM-as-judge."""

    LOW_CONFIDENCE_THRESHOLD = 0.7

    def __init__(self, llm_provider, prompt_manager):
        self._llm = llm_provider
        self._prompts = prompt_manager

    async def grade(
        self,
        question: str,
        answer: str,
        chunks: list[RetrievedChunk],
    ) -> GradeResult:
        chunk_dicts = [{"content": c.content} for c in chunks]
        grading_prompt = self._prompts.render(
            "grading",
            question=question,
            answer=answer,
            chunks=chunk_dicts,
        )

        messages = [
            {"role": "system", "content": "You are an expert quality evaluator."},
            {"role": "user", "content": grading_prompt},
        ]

        try:
            parsed = await self._llm.generate_json(messages, temperature=0.0)

            relevance = float(parsed.get("relevance", 0.0))
            faithfulness = float(parsed.get("faithfulness", 0.0))
            completeness = float(parsed.get("completeness", 0.0))
            explanation = parsed.get("explanation", "")

            avg = (relevance + faithfulness + completeness) / 3.0
            low_confidence = avg < self.LOW_CONFIDENCE_THRESHOLD

            result = GradeResult(
                relevance=relevance,
                faithfulness=faithfulness,
                completeness=completeness,
                explanation=explanation,
                low_confidence=low_confidence,
            )
            logger.info(
                "Grade: rel=%.2f faith=%.2f comp=%.2f low_conf=%s",
                relevance, faithfulness, completeness, low_confidence,
            )
            return result

        except Exception as e:
            logger.warning("Grading failed, returning default: %s", e)
            return GradeResult(
                relevance=0.0,
                faithfulness=0.0,
                completeness=0.0,
                explanation=f"Grading error: {e}",
                low_confidence=True,
            )
