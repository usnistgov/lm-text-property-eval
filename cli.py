import argparse
import os
import asyncio
import json

from model_interface import LMClient
from property_evaluator import PropertyEvaluator
import auto_prompt
from pydantic import BaseModel, Field
from typing import List, Type
from prompt_generator import PromptList
from prompt_evaluator import PromptScore, EvaluationResult
from auto_prompt import ResponseScore, ResponseEvaluationResult


# Mock LMClient for testing without external calls
class MockLMClient:
    """Mock LMClient that returns canned responses for testing."""
    def __init__(self, model: str = "mock"):
        self.model = model
        self.temperature = 0.0
        self.max_tokens = 4096

    async def generate(self, system_prompt: str, user_prompt: str, response_format: Type[BaseModel] = None):
        # Return canned responses based on the system prompt
        if "prompt‑engineering assistant" in system_prompt:
            # This is the prompt generator
            return PromptList(
                prompts=[
                    "What is the role of actin filaments in cytokinesis? Please explain in detail.",
                    "Describe how actin filaments contribute to the process of cytokinesis.",
                    "Actin filaments are crucial for cytokinesis; explain their function."
                ]
            )
        elif "expert prompt evaluator" in system_prompt:
            # This is the prompt evaluator
            # We'll return scores that make the first prompt the best (high)
            return EvaluationResult(
                results=[
                    PromptScore(relevance=2, clarity=2, faithfulness=2, conciseness=2),  # total 8 -> high
                    PromptScore(relevance=1, clarity=1, faithfulness=1, conciseness=1),   # total 4 -> medium
                    PromptScore(relevance=0, clarity=0, faithfulness=0, conciseness=0),   # total 0 -> low
                ]
            )
        elif "expert response evaluator" in system_prompt:
            # This is the response evaluator
            # We'll return scores that make the first response the best (high)
            return ResponseEvaluationResult(
                results=[
                    ResponseScore(relevance=2, accuracy=2, completeness=2, clarity=2),  # total 8 -> high
                    ResponseScore(relevance=1, accuracy=1, completeness=1, clarity=1),   # total 4 -> medium
                    ResponseScore(relevance=0, accuracy=0, completeness=0, clarity=0),   # total 0 -> low
                ]
            )
        else:
            # Fallback: return a dummy response
            if response_format is not None:
                # Try to create an instance of the response_format with default values
                # This is a simplistic fallback; for our use case we don't expect to hit this.
                return response_format()
            # For response generation when no specific system prompt matched, return a canned response
            # Check if this looks like a response generation call (has user_prompt but is not an evaluator/generator)
            is_evaluator_or_generator = (
                "prompt‑engineering assistant" in system_prompt or
                "expert prompt evaluator" in system_prompt or
                "expert response evaluator" in system_prompt or
                "You are an expert text analyst" in system_prompt or
                "You are an expert textual evaluator" in system_prompt
            )
            if user_prompt and not is_evaluator_or_generator:
                # This appears to be a response generation call
                return f"Mock response to: {user_prompt[:50]}..."
            return None


# Common arguments for all subcommands
common_parser = argparse.ArgumentParser(add_help=False)
common_parser.add_argument("--model", default=os.getenv("LM_MODEL", "gpt-4o"), help="Model name (e.g. gpt-4o, openai/gpt-oss-120b)")
common_parser.add_argument("--base-url", default=None, help="OpenAI-compatible API base URL")
common_parser.add_argument("--api-key", default=None, help="API key")
common_parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
common_parser.add_argument("--max-tokens", type=int, default=4096, help="Max tokens for generation")

async def main():
    parser = argparse.ArgumentParser(description="Calibrated LM-Judge Text Property Evaluator. Common arguments (--model, --base-url, --api-key, --temperature, --max-tokens) can be used with each subcommand.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # calibrate subcommand
    cal = subparsers.add_parser("calibrate", help="Generate a scoring rubric from sample texts", parents=[common_parser])
    cal.add_argument("--property", required=True, help="Text property to evaluate")
    cal.add_argument("--data", required=True, help="Path to input data JSON")
    cal.add_argument("--output", required=True, help="Path to save rubric JSON")
    cal.add_argument("--num-samples", type=int, default=5, help="Number of samples for calibration")
    cal.add_argument("--seed", type=int, default=None, help="Random seed for sample selection")

    # evaluate subcommand
    evl = subparsers.add_parser("evaluate", help="Score texts using a calibrated rubric", parents=[common_parser])
    evl.add_argument("--rubric", required=True, help="Path to rubric JSON")
    evl.add_argument("--data", required=True, help="Path to input data JSON")
    evl.add_argument("--output", required=True, help="Path to save results JSON")

    # autoprompt subcommand
    aut = subparsers.add_parser("autoprompt", help="Generate and score prompt variations", parents=[common_parser])
    aut.add_argument("--query", required=True, help="User query or instruction.")
    aut.add_argument(
        "--chunk",
        default="",
        help="Optional source chunk to consider when generating prompts.",
    )
    aut.add_argument(
        "--chunk-file",
        dest="chunk_file",
        default=None,
        help="Path to a file containing the chunk; overrides --chunk if provided.",
    )
    aut.add_argument(
        "--chunk-files",
        action="append",
        default=[],
        help="Path to a source-chunk file. Can be given multiple times to supply N chunks.",
    )
    aut.add_argument(
        "--chunk-dir",
        default=None,
        help="If set, all *.txt (or *.json) files under this directory are read as chunks.",
    )
    aut.add_argument(
        "--num-variants",
        type=int,
        default=5,
        help="How many prompt variants to generate.",
    )
    aut.add_argument(
        "--evaluate-responses",
        action="store_true",
        help="Evaluate prompts based on response quality instead of prompt quality",
    )
    aut.add_argument(
        "--output",
        default=None,
        help="If set, write the result JSON to this file.",
    )
    aut.add_argument(
        "--save-prompts",
        dest="save_prompts_path",
        default=None,
        help="If set, write all generated prompt variants to this file (JSON array of strings).",
    )
    aut.add_argument(
        "--mock",
        action="store_true",
        help="Use a mock LLM client (no external calls)",
    )

    args = parser.parse_args()

    # If using mock for autoprompt, use mock client; otherwise create real client
    if args.command == "autoprompt" and args.mock:
        client = MockLMClient()
        evaluator = PropertyEvaluator(client)  # Still create evaluator for consistency
    else:
        client = LMClient(
            model=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        evaluator = PropertyEvaluator(client)

    if args.command == "calibrate":
        rubric = await evaluator.calibrate(
            property_description=args.property,
            data_path=args.data,
            output_path=args.output,
            num_samples=args.num_samples,
            seed=args.seed,
        )
        print(f"Rubric saved to {args.output}")
        print(f"Property: {rubric['property']}")
        print(f"Score levels defined: {list(rubric['score_levels'].keys())}")

    elif args.command == "evaluate":
        results = await evaluator.evaluate(
            rubric_path=args.rubric,
            data_path=args.data,
            output_path=args.output,
        )
        scored = [r for r in results if r["score"] is not None]
        failed = [r for r in results if r["score"] is None]
        avg = sum(r["score"] for r in scored) / len(scored) if scored else 0.0
        print(f"\nResults saved to {args.output}")
        print(f"Scored: {len(scored)}, Failed: {len(failed)}, Average score: {avg:.4f}")


    elif args.command == "autoprompt":
        # Build list of chunk strings from all sources
        chunk_texts: List[str] = []
        if args.chunk:
            chunk_texts.append(args.chunk)
        if args.chunk_file:
            with open(args.chunk_file, "r", encoding="utf-8") as f:
                chunk_texts.append(f.read())
        if getattr(args, "chunk_files", None):
            for p in args.chunk_files:
                with open(p, "r", encoding="utf-8") as f:
                    chunk_texts.append(f.read())
        if getattr(args, "chunk_dir", None):
            from pathlib import Path
            dir_path = Path(args.chunk_dir)
            for file_path in sorted(dir_path.iterdir()):
                if file_path.is_file() and file_path.suffix in {".txt", ".json"}:
                    with open(file_path, "r", encoding="utf-8") as f:
                        chunk_texts.append(f.read())
        # Ensure at least one chunk (empty string) to avoid errors
        if not chunk_texts:
            chunk_texts = [""]

        if args.evaluate_responses:
            # Run auto‑prompter with response evaluation (multi‑chunk aware)
            best_prompt, best_response, best_score, all_prompts = await auto_prompt.run_auto_prompt_with_response_evaluation(
                query=args.query,
                chunks=chunk_texts,
                num_variants=args.num_variants,
                client=client,
            )
            # Generate responses for all prompts to include in the result
            chunk_for_gen = "\n\n---\n\n".join(chunk_texts) if chunk_texts else ""
            all_responses = await auto_prompt._generate_responses(
                prompts=all_prompts,
                chunk=chunk_for_gen,
                client=client,
            )
            # Evaluate all responses to get scores for each
            all_scores = await auto_prompt._evaluate_responses(
                responses=all_responses,
                query=args.query,
                chunks=chunk_texts,
                client=client,
            )
            result = {
                "query": args.query,
                # For backward compatibility we keep a single “chunk” field –
                # we store a short concatenation of all chunks (truncated for readability).
                "chunk": ("\n\n---\n\n".join(chunk_texts))[:500] + ("…" if len("\n\n---\n\n".join(chunk_texts)) > 500 else ""),
                "selected_prompt": best_prompt,
                "selected_response": best_response,
                "selected_prompt_score": {
                    "relevance": best_score.relevance,
                    "accuracy": best_score.accuracy,
                    "completeness": best_score.completeness,
                    "clarity": best_score.clarity,
                    "total": best_score.total,
                    "label": best_score.label,
                },
                "all_prompts": all_prompts,
                "all_responses": all_responses,
                "all_scores": [
                    {
                        "relevance": score.relevance,
                        "accuracy": score.accuracy,
                        "completeness": score.completeness,
                        "clarity": score.clarity,
                        "total": score.total,
                        "label": score.label,
                    }
                    for score in all_scores
                ],
            }
        else:
            # Run auto‑prompter with prompt evaluation (multi‑chunk aware)
            best_prompt, best_score, all_prompts = await auto_prompt.run_auto_prompt(
                query=args.query,
                chunks=chunk_texts,
                num_variants=args.num_variants,
                client=client,
            )
            # Evaluate all prompts to get scores for each
            all_scores = await auto_prompt.evaluate_prompts(
                prompts=all_prompts,
                query=args.query,
                chunks=chunk_texts,
                client=client,
            )
            result = {
                "query": args.query,
                "chunk": ("\n\n---\n\n".join(chunk_texts))[:500] + ("…" if len("\n\n---\n\n".join(chunk_texts)) > 500 else ""),
                "selected_prompt": best_prompt,
                "selected_prompt_score": {
                    "relevance": best_score.relevance,
                    "clarity": best_score.clarity,
                    "faithfulness": best_score.faithfulness,
                    "conciseness": best_score.conciseness,
                    "total": best_score.total,
                    "label": best_score.label,
                },
                "all_prompts": all_prompts,
                "all_scores": [
                    {
                        "relevance": score.relevance,
                        "clarity": score.clarity,
                        "faithfulness": score.faithfulness,
                        "conciseness": score.conciseness,
                        "total": score.total,
                        "label": score.label,
                    }
                    for score in all_scores
                ],
            }
        import json
        print(json.dumps(result, indent=2))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)

        # Optional: dump all generated prompts to a separate file
        if args.save_prompts_path:
            with open(args.save_prompts_path, "w", encoding="utf-8") as f:
                json.dump(all_prompts, f, indent=2)
            print(f"Saved {len(all_prompts)} prompt variants to {args.save_prompts_path}")

if __name__ == "__main__":
    asyncio.run(main())
