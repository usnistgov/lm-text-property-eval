# LM Text Property Evaluator

A calibrated LM-as-judge framework for scoring arbitrary text properties. Instead of asking a language model to score text with no frame of reference, this tool first **calibrates** a scoring rubric from sample texts, then **evaluates** every text chunk against that anchored rubric. This produces scores that are meaningful, consistent, and auditable.

## How It Works

The evaluation pipeline has two phases:

### 1. Calibrate

The LLM examines a random sample of your text chunks and generates a detailed scoring rubric with concrete descriptions for five score levels (0.0, 0.25, 0.5, 0.75, 1.0). This rubric is grounded in the actual content, so score levels reflect real variation in your data rather than abstract definitions.

### 2. Evaluate

Each text chunk is scored against the calibrated rubric. The LLM receives the rubric as a system prompt and returns a structured score via constrained decoding (Pydantic `response_format`), guaranteeing a valid float every time. Evaluation runs asynchronously with up to 10 concurrent API calls.

## Setup

### Install uv

[https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)

### Create and activate virtual environment

```shell
uv venv --python=3.12
source .venv/bin/activate
```

### Install dependencies

```shell
uv pip install openai pydantic python-dotenv
```

For PDF ingestion (optional):

```shell
uv pip install docling
```

### Environment variables

Create a `.env` file (or export directly) with your API key:

```
OPENAI_API_KEY=sk-...
```

Set the target OpenAI-compatible endpoints (**This must be set**).:


If you are pointing to OpenAI models:
```
OPENAI_BASE_URL=https://api.openai.com/v1
```

If you are self-hosting, you need to specify the chat completions endpoint.

```
OPENAI_BASE_URL=https://your-server.example.com/v1
```

## Project Structure

```
.
├── model_interface.py       # Async OpenAI-compatible LLM client
├── prompts.py               # Prompt templates for calibration and evaluation
├── property_evaluator.py    # Core PropertyEvaluator class (calibrate + evaluate)
├── cli.py                   # Command-line interface
├── data_pdf_chunking.py     # PDF/Markdown to chunked JSON converter
├── example.py               # End-to-end example script
├── subset_for_example.py    # Helper to create a small sample dataset
└── data/
    └── Biology2e-WEB.json   # Example dataset (OpenStax Biology 2e)
```

## Data Format

Input data is a JSON array of objects with `id` and `context` fields:

```json
[
  {"id": 123456, "context": "The text content to evaluate..."},
  {"id": 789012, "context": "Another text chunk..."}
]
```

### Preparing data from documents

Use `data_pdf_chunking.py` to convert PDFs or Markdown files into the required format. It splits documents on markdown headings and merges small sections until each chunk is at least 2000 characters.

```shell
# Convert all PDFs and Markdown files in ./data
python data_pdf_chunking.py

# Or use programmatically
from data_pdf_chunking import convert_file
convert_file("document.pdf", "output.json")
convert_file("document.md", "output.json")
```

## Usage

### CLI

The CLI has two subcommands: `calibrate` and `evaluate`.

#### Calibrate a rubric

```shell
python cli.py --model gpt-4o calibrate \
  --property "technical complexity" \
  --data data/Biology2e-WEB.json \
  --output rubric.json \
  --num-samples 5 \
  --seed 42
```

**Arguments:**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--property` | Yes | | Text property to evaluate (free-form description) |
| `--data` | Yes | | Path to input data JSON |
| `--output` | Yes | | Path to save the generated rubric |
| `--num-samples` | No | 5 | Number of sample texts for calibration |
| `--seed` | No | None | Random seed for reproducible sample selection |

#### Evaluate texts

```shell
python cli.py --model gpt-4o evaluate \
  --rubric rubric.json \
  --data data/Biology2e-WEB.json \
  --output results.json
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `--rubric` | Yes | Path to a calibrated rubric JSON |
| `--data` | Yes | Path to input data JSON |
| `--output` | Yes | Path to save results JSON |

#### Global arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--model` | Yes | | Model name (e.g., `gpt-4o`, `gpt-oss-120b`) |
| `--base-url` | No | None | OpenAI-compatible API base URL |
| `--api-key` | No | None | API key (falls back to env vars) |
| `--temperature` | No | 0.7 | Sampling temperature |
| `--max-tokens` | No | 4096 | Max tokens per generation |

### Python API

```python
import asyncio
from model_interface import LMClient
from property_evaluator import PropertyEvaluator

async def main():
    client = LMClient(
        model="gpt-4o",
        base_url="https://your-server.example.com/v1",
        api_key="your-key",
        temperature=0.7,
    )
    evaluator = PropertyEvaluator(client)

    # Step 1: Calibrate
    rubric = await evaluator.calibrate(
        property_description="technical complexity",
        data_path="data/input.json",
        output_path="rubric.json",
        num_samples=5,
        seed=42,
    )

    # Step 2: Evaluate
    results = await evaluator.evaluate(
        rubric_path="rubric.json",
        data_path="data/input.json",
        output_path="results.json",
    )

asyncio.run(main())
```

## Output Formats

### Rubric (`rubric.json`)

```json
{
  "property": "technical complexity",
  "rubric_description": "Measures the degree of specialized...",
  "score_levels": {
    "0.0": "Text contains no technical content...",
    "0.25": "Text includes basic terminology...",
    "0.5": "Text presents moderate technical detail...",
    "0.75": "Text contains substantial technical depth...",
    "1.0": "Text is highly specialized with advanced..."
  },
  "calibration_metadata": {
    "model": "gpt-4o",
    "data_file": "data/input.json",
    "num_samples": 5,
    "sample_ids": [123, 456, 789, ...],
    "timestamp": "2025-01-15T12:00:00+00:00"
  }
}
```

The `calibration_metadata` records provenance: which model created the rubric, what data it was calibrated on, and which specific samples were used.

### Results (`results.json`)

```json
[
  {"id": 123456, "score": 0.75},
  {"id": 789012, "score": 0.5}
]
```

Scores are floats clamped to [0.0, 1.0].

## Architecture Notes

- **Structured output**: Uses OpenAI's `response_format` with Pydantic models for both calibration (`Rubric`) and evaluation (`EvalScore`). The API constrains decoding to guarantee valid output matching the schema, eliminating parsing failures.
- **Async concurrency**: All LLM calls use `AsyncOpenAI`. Evaluation runs up to 10 concurrent requests (configurable via `max_concurrency`) using `asyncio.Semaphore`, so large datasets don't overwhelm the API provider.
- **OpenAI-compatible**: Works with any OpenAI-compatible API (OpenAI, vLLM, etc.) via `--base-url`.

## Example: Biology 2e

The included dataset is from the OpenStax Biology 2e textbook, chunked into ~1200 sections.

Citation: Mary Ann Clark, Matthew Douglas, and Jung Choi. *Biology 2e*. OpenStax, 2018.

```shell
# Create a small sample for testing
python subset_for_example.py

# Run the full pipeline
python example.py
```
