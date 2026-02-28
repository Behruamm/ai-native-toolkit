from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system: str = "") -> str:
        """
        Generate text from an LLM given a prompt and an optional system message.
        """
        pass
