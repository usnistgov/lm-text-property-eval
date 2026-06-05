# PromptForge Studio

A calibrated LM-as-judge framework for scoring arbitrary text properties and optimizing prompts. The tool first calibrates a scoring rubric from sample texts for reliable evaluation, then evaluates text chunks against that rubric. Additionally, it provides automated prompt generation and scoring (autoprompt) to discover high-performing prompt variations for any query, optionally using source chunks for context.

## How It Works

PromptForge Studio offers three main capabilities:

### 1. Calibrate
The LLM examines a random sample of your text chunks and generates a detailed scoring rubric with concrete descriptions for five score levels (0.0, 0.25, 0.5, 0.75, 1.0). This rubric is grounded in the actual content, so score levels reflect real variation in your data rather than abstract definitions.

### 2. Evaluate
Each text chunk is scored against the calibrated rubric. The LLM receives the rubric as a system prompt and returns a structured score via constrained decoding (Pydantic `response_format`), guaranteeing a valid float every time. Evaluation runs asynchronously with up to 10 concurrent API calls.

### 3. Autoprompt (Prompt Optimization)
Given a query and optional source chunks, the tool automatically generates multiple prompt variations, scores them (either by prompt quality or by the quality of responses they elicit), and returns the best-performing prompt. This enables discovering high-performing prompts without manual trial-and-error.

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
LM_MODEL_API_KEY=sk-...
```

Set the target OpenAI-compatible endpoints (**This must be set**).:


If you are pointing to OpenAI models:
```
LM_MODEL_BASE_URL=https://api.openai.com/v1
```

If you are self-hosting, you need to specify the chat completions endpoint.

```
LM_MODEL_BASE_URL=https://your-server.example.com/v1
```

LM_MODEL=openai/gpt-oss-120b

## Project Structure

```
.
├── model_interface.py       # Async OpenAI-compatible LLM client
├── prompts.py               # Prompt templates for calibration, evaluation, and auto-prompting
├── property_evaluator.py    # Core PropertyEvaluator class (calibrate + evaluate)
├── cli.py                   # Command-line interface
├── auto_prompt.py           # Automatic prompt generation and scoring
├── prompt_generator.py      # Prompt generation utilities
├── prompt_evaluator.py      # Prompt and response evaluation utilities
├── data_pdf_chunking.py     # PDF/Markdown to chunked JSON converter
└── data/
    ├── Biology2e-WEB.json   # Example dataset (OpenStax Biology 2e)
    └── chunks/              # Example chunk files (chunk1.txt, chunk2.txt)
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

The CLI has three subcommands: `calibrate`, `evaluate`, and `autoprompt`.

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

#### Autoprompt: Generate and score prompt variations

The autoprompt feature automatically generates multiple prompt variations for a given query, scores them (based on prompt quality or response quality), and returns the best-performing prompt. It can optionally use source chunks to inform prompt generation and evaluation.

```shell
python cli.py --model gpt-4o autoprompt \
  --query "Your question or instruction" \
  --evaluate-responses \
  --temperature 0.9 \
  --num-variants 8 \
  --chunk-files data/chunks/chunk1.txt \
  --chunk-files data/chunks/chunk2.txt \
  --output autoprompt_result.json \
  --save-prompts all_prompts_$(Get-Date -Format "yyyyMMdd_HHmmss").json
```

**Output:** The result JSON includes the selected prompt, its score, and (if requested) all generated prompts, responses, and scores.

**Arguments:**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--query` | Yes | | User query or instruction for which to generate prompts. |
| `--chunk` | No | | Optional source chunk to consider when generating prompts. |
| `--chunk-file` | No | None | Path to a file containing the chunk; overrides `--chunk` if provided. |
| `--chunk-files` | No | [] | Path to a source-chunk file. Can be given multiple times to supply N chunks. |
| `--chunk-dir` | No | None | If set, all `*.txt` (or `*.json`) files under this directory are read as chunks. |
| `--num-variants` | No | 5 | How many prompt variants to generate. |
| `--evaluate-responses` | No | | Evaluate prompts based on response quality instead of prompt quality. |
| `--output` | No | None | If set, write the result JSON to this file. |
| `--save-prompts-path` | No | None | If set, write all generated prompt variants to this file (JSON array of strings). |
| `--mock` | No | | Use a mock LLM client (no external calls). |

**Note:** The `--evaluate-responses` flag changes the evaluation metric from prompt quality (relevance, clarity, faithfulness, conciseness) to response quality (relevance, accuracy, completeness, clarity) by generating responses from each prompt and scoring them.

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
We also provide two example chunk files in `data/chunks/` for demonstration.

Citation: Mary Ann Clark, Matthew Douglas, and Jung Choi. *Biology 2e*. OpenStax, 2018.

### Using the autoprompt feature (PowerShell example)

```powershell
python cli.py autoprompt `
  --model gpt-oss-120b `
  --query "What is the role of actin filaments in cytokinesis?" `
  --evaluate-responses `
  --temperature 0.9 `
  --num-variants 8 `
  --chunk-files data\chunks\chunk1.txt `
  --chunk-files data\chunks\chunk2.txt `
  --output autoprompt_result.json `
  --save-prompts ("prompts_{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
```

**Note for Unix shells (bash, zsh):** Use `\` for line continuation and `$(date +%Y%m%d_%H%M%S)` for the timestamp, e.g.:

```bash
python cli.py autoprompt \
  --model gpt-oss-120b \
  --query "What is the role of actin filaments in cytokinesis?" \
  --evaluate-responses \
  --temperature 0.9 \
  --num-variants 8 \
  --chunk-files data/chunks/chunk1.txt \
  --chunk-files data/chunks/chunk2.txt \
  --output autoprompt_result.json \
  --save-prompts "prompts_$(date +%Y%m%d_%H%M%S).json"
```
