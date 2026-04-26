"""LLM connector using the OpenAI API.

A thin wrapper that exposes ``get_llm_response(user_prompt, context_prompt, ...)``.
Compatible with OpenAI, Azure OpenAI and any OpenAI-compatible endpoint
(set ``OPENAI_BASE_URL`` to override the default base).
"""
import os
import traceback
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class LLMConnector:
    def __init__(self) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")  # optional, e.g. Azure proxy
        if not api_key:
            print("⚠ OPENAI_API_KEY not set — LLMConnector calls will fail until configured.")
        self.client = OpenAI(api_key=api_key or "missing-key", base_url=base_url) if api_key else None
        self.default_model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    def get_llm_response(
        self,
        user_prompt: str,
        context_prompt: str = "",
        modelID: str | None = None,
        temperature: float = 0.0,
        outputMaxTokens: int = 1000,
        outputFormat: str = "TEXT",
    ) -> str:
        """Generate a response from the chat completions endpoint.

        Args:
            user_prompt: The main user message.
            context_prompt: Optional system instructions.
            modelID: Override for the model id. Falls back to ``LLM_MODEL`` env var.
            temperature: Sampling temperature.
            outputMaxTokens: Maximum tokens in the response.
            outputFormat: ``"JSON"`` to enforce JSON output, otherwise free text.
        """
        if self.client is None:
            return (
                "LLM is not configured. Set the OPENAI_API_KEY environment variable "
                "and reload the application."
            )

        messages: list[dict[str, Any]] = []
        if context_prompt:
            messages.append({"role": "system", "content": context_prompt})
        messages.append({"role": "user", "content": user_prompt})

        kwargs: dict[str, Any] = {
            "model": modelID or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": outputMaxTokens,
        }
        if outputFormat.upper() == "JSON":
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"LLM error: {e}")
            print(traceback.format_exc())
            return (
                "We're sorry, the language model is currently unreachable. "
                "Please verify your API key and try again."
            )

    def list_all_models(self) -> list[str]:
        """List models available on the configured backend."""
        if self.client is None:
            return []
        try:
            return [m.id for m in self.client.models.list().data]
        except Exception as e:
            print(f"list_all_models failed: {e}")
            return []


if __name__ == "__main__":
    llm = LLMConnector()
    print("Models:", llm.list_all_models()[:10])
    print(llm.get_llm_response(user_prompt="What is the capital of France?"))
