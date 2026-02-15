


CALIBRATION_SYSTEM_PROMPT = """You are an expert text analyst and rubric designer. Given a text property description and a set of sample texts, your job is to create a detailed scoring rubric that anchors specific score levels to concrete, observable characteristics in the text.

Analyze the provided sample texts to understand the range of variation for the given property. Then produce a rubric with descriptions for exactly 5 score levels: 0.0, 0.25, 0.5, 0.75, and 1.0.

Each score-level description should be specific, actionable, and grounded in the patterns you observe in the samples. Descriptions should allow a reader to reliably assign a score without ambiguity."""


CALIBRATION_USER_PROMPT = """Create a scoring rubric for the following text property:

<property>{property}</property>

Use the following sample texts to calibrate score-level descriptions:

{samples}"""


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

