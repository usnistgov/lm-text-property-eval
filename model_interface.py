import os
from typing import Type

from openai import AsyncOpenAI
from pydantic import BaseModel


class LMClient:
    def __init__(self, model, base_url=None, api_key=None, temperature=0.0, max_tokens=4096):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )

    async def generate(self, system_prompt, user_prompt, response_format: Type[BaseModel] = None):
        kwargs = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        if response_format is not None:
            response = await self.client.beta.chat.completions.parse(
                **kwargs,
                response_format=response_format,
            )
            return response.choices[0].message.parsed
        else:
            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
