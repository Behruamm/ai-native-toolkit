import os
from anthropic import AsyncAnthropic

from .base import LLMProvider

PRIMARY_MODEL = "claude-3-5-sonnet-latest"
FALLBACK_MODEL = "claude-3-5-haiku-latest"


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = AsyncAnthropic(api_key=self.api_key)

    async def _call_model(self, model_name: str, prompt: str, system: str = "") -> str:
        max_tokens = 4096 if "sonnet" in model_name else 2048

        kwargs = {
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": 0.4,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system:
            kwargs["system"] = system

        response = await self.client.messages.create(**kwargs)

        # Anthropic returns a list of content blocks
        text_blocks = [block.text for block in response.content if block.type == "text"]
        return "".join(text_blocks)

    async def generate(self, prompt: str, system: str = "") -> str:
        try:
            result = await self._call_model(PRIMARY_MODEL, prompt, system)
            if result and result.strip():
                return result
            raise RuntimeError("Empty response from primary model")
        except Exception as e:
            # Fallback to haiku
            try:
                return await self._call_model(FALLBACK_MODEL, prompt, system)
            except Exception as fallback_e:
                raise RuntimeError(
                    f"Both primary and fallback Anthropic models failed. Primary Error: {e}"
                )
