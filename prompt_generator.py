"""Prompt generation utilities for the auto‑prompter."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from model_interface import LMClient
from prompts import (
    PROMPT_GENERATION_SYSTEM_PROMPT,
    PROMPT_GENERATION_USER_PROMPT,
)


class PromptList(BaseModel):
    """Structured output for the prompt generator."""
    prompts: List[str] = Field(
        description="List of distinct prompt variations for the given query and chunk."
    )


async def generate_prompts(
    query: str,
    chunk: str,
    num_variants: int = 5,
    client: LMClient | None = None,
) -> List[str]:
    """
    Use an LLM to generate diverse prompt variations.

    Parameters
    ----------
    query: The original user question or instruction.
    chunk: Optional source text that should be considered when crafting prompts.
    num_variants: How many different prompts to generate.
    client: An LMClient instance; if None, a new client is created using environment
            variables (LM_* or OPENAI_*).

    Returns
    -------
    List of prompt strings.
    """
    if client is None:
        client = LMClient(model="gpt-4o")  # default; will be overridden by env vars

    system_prompt = PROMPT_GENERATION_SYSTEM_PROMPT
    user_prompt = PROMPT_GENERATION_USER_PROMPT.format(
        query=query, chunk=chunk, n=num_variants
    )

    parsed: PromptList = await client.generate(
        system_prompt, user_prompt, response_format=PromptList
    )
    return parsed.prompts