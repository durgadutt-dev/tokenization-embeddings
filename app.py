import gradio as gr
import requests
from config import MAX_NEW_TOKENS, TEMPERATURE, DO_SAMPLE, BACKEND, OLLAMA_MODEL

if BACKEND == "transformers":
    from model import load_model, generate as transformers_generate
    model, tokenizer = load_model()


def ollama_generate(message: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": message}],
            "stream": False,
            "options": {
                "num_predict": MAX_NEW_TOKENS,
                "temperature": TEMPERATURE,
            },
        },
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def chat(message, history):
    if BACKEND == "ollama":
        return ollama_generate(message)
    return transformers_generate(
        model, tokenizer, message,
        max_new_tokens=MAX_NEW_TOKENS,
        temperature=TEMPERATURE,
        do_sample=DO_SAMPLE,
    )


demo = gr.ChatInterface(
    fn=chat,
    title=f"Phi-3 Mini ({BACKEND})",
)

if __name__ == "__main__":
    demo.launch()
