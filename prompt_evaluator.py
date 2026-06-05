"""Prompt evaluation utilities for the auto‑prompter."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from model_interface import LMClient
from prompts import (
    PROMPT_EVALUATION_SYSTEM_PROMPT,
    PROMPT_EVALUATION_USER_PROMPT,
)


class PromptScore(BaseModel):
    """Score for a single prompt across four dimensions."""
    relevance: int = Field(..., ge=0, le=2, description="How well the prompt addresses the query (0‑2).")
    clarity: int = Field(..., ge=0, le=2, description="Is the instruction unambiguous? (0‑2).")
    faithfulness: int = Field(..., ge=0, le=2, description="Does the prompt correctly use the provided chunk? (0‑2).")
    conciseness: int = Field(..., ge=0, le=2, description="Is the prompt as concise as possible? (0‑2).")

    @property
    def total(self) -> int:
        return self.relevance + self.clarity + self.faithfulness + self.conciseness

    @property
    def label(self) -> str:
        """Map total score to categorical label."""
        if self.total >= 6:
            return "high"
        if self.total >= 3:
            return "medium"
        return "low"


class EvaluationResult(BaseModel):
    """Output of the prompt evaluator."""
    results: List[PromptScore] = Field(
        description="Evaluation scores for each candidate prompt, in the same order as input."
    )




async def evaluate_prompts(
    prompts: List[str],
    query: str,
    chunks: List[str],
    client: LMClient | None = None,
) -> List[PromptScore]:
    """
    Use an LLM to score a list of prompt variations against multiple source chunks.
    The final score for each prompt is the average of the scores obtained
    for each individual chunk.

    Parameters
    ----------
    prompts: List of candidate prompt strings.
    query: Original user query (for relevance check).
    chunks: List of source‑chunk strings (each chunk is used to compute the
            faithfulness dimension; the final score is averaged across chunks).
    client: LMClient instance; if None, a new client is created.

    Returns
    -------
    List of PromptScore objects (averaged across chunks), aligned with the input prompts.
    """
    if client is None:
        client = LMClient(model="gpt-4o")

    # We'll accumulate scores per prompt across all chunks
    # Initialize a list of zero‑filled PromptScore objects
    accumulated = [
        PromptScore(relevance=0, clarity=0, faithfulness=0, conciseness=0)
        for _ in prompts
    ]

    for chunk in chunks:
        # Build a enumerated list for the user prompt (same for every chunk)
        enumerated = "\n".join(f"{i+1}. {p}" for i, p in enumerate(prompts))
        user_prompt = PROMPT_EVALUATION_USER_PROMPT.format(query=query, chunk=chunk, prompts=enumerated)

        parsed: EvaluationResult = await client.generate(
            PROMPT_EVALUATION_SYSTEM_PROMPT,
            user_prompt,
            response_format=EvaluationResult,
        )
        # Guard against malformed LLM output
        if len(parsed.results) != len(prompts):
            chunk_scores = [
                PromptScore(relevance=0, clarity=0, faithfulness=0, conciseness=0)
                for _ in prompts
            ]
        else:
            chunk_scores = parsed.results

        # Element‑wise add the scores from this chunk
        for i, sc in enumerate(chunk_scores):
            accumulated[i].relevance   += sc.relevance
            accumulated[i].clarity     += sc.clarity
            accumulated[i].faithfulness+= sc.faithfulness
            accumulated[i].conciseness+= sc.conciseness

    # Average across the number of chunks
    n_chunks = max(len(chunks), 1)   # avoid division‑by‑zero
    averaged = [
        PromptScore(
            relevance   = round(acc.relevance   / n_chunks),
            clarity     = round(acc.clarity     / n_chunks),
            faithfulness= round(acc.faithfulness/ n_chunks),
            conciseness = round(acc.conciseness / n_chunks),
        )
        for acc in accumulated
    ]
    return averaged