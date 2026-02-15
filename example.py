"""Example script demonstrating calibration and evaluation via Python API."""

import asyncio
import os

from dotenv import load_dotenv

from model_interface import LMClient
from property_evaluator import PropertyEvaluator

# Load environment variables from .env file
load_dotenv()

MODEL = "gpt-oss-120b"
API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL")
DATA = "data/Biology2e-WEB-sample.json"
RUBRIC = "rubric.json"
RESULTS = "results.json"
PROPERTY = "midocondria involvement"
SEED = 42
NUM_SAMPLES = 10


async def main():
    client = LMClient(model=MODEL, base_url=BASE_URL, api_key=API_KEY, temperature=0.7)
    evaluator = PropertyEvaluator(client)

    # Step 1: Calibrate — generate a scoring rubric from sample texts
    print("=" * 60)
    print("Step 1: Calibrating rubric")
    print("=" * 60)
    rubric = await evaluator.calibrate(
        property_description=PROPERTY,
        data_path=DATA,
        output_path=RUBRIC,
        num_samples=NUM_SAMPLES,
        seed=SEED,
    )
    print(f"Rubric saved to {RUBRIC}")
    print(f"Property: {rubric['property']}")
    print(f"Score levels defined: {list(rubric['score_levels'].keys())}")

    # Step 2: Evaluate — score each text chunk using the calibrated rubric
    print()
    print("=" * 60)
    print("Step 2: Evaluating texts")
    print("=" * 60)
    results = await evaluator.evaluate(
        rubric_path=RUBRIC,
        data_path=DATA,
        output_path=RESULTS,
    )
    scored = [r for r in results if r["score"] is not None]
    failed = [r for r in results if r["score"] is None]
    avg = sum(r["score"] for r in scored) / len(scored) if scored else 0.0
    print(f"\nResults saved to {RESULTS}")
    print(f"Scored: {len(scored)}, Failed: {len(failed)}, Average score: {avg:.4f}")


asyncio.run(main())
