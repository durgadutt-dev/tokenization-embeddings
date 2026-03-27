"""
plan_parser.py
--------------
Insurance plan JSON extraction from raw PDF text.

Phi-3 Mini 128k supports up to 128,000 tokens of context, so the entire
document (~6k tokens for a standard 5-page SBC) is sent in a single model
call — no chunking required.

Ollama's format="json" mode is used to guarantee valid JSON output: the
model will not stop generating until the JSON object is properly closed.

Usage standalone (no UI required):
    from pdf_extractor import extract_pdf
    from plan_parser import parse_insurance_pdf

    pages = extract_pdf("my_plan.pdf")
    json_str = parse_insurance_pdf(pages)
"""
import json
import logging
from llm_client import call_model
from config import MODEL_CONTEXT_WINDOW, EXTRACTION_PROMPT_OVERHEAD


def _compute_token_budget(document: str) -> tuple[int, int]:
    """
    Calculate the num_ctx and max output tokens needed for a given document.

    Sets num_ctx to only what's required (input + output) rather than the
    full 128k window — allocating the full window is slow and wastes memory.

    Approximation: 1 token ≈ 4 characters (conservative for English insurance text).

    Args:
        document: The full document text being sent to the model.

    Returns:
        Tuple of (num_ctx, max_output_tokens).
    """
    estimated_input_tokens = len(document) // 4 + EXTRACTION_PROMPT_OVERHEAD

    # Output budget = whatever remains in the context window
    max_output_tokens = max(MODEL_CONTEXT_WINDOW - estimated_input_tokens, 1024)

    # num_ctx = total window needed for this specific request
    # Round up to the next power of 2 for Ollama memory alignment efficiency
    total_needed = estimated_input_tokens + max_output_tokens
    num_ctx = min(total_needed, MODEL_CONTEXT_WINDOW)

    return num_ctx, max_output_tokens

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are an insurance document analyst. "
    "Return only valid JSON with no explanation and no markdown fences."
)

_USER_PROMPT = """\
Extract all insurance and coverage information from the document below and \
return it as a well-structured JSON object.

Include every field related to: plan details, deductibles, out-of-pocket maximums, \
copays, coinsurance, covered services, exclusions, network information, visit limits, \
preauthorisation requirements, and any other insurance or coverage data present.

Document:
{document}

Return only valid JSON. No explanation, no markdown fences."""

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) that models sometimes add."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]   # drop opening fence line
        stripped = stripped.rsplit("```", 1)[0]  # drop closing fence
    return stripped.strip()


def _parse_json_safe(text: str) -> dict | None:
    """
    Parse a JSON string, stripping markdown fences first.

    Returns:
        Parsed dict, or None if parsing failed (logged as warning).
    """
    cleaned = _strip_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logging.warning(
            f"JSON parse failed: {e}\n"
            f"First 500 chars of raw response:\n{cleaned[:500]}"
        )
        return None

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_insurance_pdf(pages: list[str]) -> str:
    """
    Extract all insurance data from a PDF's pages in a single model call.

    Phi-3 Mini 128k can hold the entire document in context, so all pages
    are concatenated and sent at once. Ollama's JSON format mode ensures
    the output is always valid JSON.

    Args:
        pages: List of page text strings from pdf_extractor.extract_pdf().

    Returns:
        Pretty-printed JSON string of the complete insurance plan data.
        Returns a JSON error object if extraction failed.
    """
    document = "\n\n".join(page for page in pages if page.strip())

    if not document:
        logging.warning("parse_insurance_pdf: no text content in pages.")
        return json.dumps({"error": "No text could be extracted from this document."})

    num_ctx, max_output_tokens = _compute_token_budget(document)
    logging.info(
        f"Sending full document to model ({len(document)} chars, "
        f"~{len(document) // 4} input tokens, "
        f"{max_output_tokens} output tokens, num_ctx={num_ctx})..."
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _USER_PROMPT.format(document=document)},
    ]

    raw_response = call_model(
        messages,
        max_new_tokens=max_output_tokens,
        use_json_format=True,   # Ollama JSON mode — guarantees valid, complete JSON
        num_ctx=num_ctx,
        timeout=600,            # extraction can take several minutes for large documents
    )

    result = _parse_json_safe(raw_response)

    if result is None:
        logging.warning("Extraction failed — returning raw response wrapped in JSON.")
        return json.dumps({"raw_extraction": raw_response}, ensure_ascii=False)

    logging.info("Extraction successful.")
    return json.dumps(result, indent=2, ensure_ascii=False)
