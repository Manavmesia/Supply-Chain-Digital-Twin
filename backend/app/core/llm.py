"""
LLM Provider Factory for Multi-Agent System.

Provides get_llm() to instantiate ChatGroq or other specified providers.
"""

from __future__ import annotations

from typing import Any
from langchain_core.language_models.chat_models import BaseChatModel
from app.core.config import settings


def get_llm(
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """
    Factory function to initialize and return a LangChain ChatModel instance.
    Defaults to Groq (llama-3.3-70b-versatile).
    """
    provider = (provider or settings.LLM_PROVIDER).lower()
    model = model or settings.LLM_MODEL
    temp = settings.LLM_TEMPERATURE if temperature is None else temperature

    if provider == "groq":
        from langchain_groq import ChatGroq

        api_key = settings.GROQ_API_KEY
        return ChatGroq(
            model=model or "llama-3.3-70b-versatile",
            temperature=temp,
            groq_api_key=api_key if api_key else None,
            **kwargs,
        )
    else:
        raise ValueError(
            f"Unsupported LLM provider: '{provider}'. Supported provider is 'groq'."
        )
