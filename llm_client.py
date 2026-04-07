"""
llm_client.py
-------------
Thin wrapper around the configured model backend (Ollama or HuggingFace Transformers).

Usage:
    from llm_client import call_model
    reply = call_model([{"role": "user", "content": "Hello"}])
"""
import logging
import requests
from config import BACKEND, OLLAMA_MODEL, MAX_NEW_TOKENS, TEMPERATURE, DO_SAMPLE

if BACKEND == "transformers":
    from model import load_model, generate as _transformers_generate
    _model, _tokenizer = load_model()


def call_model(
    messages: list[dict],
    max_new_tokens: int = MAX_NEW_TOKENS,
    timeout: int = 120,
) -> str:
    """
    Send a list of chat messages to the configured backend and return the reply.

    Args:
        messages:       List of {"role": "system"|"user"|"assistant", "content": str}.
        max_new_tokens: Token budget for the response.
        timeout:        Request timeout in seconds (Ollama only).

    Returns:
        The model reply as a plain string, or a ⚠️-prefixed error string on failure.
    """
    try:
        if BACKEND == "ollama":
            response = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_predict": max_new_tokens,
                        "temperature": TEMPERATURE,
                    },
                },
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()["message"]["content"]

        # Transformers backend
        prompt = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
        return _transformers_generate(
            _model, _tokenizer, prompt,
            max_new_tokens=max_new_tokens,
            temperature=TEMPERATURE,
            do_sample=DO_SAMPLE,
        )

    except requests.exceptions.ConnectionError:
        return "⚠️ Cannot reach Ollama. Run: ollama serve"
    except requests.exceptions.Timeout:
        return "⚠️ Model timed out — try a shorter prompt or increase timeout."
    except Exception as e:
        logging.error(f"call_model error: {e}")
        return f"⚠️ Unexpected error: {e}"
