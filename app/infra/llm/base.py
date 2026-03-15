from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    async def call(self, user_prompt: str) -> dict[str, Any]:
        """Send a prompt to the provider and return the parsed recommendation dict."""
