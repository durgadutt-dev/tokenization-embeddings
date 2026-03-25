"""
generate.py — Text generation (inference)
------------------------------------------
Given a trained SLM and a text prompt, generates new tokens
one at a time using the model's predicted probability distribution.

Generation loop:
  1. Encode prompt → token IDs
  2. Forward pass  → logits for next token (last position only)
  3. Apply temperature scaling
  4. Sample from the distribution
  5. Append new token, repeat from step 2
  6. Decode all token IDs → text
"""

import torch
from bpe_tokenizer import BPETokenizer
from model import SLM
from config import ModelConfig


def generate(
    model: SLM,
    tokenizer: BPETokenizer,
    prompt: str,
    config: ModelConfig,
) -> str:
    """
    Generate text continuation for a given prompt.

    Args:
        model     : trained SLM
        tokenizer : trained BPETokenizer (same one used during training)
        prompt    : seed text to continue from
        config    : ModelConfig (reads max_new_tokens, temperature, max_seq_len)

    Returns:
        Generated text string (prompt + continuation)
    """
    model.eval()
    token_ids = tokenizer.encode(prompt)

    with torch.no_grad():
        for _ in range(config.max_new_tokens):
            # crop to max_seq_len — model can't handle longer context
            context = token_ids[-config.max_seq_len:]
            inputs  = torch.tensor([context]).to(config.device)  # (1, seq_len)

            logits  = model(inputs)                        # (1, seq_len, vocab_size)
            next_logits = logits[0, -1, :]                 # logits at last position only

            # temperature scaling — divide before softmax
            next_logits = next_logits / config.temperature
            probs       = torch.softmax(next_logits, dim=-1)

            # sample one token from the distribution
            next_id = torch.multinomial(probs, num_samples=1).item()
            token_ids.append(next_id)

    return tokenizer.decode(token_ids)
