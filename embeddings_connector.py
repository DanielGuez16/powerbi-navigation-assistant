"""Embeddings connector using the OpenAI embeddings API.

Exposes ``generate_embeddings(text)`` returning a 1-D list of floats.
Compatible with OpenAI, Azure OpenAI and any OpenAI-compatible endpoint
(set ``OPENAI_BASE_URL`` to override).
"""
import os
import traceback

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class EMBEDDINGConnector:
    def __init__(self) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")
        if not api_key:
            print("⚠ OPENAI_API_KEY not set — EMBEDDINGConnector calls will fail until configured.")
        self.client = OpenAI(api_key=api_key or "missing-key", base_url=base_url) if api_key else None
        self.model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

    def generate_embeddings(self, text: str, modelID: str | None = None) -> list[float]:
        """Generate an embedding vector for a single piece of text."""
        if self.client is None:
            raise RuntimeError("OPENAI_API_KEY is not set; cannot generate embeddings.")
        if not isinstance(text, str):
            text = str(text)
        try:
            response = self.client.embeddings.create(
                model=modelID or self.model,
                input=text,
            )
            return list(response.data[0].embedding)
        except Exception as e:
            print(f"Embedding error: {e}")
            print(traceback.format_exc())
            raise


if __name__ == "__main__":
    connector = EMBEDDINGConnector()
    vec = connector.generate_embeddings(text="Hello, embeddings world!")
    print(f"Embedding length: {len(vec)}")
