"""
data.py — Training data preparation
--------------------------------------
Receives the flat token ID stream from tokenization.py and prepares
batches for the training loop.

Responsibilities:
  1. Slide a fixed-length window to create (input, target) pairs
     e.g. token stream [A B C D E] with seq_len=3 →
          input  [A B C]  target [B C D]
          input  [B C D]  target [C D E]
  2. Wrap in a DataLoader for batched training
"""

import json
from pathlib import Path

import torch
from torch.utils.data import Dataset, DataLoader

from config import ModelConfig

DATA_DIR          = Path(__file__).parent / "data_files"
TRAIN_IDS_FILE    = DATA_DIR / "train_tokens.json"
VAL_IDS_FILE      = DATA_DIR / "val_tokens.json"
BATCHES_PREVIEW   = DATA_DIR / "batches_preview.txt"


class TextDataset(Dataset):
    """
    Converts a flat list of token IDs into (input_seq, target_seq) pairs
    using a sliding window of length config.max_seq_len.
    """

    def __init__(self, token_ids: list[int], config: ModelConfig) -> None:
        self.token_ids = torch.tensor(token_ids, dtype=torch.long)
        self.seq_len   = config.max_seq_len

    def __len__(self) -> int:
        # each window needs seq_len + 1 tokens (input + one target token)
        return len(self.token_ids) - self.seq_len

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        input_seq  = self.token_ids[idx : idx + self.seq_len]
        target_seq = self.token_ids[idx + 1 : idx + self.seq_len + 1]
        return input_seq, target_seq


def get_dataloaders(config: ModelConfig) -> tuple[DataLoader, DataLoader]:
    """
    Read train_tokens.json and val_tokens.json and return both DataLoaders.

    Args:
        config : ModelConfig (reads batch_size, max_seq_len)

    Returns:
        train_loader : shuffled DataLoader for training
        val_loader   : unshuffled DataLoader for validation
    """
    train_ids: list[int] = json.loads(TRAIN_IDS_FILE.read_text())
    val_ids:   list[int] = json.loads(VAL_IDS_FILE.read_text())

    train_loader = DataLoader(
        TextDataset(train_ids, config),
        batch_size=config.batch_size, shuffle=True
    )
    val_loader = DataLoader(
        TextDataset(val_ids, config),
        batch_size=config.batch_size, shuffle=False
    )
    return train_loader, val_loader


def save_batches_preview(
    dataloader: DataLoader, config: ModelConfig, token_ids: list[int]
) -> None:
    """
    Write a preview of the first 3 batches to batches_preview.txt.
    Skipped if the file already exists.
    """
    if BATCHES_PREVIEW.exists():
        return

    lines = [
        f"Total tokens   : {len(token_ids)}",
        f"Total batches  : {len(dataloader)}",
        f"Batch size     : {config.batch_size}",
        f"Sequence length: {config.max_seq_len}",
        "",
    ]
    for i, (inputs, targets) in enumerate(dataloader):
        lines.append(f"Batch {i + 1}:")
        for inp, tgt in zip(inputs.tolist(), targets.tolist()):
            lines.append(f"  input : {inp}")
            lines.append(f"  target: {tgt}")
        if i == 2:
            lines.append("  ...")
            break

    BATCHES_PREVIEW.write_text("\n".join(lines))
