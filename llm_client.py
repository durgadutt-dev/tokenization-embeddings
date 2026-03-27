"""
llm_client.py
-------------
Thin wrapper around the configured model backend (Ollama or HuggingFace Transformers).

Usage anywhere in the project:
    from llm_client import call_model
    reply = call_model([{"role": "user", "content": "Hello"}])

To switch backends, change BACKEND in config.py.
"""
import logging
import requests
from config import BACKEND, OLLAMA_MODEL, MAX_NEW_TOKENS, TEMPERATURE, DO_SAMPLE

# Load the HuggingFace model once at import time if transformers backend is active.
# This is intentionally done at module level so the model is shared across callers.
if BACKEND == "transformers":
    from model import load_model, generate as _transformers_generate
    _model, _tokenizer = load_model()


def call_model(messages: list[dict]) -> str:
    """
    Send a list of chat messages to the configured backend and return the reply.

    Args:
        messages: List of {"role": "system"|"user"|"assistant", "content": str}.
                  System messages are supported by Ollama natively.
                  For the transformers backend they are flattened into the prompt.

    Returns:
        The model's reply as a plain string.
        Returns a user-friendly error string (prefixed with ⚠️) on failure
        so callers don't need to handle exceptions.
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
                        "num_predict": MAX_NEW_TOKENS,
                        "temperature": TEMPERATURE,
                    },
                },
                timeout=120,
            )
            response.raise_for_status()
            return response.json()["message"]["content"]

        # Transformers backend: flatten the message list into a single prompt string.
        # TODO (Colab migration): replace with tokenizer.apply_chat_template()
        # to properly handle multi-turn history and system prompts.
        prompt = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in messages
        )
        return _transformers_generate(
            _model, _tokenizer, prompt,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            do_sample=DO_SAMPLE,
        )

    except requests.exceptions.ConnectionError:
        return "⚠️ Cannot reach Ollama. Make sure it is running: `ollama serve`"
    except requests.exceptions.Timeout:
        return "⚠️ Model timed out. Try a shorter question or reduce MAX_NEW_TOKENS in config.py."
    except Exception as e:
        logging.error(f"call_model error: {e}")
        return f"⚠️ Unexpected error: {e}"
