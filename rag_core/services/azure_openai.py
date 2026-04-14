"""Azure OpenAI: embeddings + chat for RAG."""

from __future__ import annotations

from dataclasses import dataclass
import time

from django.conf import settings
from openai import AzureOpenAI


@dataclass
class AzureOpenAIConfig:
    endpoint: str
    api_key: str
    api_version: str
    chat_deployment: str
    embedding_deployment: str


def _config() -> AzureOpenAIConfig:
    return AzureOpenAIConfig(
        endpoint=(settings.AZURE_OPENAI_ENDPOINT or "").rstrip("/"),
        api_key=settings.AZURE_OPENAI_API_KEY or "",
        api_version=settings.AZURE_OPENAI_API_VERSION,
        chat_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT or "",
        embedding_deployment=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT or "",
    )


def get_client() -> AzureOpenAI:
    c = _config()
    if not c.endpoint or not c.api_key:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set.")
    return AzureOpenAI(
        azure_endpoint=c.endpoint,
        api_key=c.api_key,
        api_version=c.api_version,
    )


def _with_retries(fn, *, retries: int = 3, delay_s: float = 0.8):
    last_exc = None
    for attempt in range(retries):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - network behavior
            last_exc = exc
            if attempt == retries - 1:
                break
            time.sleep(delay_s * (2**attempt))
    raise RuntimeError(f"Azure OpenAI request failed after retries: {last_exc}") from last_exc


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed; returns one vector per input string."""
    c = _config()
    if not c.embedding_deployment:
        raise RuntimeError("AZURE_OPENAI_EMBEDDING_DEPLOYMENT must be set.")
    client = get_client()
    # Azure OpenAI embeddings API
    resp = _with_retries(
        lambda: client.embeddings.create(
            model=c.embedding_deployment,
            input=texts,
        )
    )
    return [item.embedding for item in resp.data]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def chat_with_context(
    system_prompt: str,
    user_question: str,
    context_chunks: list[str],
) -> str:
    """Single-turn RAG answer from retrieved chunks."""
    c = _config()
    if not c.chat_deployment:
        raise RuntimeError("AZURE_OPENAI_CHAT_DEPLOYMENT must be set.")
    client = get_client()
    context_block = "\n\n---\n\n".join(context_chunks)
    user_content = (
        "Use ONLY the following context to answer. If the answer is not in the context, "
        "say you don't know from the provided documents.\n\n"
        f"Context:\n{context_block}\n\nQuestion: {user_question}"
    )
    resp = _with_retries(
        lambda: client.chat.completions.create(
            model=c.chat_deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=768,
        )
    )
    choice = resp.choices[0]
    if not choice.message or not choice.message.content:
        return ""
    return choice.message.content.strip()


def healthcheck() -> None:
    embed_query("healthcheck")
