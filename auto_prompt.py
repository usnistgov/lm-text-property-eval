"""Auto‑prompter: generate prompt variants, score them, and pick the best."""

from __future__ import annotations

from typing import List, Tuple

from prompt_generator import generate_prompts
from prompt_evaluator import evaluate_prompts, PromptScore, EvaluationResult
from model_interface import LMClient
from prompts import (
    RESPONSE_EVALUATION_SYSTEM_PROMPT,
    RESPONSE_EVALUATION_USER_PROMPT,
)
from pydantic import BaseModel, Field


class ResponseScore(BaseModel):
    """Score for a single response across four dimensions."""
    relevance: int = Field(..., ge=0, le=2, description="How well the response addresses the query (0‑2).")
    accuracy: int = Field(..., ge=0, le=2, description="Is the information correct and accurate? (0‑2).")
    completeness: int = Field(..., ge=0, le=2, description="Does the response fully answer the query? (0‑2).")
    clarity: int = Field(..., ge=0, le=2, description="Is the response clear and easy to understand? (0‑2).")

    @property
    def total(self) -> int:
        return self.relevance + self.accuracy + self.completeness + self.clarity

    @property
    def label(self) -> str:
        """Map total score to categorical label."""
        if self.total >= 6:
            return "high"
        if self.total >= 3:
            return "medium"
        return "low"


class ResponseEvaluationResult(BaseModel):
    """Output of the response evaluator."""
    results: List[ResponseScore] = Field(
        description="Evaluation scores for each candidate response, in the same order as input."
    )


async def run_auto_prompt(
    query: str,
    chunks: List[str],
    num_variants: int = 5,
    client: LMClient | None = None,
) -> Tuple[str, PromptScore, List[str]]:
    """
    Generate prompt variations, evaluate them, and return the highest‑scoring prompt
    together with the full list of candidates.

    Returns
    -------
    (best_prompt, best_score, all_prompts) where best_score is a PromptScore instance
    and all_prompts is the list of N generated prompt strings.
    """
    if client is None:
        client = LMClient()  # relies on LM_* / OPENAI_* env vars

    # 1. Generate candidates
    # For prompt generation we can use the first chunk if available, otherwise empty string.
    # The generator currently expects a single chunk; we join all chunks with a separator
    # to give it a broader context.
    chunk_for_gen = "\n\n---\n\n".join(chunks) if chunks else ""
    candidates = await generate_prompts(
        query=query,
        chunk=chunk_for_gen,
        num_variants=num_variants,
        client=client,
    )

    # 2. Score each candidate using the multi‑chunk evaluator
    scores = await evaluate_prompts(
        prompts=candidates,
        query=query,
        chunks=chunks,
        client=client,
    )

    # 3. Pick the prompt with the highest total score (break ties by first)
    best_idx = max(range(len(scores)), key=lambda i: scores[i].total)
    best_prompt = candidates[best_idx]
    best_score = scores[best_idx]

    return best_prompt, best_score, candidates


async def _generate_responses(
    prompts: List[str],
    chunk: str = "",
    client: LMClient | None = None,
) -> List[str]:
    """
    Generate responses for each prompt by executing it against the LLM.

    Parameters
    ----------
    prompts: List of prompt strings to execute.
    chunk: Optional source chunk to consider when generating responses.
    client: LMClient instance; if None, a new client is created.

    Returns
    -------
    List of response strings, aligned with the input prompts.
    """
    if client is None:
        client = LMClient()

    responses = []
    for prompt in prompts:
        # For response generation, we use the prompt as the user input
        # with a minimal system prompt (or empty) to treat it as a direct instruction
        system_prompt = ""  # Let the prompt speak for itself
        user_prompt = prompt

        # Add chunk context if provided (as part of the system prompt for clarity)
        if chunk:
            system_prompt = f"Use the following source chunk to inform your response:\n\n{chunk}\n\n"

        try:
            response = await client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format=None,  # Get raw text response
            )
            responses.append(response)
        except Exception as e:
            # If response generation fails, return an error message
            responses.append(f"[Error generating response: {str(e)}]")

    return responses


async def _evaluate_responses(
    responses: List[str],
    query: str,
    chunks: List[str],
    client: LMClient | None = None,
) -> List[ResponseScore]:
    """
    Evaluate a list of response strings using the LLM against multiple source chunks.
    The final score for each response is the average of the scores obtained
    for each individual chunk.

    Parameters
    ----------
    responses: List of candidate response strings.
    query: Original user query (for relevance check).
    chunks: List of source‑chunk strings (each chunk is used to compute the
            completeness dimension; the final score is averaged across chunks).
    client: LMClient instance; if None, a new client is created.

    Returns
    -------
    List of ResponseScore objects (averaged across chunks), aligned with the input responses.
    """
    if client is None:
        client = LMClient()

    # We'll accumulate scores per response across all chunks
    accumulated = [
        ResponseScore(relevance=0, accuracy=0, completeness=0, clarity=0)
        for _ in responses
    ]

    for chunk in chunks:
        # Build an enumerated list for the user prompt (same for every chunk)
        enumerated = "\n".join(f"{i+1}. {r}" for i, r in enumerate(responses))
        user_prompt = RESPONSE_EVALUATION_USER_PROMPT.format(
            query=query, chunk=chunk, responses=enumerated
        )

        parsed: ResponseEvaluationResult = await client.generate(
            RESPONSE_EVALUATION_SYSTEM_PROMPT,
            user_prompt,
            response_format=ResponseEvaluationResult,
        )
        # Guard against malformed LLM output
        if len(parsed.results) != len(responses):
            chunk_scores = [
                ResponseScore(relevance=0, accuracy=0, completeness=0, clarity=0)
                for _ in responses
            ]
        else:
            chunk_scores = parsed.results

        # Element‑wise add the scores from this chunk
        for i, sc in enumerate(chunk_scores):
            accumulated[i].relevance   += sc.relevance
            accumulated[i].accuracy    += sc.accuracy
            accumulated[i].completeness+= sc.completeness
            accumulated[i].clarity     += sc.clarity

    # Average across the number of chunks
    n_chunks = max(len(chunks), 1)
    averaged = [
        ResponseScore(
            relevance   = round(acc.relevance   / n_chunks),
            accuracy    = round(acc.accuracy    / n_chunks),
            completeness= round(acc.completeness/ n_chunks),
            clarity     = round(acc.clarity     / n_chunks),
        )
        for acc in accumulated
    ]
    return averaged


async def run_auto_prompt_with_response_evaluation(
    query: str,
    chunks: List[str],
    num_variants: int = 5,
    client: LMClient | None = None,
) -> Tuple[str, str, ResponseScore, List[str]]:
    """
    Generate prompt variations, execute them to get responses, evaluate responses,
    and return the prompt with the highest-scoring response together with the
    full list of candidates.

    Returns
    -------
    (best_prompt, best_response, best_score, all_prompts) where best_score is a
    ResponseScore instance and all_prompts is the list of N generated prompt strings.
    """
    if client is None:
        client = LMClient()  # relies on LM_* / OPENAI_* env vars

    # 1. Generate candidates
    # For prompt generation we join all chunks with a separator to give broader context.
    chunk_for_gen = "\n\n---\n\n".join(chunks) if chunks else ""
    candidates = await generate_prompts(
        query=query,
        chunk=chunk_for_gen,
        num_variants=num_variants,
        client=client,
    )

    # 2. Generate responses for each candidate
    # For response generation we also give the concatenated chunks as context.
    responses = await _generate_responses(
        prompts=candidates,
        chunk=chunk_for_gen,
        client=client,
    )

    # 3. Score each response using the multi‑chunk evaluator
    scores = await _evaluate_responses(
        responses=responses,
        query=query,
        chunks=chunks,
        client=client,
    )

    # 4. Pick the prompt with the highest-scoring response (break ties by first)
    best_idx = max(range(len(scores)), key=lambda i: scores[i].total)
    best_prompt = candidates[best_idx]
    best_response = responses[best_idx]
    best_score = scores[best_idx]

    return best_prompt, best_response, best_score, candidates


async def run_auto_prompt_batch(
    queries: List[str],
    chunk: str = "",
    num_variants: int = 5,
    client: LMClient | None = None,
) -> List[Tuple[str, PromptScore]]:
    """Convenience for multiple queries."""
    return [
        await run_auto_prompt(q, chunk, num_variants, client) for q in queries
    ]


if __name__ == "__main__":
    # Simple CLI test
    import argparse
    import asyncio
    import json

    parser = argparse.ArgumentParser(
        description="Auto‑prompter: generate and score prompt variations."
    )
    parser.add_argument("--query", required=True, help="User query or instruction.")
    parser.add_argument(
        "--chunk",
        default="",
        help="Optional source chunk to consider when generating prompts.",
    )
    parser.add_argument(
        "--num-variants",
        type=int,
        default=5,
        help="How many prompt variants to generate.",
    )
    parser.add_argument(
        "--evaluate-responses",
        action="store_true",
        help="Evaluate prompts based on response quality instead of prompt quality",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="If set, write the result JSON to this file.",
    )
    args = parser.parse_args()

    async def main():
        client = LMClient()
        if args.evaluate_responses:
            # Test response-based evaluation
            prompt, response, score, _ = await run_auto_prompt_with_response_evaluation(
                query=args.query,
                chunk=args.chunk,
                num_variants=args.num_variants,
                client=client,
            )
            result = {
                "query": args.query,
                "chunk": args.chunk,
                "selected_prompt": prompt,
                "selected_response": response,
                "scores": {
                    "relevance": score.relevance,
                    "accuracy": score.accuracy,
                    "completeness": score.completeness,
                    "clarity": score.clarity,
                    "total": score.total,
                    "label": score.label,
                },
            }
        else:
            # Test prompt-based evaluation (original behavior)
            prompt, score, _ = await run_auto_prompt(
                query=args.query,
                chunk=args.chunk,
                num_variants=args.num_variants,
                client=client,
            )
            result = {
                "query": args.query,
                "chunk": args.chunk,
                "selected_prompt": prompt,
                "scores": {
                    "relevance": score.relevance,
                    "clarity": score.clarity,
                    "faithfulness": score.faithfulness,
                    "conciseness": score.conciseness,
                    "total": score.total,
                    "label": score.label,
                },
            }
        print(json.dumps(result, indent=2))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)

    asyncio.run(main())