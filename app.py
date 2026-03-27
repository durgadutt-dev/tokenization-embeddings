"""
app.py
------
Gradio web UI for the Insurance RAG Assistant.

Flow:
  1. User uploads one or more insurance PDF files (incumbent plans)
  2. Each PDF is extracted by pdfplumber and chunked + embedded into ChromaDB
  3. User asks questions in chat
  4. Relevant chunks are retrieved via semantic search
  5. Retrieved chunks + question are sent to Phi-3 for a grounded answer

Layout:
  Left panel  — PDF upload + list of indexed plans
  Right panel — Chat

Modules:
  pdf_extractor → raw text per page
  embedder      → chunk, embed, store in ChromaDB
  retriever     → semantic search at query time
  llm_client    → send retrieved context + question to Phi-3
"""
import os
import logging
import gradio as gr

from config import BACKEND, OLLAMA_MODEL
from pdf_extractor import extract_pdf
from embedder import load_embedder, get_collection, embed_and_store, list_plans
from retriever import retrieve
from llm_client import call_model

# ── Logging ───────────────────────────────────────────────────────────────────
_log_handler = logging.FileHandler("insurance_rag.log")
_log_handler.setFormatter(
    logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
logging.getLogger().addHandler(_log_handler)
logging.getLogger().setLevel(logging.INFO)

# ── Shared resources (loaded once at startup) ─────────────────────────────────
embedder   = load_embedder()
collection = get_collection()


# ── PDF upload handler ────────────────────────────────────────────────────────

def upload_plans(files) -> str:
    """
    Called when PDFs are uploaded.

    Extracts text from each file, chunks and embeds the content,
    and stores it in ChromaDB. Returns a status message for the UI.

    Args:
        files: List of file paths from gr.Files upload component.

    Returns:
        Status string summarising what was indexed.
    """
    if not files:
        return "No files uploaded."

    results = []
    for file_path in files:
        plan_name = os.path.splitext(os.path.basename(file_path))[0]
        logging.info(f"Processing plan: {plan_name} | {file_path}")

        pages    = extract_pdf(file_path)
        n_chunks = embed_and_store(pages, plan_name, embedder, collection)
        results.append(f"✓ {plan_name} — {n_chunks} chunks indexed")

    # Show all currently indexed plans
    all_plans = list_plans(collection)
    plan_list = "\n".join(f"  • {p}" for p in all_plans)

    return "\n".join(results) + f"\n\nIndexed plans:\n{plan_list}"


# ── Chat handler ──────────────────────────────────────────────────────────────

def respond(message: str, history: list) -> tuple:
    """
    Handle a user chat message.

    1. Retrieve the top-K most relevant chunks from ChromaDB
    2. Build a prompt with retrieved context + conversation history
    3. Send to Phi-3 and return the reply

    If no plans are indexed, prompts the user to upload PDFs first.
    """
    if not message.strip():
        return history, ""

    if collection.count() == 0:
        history.append((message, "⚠️ Please upload at least one insurance PDF first."))
        return history, ""

    # Step 1: semantic search — find relevant chunks
    chunks = retrieve(message, collection, embedder)

    if not chunks:
        history.append((message, "⚠️ No relevant information found in the indexed plans."))
        return history, ""

    # Step 2: build context from retrieved chunks
    context = "\n\n".join(f"- {chunk}" for chunk in chunks)

    system_prompt = (
        "You are an expert health insurance advisor. "
        "Answer the user's question using ONLY the insurance plan excerpts below. "
        "Be specific, cite coverage details, and flag any limitations or "
        "preauthorisation requirements. "
        "If the answer is not in the excerpts, say so clearly.\n\n"
        f"Relevant plan excerpts:\n{context}"
    )

    # Step 3: build full message list with conversation history
    messages = [{"role": "system", "content": system_prompt}]
    for user_msg, assistant_msg in history:
        messages.append({"role": "user",      "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_msg})
    messages.append({"role": "user", "content": message})

    # Step 4: call LLM
    reply = call_model(messages)
    history.append((message, reply))
    return history, ""


# ── Gradio UI ─────────────────────────────────────────────────────────────────

with gr.Blocks(title="Insurance RAG Assistant", theme=gr.themes.Soft()) as demo:
    gr.Markdown("## Insurance RAG Assistant")
    gr.Markdown(f"`Backend: {BACKEND}` | `Model: {OLLAMA_MODEL}`")

    with gr.Row():

        # Left panel: upload + index status
        with gr.Column(scale=1):
            pdf_upload = gr.Files(
                label="Upload Insurance PDFs",
                file_types=[".pdf"],
            )
            upload_btn = gr.Button("Index Plans", variant="primary")
            upload_status = gr.Textbox(
                label="Index Status",
                lines=8,
                interactive=False,
                placeholder="Upload PDFs and click 'Index Plans'…",
            )

        # Right panel: chat
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(height=520, label="Chat")
            msg_input = gr.Textbox(
                placeholder="Ask about your plan, e.g. What is my deductible?",
                show_label=False,
            )
            gr.ClearButton([msg_input, chatbot], value="Clear Chat")

    # Wire upload button
    upload_btn.click(
        fn=upload_plans,
        inputs=[pdf_upload],
        outputs=[upload_status],
    )

    # Wire chat input
    msg_input.submit(
        fn=respond,
        inputs=[msg_input, chatbot],
        outputs=[chatbot, msg_input],
    )


if __name__ == "__main__":
    demo.launch()
