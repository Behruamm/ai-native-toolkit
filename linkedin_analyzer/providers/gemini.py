import os
import google.generativeai as genai

from .base import LLMProvider

# 2.5 Pro primary, 2.5 Flash fallback
PRIMARY_MODEL = "gemini-2.5-pro"
FALLBACK_MODEL = "gemini-2.5-flash"


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured")

        genai.configure(api_key=self.api_key)

    async def _call_model(self, model_name: str, prompt: str, system: str = "") -> str:
        # 2.5 Pro is a "thinking" model — needs higher token budget
        max_tokens = 8192 if "pro" in model_name.lower() else 2048

        generation_config = genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=max_tokens,
        )

        system_instruction = system if system else None

        model = genai.GenerativeModel(
            model_name=model_name, system_instruction=system_instruction
        )

        response = await model.generate_content_async(
            prompt, generation_config=generation_config
        )

        # Check if it was blocked by finish_reason or safety ratings
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            raise RuntimeError(
                f"Prompt blocked: {response.prompt_feedback.block_reason}"
            )

        return response.text

    async def generate(self, prompt: str, system: str = "") -> str:
        try:
            result = await self._call_model(PRIMARY_MODEL, prompt, system)
            if result and result.strip():
                return result
            raise RuntimeError("Empty response from primary model")
        except Exception as e:
            # Fallback to Flash on Max tokens or other errors
            try:
                return await self._call_model(FALLBACK_MODEL, prompt, system)
            except Exception as fallback_e:
                raise RuntimeError(
                    f"Both primary and fallback Gemini models failed. Primary Error: {e}"
                )
