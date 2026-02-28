import os
from openai import AsyncOpenAI

from .base import LLMProvider

PRIMARY_MODEL = "gpt-4o"
FALLBACK_MODEL = "gpt-4o-mini"


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        self.client = AsyncOpenAI(api_key=self.api_key)

    async def _call_model(self, model_name: str, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        max_tokens = 4096 if "gpt-4o" == model_name else 2048

        response = await self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.4,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content
        if content:
            return content
        return ""

    async def generate(self, prompt: str, system: str = "") -> str:
        try:
            result = await self._call_model(PRIMARY_MODEL, prompt, system)
            if result and result.strip():
                return result
            raise RuntimeError("Empty response from primary model")
        except Exception as e:
            # Fallback to mini
            try:
                return await self._call_model(FALLBACK_MODEL, prompt, system)
            except Exception as fallback_e:
                raise RuntimeError(
                    f"Both primary and fallback OpenAI models failed. Primary Error: {e}"
                )
