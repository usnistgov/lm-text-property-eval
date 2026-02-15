import argparse
import asyncio

from model_interface import LMClient
from property_evaluator import PropertyEvaluator


async def main():
    parser = argparse.ArgumentParser(description="Calibrated LM-Judge Text Property Evaluator")
    parser.add_argument("--model", required=True, help="Model name (e.g. gpt-4o)")
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible API base URL")
    parser.add_argument("--api-key", default=None, help="API key")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=4096, help="Max tokens for generation")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # calibrate subcommand
    cal = subparsers.add_parser("calibrate", help="Generate a scoring rubric from sample texts")
    cal.add_argument("--property", required=True, help="Text property to evaluate")
    cal.add_argument("--data", required=True, help="Path to input data JSON")
    cal.add_argument("--output", required=True, help="Path to save rubric JSON")
    cal.add_argument("--num-samples", type=int, default=5, help="Number of samples for calibration")
    cal.add_argument("--seed", type=int, default=None, help="Random seed for sample selection")

    # evaluate subcommand
    evl = subparsers.add_parser("evaluate", help="Score texts using a calibrated rubric")
    evl.add_argument("--rubric", required=True, help="Path to rubric JSON")
    evl.add_argument("--data", required=True, help="Path to input data JSON")
    evl.add_argument("--output", required=True, help="Path to save results JSON")

    args = parser.parse_args()

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


if __name__ == "__main__":
    asyncio.run(main())
