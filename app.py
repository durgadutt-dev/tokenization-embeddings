"""
app.py
------
Gradio UI for the Health Insurance Plan Similarity Recommender.

Layout:
  Left panel  — JSON upload + settings (top-k, explain toggle)
  Right panel — Results table + per-plan explanation cards

Flow:
  1. User uploads their current plan JSON (or pastes raw JSON)
  2. Clicks "Find Similar Plans"
  3. Top-K catalog matches are shown with similarity scores
  4. Each match includes a plain-English explanation from Phi-3 (optional)

Start:
    python app.py
"""
import json
import logging
import os

import gradio as gr

from config import CATALOG_INDEX_DIR, OLLAMA_MODEL, TOP_K
from recommender import recommend

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)

# ── Catalog readiness check ───────────────────────────────────────────────────

def _catalog_ready() -> bool:
    required = [
        "catalog_structured.npy",
        "catalog_semantic.npy",
        "plan_metadata.json",
        "scaler.pkl",
    ]
    return all(os.path.exists(os.path.join(CATALOG_INDEX_DIR, f)) for f in required)


def _catalog_plan_count() -> int:
    path = os.path.join(CATALOG_INDEX_DIR, "plan_metadata.json")
    if not os.path.exists(path):
        return 0
    with open(path) as f:
        return len(json.load(f))


# ── Core handler ──────────────────────────────────────────────────────────────

def run_recommender(
    upload_file,
    raw_json_text: str,
    top_k: int,
    explain: bool,
) -> tuple[str, str]:
    """
    Called when the user clicks "Find Similar Plans".

    Resolves the query plan from either the uploaded file or the pasted JSON
    text box (file takes priority), runs the recommender, and returns:
      - results_md: Markdown table + explanation cards for the Results panel.
      - status_md:  Status / error message for the Status box.
    """
    if not _catalog_ready():
        return (
            "",
            "**Catalog index not found.**\n\nRun `python catalog_builder.py` first to build the index.",
        )

    # ── Resolve input ─────────────────────────────────────────────────────────
    query_plan = None

    if upload_file is not None:
        try:
            with open(upload_file, encoding="utf-8") as f:
                query_plan = json.load(f)
        except Exception as e:
            return "", f"**Could not parse uploaded file:** {e}"

    elif raw_json_text.strip():
        try:
            query_plan = json.loads(raw_json_text)
        except json.JSONDecodeError as e:
            return "", f"**Invalid JSON in text box:** {e}"

    if query_plan is None:
        return "", "**No input provided.** Upload a plan JSON file or paste JSON into the text box."

    query_name = (
        query_plan.get("plan_details", {}).get("plan_name")
        or "Uploaded Plan"
    )

    # ── Run recommender ───────────────────────────────────────────────────────
    logging.info(f"Running recommender for: {query_name!r} | top_k={top_k} explain={explain}")
    try:
        results = recommend(query_plan, top_k=int(top_k), explain=explain)
    except Exception as e:
        logging.exception("recommend() failed")
        return "", f"**Recommender error:** {e}"

    if not results:
        return "", "No results returned — the catalog may be empty."

    # ── Format Markdown output ────────────────────────────────────────────────
    lines = [f"## Results for: *{query_name}*\n"]

    # Summary table
    lines.append(
        "| # | Plan | Insurer | Type | Metal | Score | Structured | Semantic |"
    )
    lines.append(
        "|---|------|---------|------|-------|------:|------------|---------|"
    )
    for r in results:
        lines.append(
            f"| {r['rank']} | {r['plan_name']} | {r['insurer']} "
            f"| {r['plan_type']} | {r['metal_level']} "
            f"| **{r['similarity_score']:.4f}** "
            f"| {r['structured_score']:.4f} | {r['semantic_score']:.4f} |"
        )

    lines.append("")

    # Explanation cards
    for r in results:
        score_bar = _score_bar(r["similarity_score"])
        lines.append(f"---\n### #{r['rank']} — {r['plan_name']}")
        lines.append(
            f"**Insurer:** {r['insurer']}  |  "
            f"**Type:** {r['plan_type']}  |  "
            f"**Metal:** {r['metal_level']}  |  "
            f"**Network:** {r['network_name']}"
        )
        lines.append(
            f"\n**Similarity score:** {r['similarity_score']:.4f}  {score_bar}"
        )
        lines.append(
            f"*(structured: {r['structured_score']:.4f}  ·  semantic: {r['semantic_score']:.4f})*"
        )
        if r.get("explanation"):
            lines.append(f"\n**Why matched:**\n> {r['explanation'].strip()}")
        lines.append("")

    results_md = "\n".join(lines)
    status_md  = f"Found **{len(results)}** match(es) for *{query_name}* from a catalog of **{_catalog_plan_count()}** plans."

    return results_md, status_md


def _score_bar(score: float, width: int = 20) -> str:
    """Render a simple Unicode progress bar for a similarity score."""
    clamped = max(0.0, min(1.0, score))
    filled  = round(clamped * width)
    return "█" * filled + "░" * (width - filled) + f" {clamped*100:.1f}%"


# ── JSON pretty-print helper ──────────────────────────────────────────────────

def pretty_print_json(upload_file, raw_text: str) -> str:
    """Pretty-print the resolved JSON so the user can verify what was loaded."""
    if upload_file is not None:
        try:
            with open(upload_file, encoding="utf-8") as f:
                return json.dumps(json.load(f), indent=2)
        except Exception as e:
            return f"Parse error: {e}"
    if raw_text.strip():
        try:
            return json.dumps(json.loads(raw_text), indent=2)
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {e}"
    return ""


# ── Gradio UI ─────────────────────────────────────────────────────────────────

_catalog_count = _catalog_plan_count()
_status_emoji  = "✅" if _catalog_ready() else "⚠️"
_catalog_label = (
    f"{_status_emoji}  Catalog ready — **{_catalog_count}** plan(s) indexed."
    if _catalog_ready()
    else "⚠️  Catalog not built. Run `python catalog_builder.py` first."
)

with gr.Blocks(title="Health Plan Recommender") as demo:

    gr.Markdown(
        "# Health Insurance Plan Similarity Recommender\n"
        f"*Catalog: {_catalog_count} plan(s) · LLM: `{OLLAMA_MODEL}`*"
    )
    gr.Markdown(_catalog_label)

    with gr.Row():

        # ── Left panel: input ─────────────────────────────────────────────────
        with gr.Column(scale=1):
            gr.Markdown("### Your Plan")

            upload_file = gr.File(
                label="Upload plan JSON",
                file_types=[".json"],
            )

            gr.Markdown("*— or paste JSON directly —*")

            raw_json = gr.Textbox(
                label="Raw JSON",
                placeholder='{\n  "plan_details": { ... }\n}',
                lines=12,
                max_lines=30,
            )

            preview_btn = gr.Button("Preview loaded JSON", variant="secondary", size="sm")
            json_preview = gr.Code(
                label="Loaded plan (preview)",
                language="json",
                lines=8,
                interactive=False,
                visible=False,
            )

            gr.Markdown("### Settings")

            top_k_slider = gr.Slider(
                minimum=1,
                maximum=10,
                value=TOP_K,
                step=1,
                label="Number of results (top-k)",
            )
            explain_toggle = gr.Checkbox(
                value=True,
                label="Generate plain-English explanation (requires Ollama)",
            )

            find_btn = gr.Button("Find Similar Plans", variant="primary")

        # ── Right panel: results ──────────────────────────────────────────────
        with gr.Column(scale=2):
            gr.Markdown("### Results")

            status_box = gr.Markdown(
                value="*Upload a plan JSON and click **Find Similar Plans**.*"
            )

            results_display = gr.Markdown(
                value="",
                label="Matches",
            )

    # ── Event wiring ──────────────────────────────────────────────────────────

    preview_btn.click(
        fn=pretty_print_json,
        inputs=[upload_file, raw_json],
        outputs=[json_preview],
    ).then(
        fn=lambda: gr.update(visible=True),
        outputs=[json_preview],
    )

    find_btn.click(
        fn=lambda: (gr.update(value="*Searching …*"), gr.update(value="")),
        outputs=[status_box, results_display],
    ).then(
        fn=run_recommender,
        inputs=[upload_file, raw_json, top_k_slider, explain_toggle],
        outputs=[results_display, status_box],
    )


if __name__ == "__main__":
    demo.launch(
        show_error=True,
        theme=gr.themes.Soft(),
    )
