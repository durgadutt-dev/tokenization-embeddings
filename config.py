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

    # Dataset — key from datasets.DATASETS registry
    # Options: "txt", "tinystories", "wikitext"
    data_source: str  = "tinystories"

    # Vocabulary — 8192 covers most TinyStories words as whole tokens
    vocab_size: int   = 8192

    # Model dimensions
    embed_dim: int    = 256    # size of each token embedding vector
    num_heads: int    = 8      # attention heads (embed_dim must be divisible)
    num_layers: int   = 4      # number of transformer blocks
    ffn_dim: int      = 1024   # 4× embed_dim (standard ratio)
    max_seq_len: int  = 256    # captures most of a short story

    # Training
    batch_size: int   = 32     # reduce to 16 if GPU runs out of memory
    epochs: int       = 3      # 2M stories — 1 epoch is already a lot of data
    learning_rate: float = 3e-4
    dropout: float    = 0.1

    # Generation
    max_new_tokens: int = 200  # enough for a short story
    temperature: float  = 0.8  # slightly focused
