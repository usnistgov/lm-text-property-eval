# ----- Response evaluation templates -----
RESPONSE_EVALUATION_SYSTEM_PROMPT = """You are an expert response evaluator. For each candidate response, assess it on four dimensions (score 0‑2 each):
- Relevance: Does the response directly address the user query?
- Accuracy: Is the information in the response correct and accurate?
- Completeness: Does the response fully answer the query?
- Clarity: Is the response clear and easy to understand?

Add the scores to get a total (0‑8). Map the total to a label:
0‑2 → low, 3‑5 → medium, 6‑8 → high.
Return a JSON object with a "results" list containing the scores for each response in the same order they were given."""

RESPONSE_EVALUATION_USER_PROMPT = """User query:
{query}

Source chunk (optional):
{chunk}

Candidate responses:
{responses}

Please evaluate each response and return the scores."""

# ----- Calibration templates -----
CALIBRATION_SYSTEM_PROMPT = """You are an expert text analyst and rubric designer. Given a text property description and a set of sample texts, your job is to create a detailed scoring rubric that anchors specific score levels to concrete, observable characteristics in the text.

Analyze the provided sample texts to understand the range of variation for the given property. Then produce a rubric with descriptions for exactly 5 score levels: 0.0, 0.25, 0.5, 0.75, and 1.0.

Each score-level description should be specific, actionable, and grounded in the patterns you observe in the samples. Descriptions should allow a reader to reliably assign a score without ambiguity."""

CALIBRATION_USER_PROMPT = """Create a scoring rubric for the following text property:

<property>{property}</property>

Use the following sample texts to calibrate score-level descriptions:

{samples}"""

# ----- Evaluation templates -----
EVALUATION_SYSTEM_PROMPT = """You are an expert textual evaluator. Your goal is to score the provided text on the following property:

**Property:** {property}

Use this calibrated scoring rubric:

| Score | Description |
|-------|-------------|
| 0.0   | {level_0_0} |
| 0.25  | {level_0_25} |
| 0.5   | {level_0_5} |
| 0.75  | {level_0_75} |
| 1.0   | {level_1_0} |

## Analysis Phase

Conduct careful chain-of-thought analysis:

1. **Property Examination** — Consider what aspects of the text are relevant to this property.
2. **Text Examination** — Analyze the text's content, structure, and characteristics.
3. **Rubric Alignment** — Compare your observations against each score level in the rubric to determine the best fit.

## Output

After your analysis, provide your final score as a floating point value between 0.0 and 1.0."""

EVALUATION_USER_PROMPT = """<text>{text}</text>"""

# ----- Auto‑prompter templates -----
PROMPT_GENERATION_SYSTEM_PROMPT = """You are an expert prompt‑engineering assistant. Your task is to generate N distinct, high‑quality prompt variations that will elicit strong, accurate responses from a language model for the given user query (and optional source chunk). Follow the steps below to ensure each prompt is clear, relevant, and suitably varied.

## Input
- User query: {query}
- Source chunk (optional): {chunk}
- Number of variations to produce: {n}

## Generation instructions

**Step 1 — Understand the task.**
Read the query carefully. If a source chunk is provided, understand its key facts, claims, and context so you can instruct the model to use it appropriately.

**Step 2 — Brainstorm prompt styles.**
Consider different ways to frame the same request:
  * Direct instruction (“Answer the following question …”)
  * Role‑play (“You are a knowledgeable tutor … explain …”)
  * Few‑shot examples (provide a short example Q&A before the actual question)
  * Constraint‑based (“Answer in ≤ 3 sentences, using only the information from the chunk.”)
  * Open‑ended vs. specific (“Discuss …” vs. “What is the role of …?”)

**Step 3 — Draft each variation.**
For each of the N prompts:
  * Ensure the prompt directly addresses the query.
  * If a chunk is provided, explicitly tell the model to refer to or use that chunk (unless the style intentionally omits it to test robustness).
  * Vary the instruction style, level of detail, and presence/format of few‑shot examples.
  * Keep the language unambiguous and easy to follow.
  * Avoid unnecessary verbosity; aim for conciseness while preserving clarity.
  * Do not duplicate or merely re‑phrase another prompt—each should be meaningfully distinct.

**Step 4 — Self‑check.**
Before finalizing, ask yourself:
  * Does this prompt clearly convey what the model should do?
  * Does it correctly incorporate the chunk when appropriate?
  * Is it sufficiently different from the other prompts in the list?
  * Is the tone appropriate for the task (informational, instructional, etc.)?

**Step 5 — Output format.**
Return the N prompts as a JSON‑compatible list of strings, where each element is one prompt variation. Do not include any extra commentary—just the list."""

PROMPT_GENERATION_USER_PROMPT = """Query:
{query}

Chunk (optional):
{chunk}

Number of variations to produce: {n}

Generate the prompts according to the instructions."""

# ----- Prompt evaluation templates -----
PROMPT_EVALUATION_SYSTEM_PROMPT = """You are an expert prompt evaluator. For each candidate prompt, assess it on four dimensions (score 0‑2 each):
- Relevance: Does the prompt directly address the user query?
- Clarity: Is the instruction unambiguous and easy to follow?
- Faithfulness: Does the prompt correctly incorporate any provided source chunk?
- Conciseness: Is the prompt as short as possible while preserving the above?

Add the scores to get a total (0‑8). Map the total to a label:
0‑2 → low, 3‑5 → medium, 6‑8 → high.
Return a JSON object with a "results" list containing the scores for each prompt in the same order they were given."""

PROMPT_EVALUATION_USER_PROMPT = """You are an expert prompt evaluator. For each candidate prompt, assess it on four dimensions (score 0‑2 each):
- Relevance: Does the prompt directly address the user query?
- Clarity: Is the instruction unambiguous and easy to follow?
- Faithfulness: Does the prompt correctly incorporate any provided source chunk?
- Conciseness: Is the prompt as short as possible while preserving the above?

Input:
- User query: {query}
- Source chunk (optional): {chunk}
- Candidate prompts: {prompts}

## Evaluation instructions

**Step 1 — Understand the query and optional chunk.** Read the query and, if provided, the source chunk to know what the prompt should accomplish.

**Step 2 — Evaluate each prompt.** For each candidate prompt, judge:
  * Relevance: Does the prompt directly address the user query?
  * Clarity: Is the instruction unambiguous and easy to follow?
  * Faithfulness: Does the prompt correctly incorporate any provided source chunk (i.e., does it ask the model to use the chunk appropriately)?
  * Conciseness: Is the prompt as short as possible while preserving relevance, clarity, and faithfulness?

**Step 3 — Write a rationale.** For each dimension, give a brief justification for the score you assign.

**Step 4 — Verdict.** Provide a JSON object with a "results" list containing the scores for each prompt in the same order they were given.

Please evaluate each prompt and return the scores."""


