import asyncio
import json
import random
from datetime import datetime, timezone

from pydantic import BaseModel

from model_interface import LMClient
from prompts import (
    CALIBRATION_SYSTEM_PROMPT,
    CALIBRATION_USER_PROMPT,
    EVALUATION_SYSTEM_PROMPT,
    EVALUATION_USER_PROMPT,
)


def load_data(path):
    with open(path) as f:
        return json.load(f)


def load_rubric(path):
    with open(path) as f:
        return json.load(f)


def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


class ScoreLevels(BaseModel):
    level_0_0: str
    level_0_25: str
    level_0_5: str
    level_0_75: str
    level_1_0: str


class Rubric(BaseModel):
    property: str
    rubric_description: str
    score_levels: ScoreLevels


class EvalScore(BaseModel):
    score: float


class PropertyEvaluator:
    def __init__(self, client):
        self.client = client

    async def calibrate(self, property_description, data_path, output_path, num_samples=5, seed=None):
        data = load_data(data_path)

        rng = random.Random(seed)
        samples = rng.sample(data, min(num_samples, len(data)))

        samples_text = "\n\n".join(
            f'<sample id="{s["id"]}">\n{s["context"]}\n</sample>'
            for s in samples
        )

        user_prompt = CALIBRATION_USER_PROMPT.format(
            property=property_description,
            samples=samples_text,
        )

        parsed = await self.client.generate(
            CALIBRATION_SYSTEM_PROMPT, user_prompt, response_format=Rubric,
        )

        rubric = {
            "property": parsed.property,
            "rubric_description": parsed.rubric_description,
            "score_levels": {
                "0.0": parsed.score_levels.level_0_0,
                "0.25": parsed.score_levels.level_0_25,
                "0.5": parsed.score_levels.level_0_5,
                "0.75": parsed.score_levels.level_0_75,
                "1.0": parsed.score_levels.level_1_0,
            },
            "calibration_metadata": {
                "model": self.client.model,
                "data_file": str(data_path),
                "num_samples": len(samples),
                "sample_ids": [s["id"] for s in samples],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        save_json(rubric, output_path)
        return rubric

    async def _evaluate_item(self, system_prompt, item, idx, n, counter):
        user_prompt = EVALUATION_USER_PROMPT.format(text=item["context"])
        parsed = await self.client.generate(
            system_prompt, user_prompt, response_format=EvalScore,
        )
        score = max(0.0, min(1.0, parsed.score))
        counter[0] += 1
        print(f"[{counter[0]}/{n}] id={item['id']} score={score}")
        return idx, {"id": item["id"], "score": score}

    async def evaluate(self, rubric_path, data_path, output_path, max_concurrency=10):
        rubric = load_rubric(rubric_path)
        data = load_data(data_path)

        levels = rubric["score_levels"]
        system_prompt = EVALUATION_SYSTEM_PROMPT.format(
            property=rubric["property"],
            level_0_0=levels["0.0"],
            level_0_25=levels["0.25"],
            level_0_5=levels["0.5"],
            level_0_75=levels["0.75"],
            level_1_0=levels["1.0"],
        )

        n = len(data)
        results = [None] * n
        counter = [0]
        semaphore = asyncio.Semaphore(max_concurrency)

        async def bounded(system_prompt, item, idx, n, counter):
            async with semaphore:
                return await self._evaluate_item(system_prompt, item, idx, n, counter)

        tasks = [
            bounded(system_prompt, item, idx, n, counter)
            for idx, item in enumerate(data)
        ]

        for idx, result in await asyncio.gather(*tasks):
            results[idx] = result

        save_json(results, output_path)
        return results
