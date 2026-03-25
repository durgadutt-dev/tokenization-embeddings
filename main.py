"""
main.py — SLM entry point
--------------------------
Runs the full pipeline in order:

  1. tokenize  — train BPE tokenizer + encode corpus
  2. data      — prepare batches, save preview
  3. model     — build SLM, print architecture summary
  4. train     — run training loop, save weights
  5. generate  — load weights, generate text from a prompt

Usage:
  python main.py              # full pipeline
  python main.py data         # data prep only
  python main.py model        # model summary only
  python main.py train        # train the model
  python main.py generate     # generate text (requires trained model)
"""

import sys
import torch
from pathlib import Path

from config import ModelConfig
import tokenization
import data
import model as model_module
import train as train_module
import generate as generate_module

MODEL_PATH = Path(__file__).parent / "build" / "slm.pt"
PROMPT     = "The machine learning"


def main() -> None:
    config = ModelConfig()
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"

    # ── 1. Tokenization (always runs — other steps depend on it) ──────
    tokenizer, train_corpus, val_corpus = tokenization.build_tokenizer(config)

    # ── 2. Data preparation ───────────────────────────────────────────
    if arg in ("all", "data"):
        train_loader, val_loader = data.get_dataloaders(tokenizer, train_corpus, val_corpus, config)
        data.save_batches_preview(train_loader, config)

    # ── 3. Model summary ──────────────────────────────────────────────
    if arg in ("all", "model"):
        slm = model_module.SLM(config).to(config.device)
        print(slm)
        print(f"\nDevice                    : {config.device}")
        print(f"Total trainable parameters: {slm.count_parameters():,}")

    # ── 4. Training ───────────────────────────────────────────────────
    if arg in ("all", "train"):
        train_loader, val_loader = data.get_dataloaders(tokenizer, train_corpus, val_corpus, config)
        slm = model_module.SLM(config).to(config.device)
        print(f"Device  : {config.device}")
        print(f"Training SLM  ({slm.count_parameters():,} parameters)\n")
        train_module.train(slm, train_loader, val_loader, config)
        torch.save(slm.state_dict(), MODEL_PATH)
        print(f"\nModel saved → {MODEL_PATH}")

    # ── 5. Generation ─────────────────────────────────────────────────
    if arg in ("all", "generate"):
        slm = model_module.SLM(config).to(config.device)
        slm.load_state_dict(torch.load(MODEL_PATH, weights_only=True, map_location=config.device))
        print(f"Prompt    : {PROMPT!r}")
        output = generate_module.generate(slm, tokenizer, PROMPT, config)
        print(f"Generated : {output!r}")


if __name__ == "__main__":
    main()
