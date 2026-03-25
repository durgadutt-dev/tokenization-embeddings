"""
config.py — Model & training hyperparameters
---------------------------------------------
All knobs for the SLM in one place. Change values here;
everything else reads from this config.
"""

import torch
from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    # Device — automatically uses GPU if available (e.g. Colab T4)
    device: str = field(default_factory=lambda: "cuda" if torch.cuda.is_available() else "cpu")

    # Vocabulary / tokenizer
    vocab_size: int   = 1000   # BPE target vocabulary size
    corpus_file: str  = "corpus.txt"

    # Model dimensions
    embed_dim: int    = 128    # size of each token embedding vector
    num_heads: int    = 4      # attention heads (embed_dim must be divisible)
    num_layers: int   = 2      # number of transformer blocks
    ffn_dim: int      = 512    # hidden size inside feed-forward layers
    max_seq_len: int  = 16     # maximum token sequence length

    # Training
    batch_size: int   = 16
    epochs: int       = 10
    learning_rate: float = 3e-4
    dropout: float    = 0.1

    # Generation
    max_new_tokens: int = 50   # tokens to generate per prompt
    temperature: float  = 1.0  # > 1 more random, < 1 more focused
