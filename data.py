"""
data.py — Training data preparation
--------------------------------------
Two dataset strategies depending on corpus size:

  Small datasets (e.g. txt):
    - Encode all token IDs upfront → cache to disk → TextDataset
    - Sliding window across the full flat token stream

  Large datasets (e.g. tinystories, wikitext):
    - StreamingDataset encodes one story at a time on the fly
    - No giant JSON files written to disk
    - Random window sampled from each story
"""

import json
import random
from pathlib import Path

import torch
from torch.utils.data import Dataset, DataLoader

from bpe_tokenizer import BPETokenizer
from config import ModelConfig
from dataset_registry import LARGE_DATASETS

DATA_DIR        = Path(__file__).parent / "data_files"
TRAIN_IDS_FILE  = DATA_DIR / "train_tokens.json"
VAL_IDS_FILE    = DATA_DIR / "val_tokens.json"
BATCHES_PREVIEW = DATA_DIR / "batches_preview.txt"


# ── Small dataset — encode all, cache, sliding window ─────────────────

class TextDataset(Dataset):
    """
    Converts a flat list of token IDs into (input_seq, target_seq) pairs
    using a sliding window of length config.max_seq_len.
    """

    def __init__(self, token_ids: list[int], config: ModelConfig) -> None:
        self.token_ids = torch.tensor(token_ids, dtype=torch.long)
        self.seq_len   = config.max_seq_len

    def __len__(self) -> int:
        return len(self.token_ids) - self.seq_len

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        input_seq  = self.token_ids[idx : idx + self.seq_len]
        target_seq = self.token_ids[idx + 1 : idx + self.seq_len + 1]
        return input_seq, target_seq


# ── Large dataset — encode on the fly, one story at a time ────────────

class StreamingDataset(Dataset):
    """
    Encodes each story on the fly using the tokenizer.
    Samples a random window of max_seq_len from each encoded story.
    No token IDs are cached to disk.
    """

    def __init__(
        self, corpus: list[str], tokenizer: BPETokenizer, config: ModelConfig
    ) -> None:
        self.corpus    = corpus
        self.tokenizer = tokenizer
        self.seq_len   = config.max_seq_len
        self.pad_id    = tokenizer.special_tokens.get("<|pad|>", 1)

    def __len__(self) -> int:
        return len(self.corpus)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        token_ids = self.tokenizer.encode(self.corpus[idx])

        # pad if story is shorter than seq_len + 1
        if len(token_ids) < self.seq_len + 1:
            token_ids += [self.pad_id] * (self.seq_len + 1 - len(token_ids))

        # sample a random window within the story
        max_start = len(token_ids) - self.seq_len - 1
        start     = random.randint(0, max_start) if max_start > 0 else 0

        input_seq  = torch.tensor(token_ids[start : start + self.seq_len])
        target_seq = torch.tensor(token_ids[start + 1 : start + self.seq_len + 1])
        return input_seq, target_seq


# ── DataLoader factory ────────────────────────────────────────────────

def get_dataloaders(
    tokenizer: BPETokenizer,
    train_corpus: list[str],
    val_corpus: list[str],
    config: ModelConfig,
) -> tuple[DataLoader, DataLoader]:
    """
    Return train and val DataLoaders.

    Small datasets → TextDataset (cached token IDs, sliding window)
    Large datasets → StreamingDataset (on-the-fly encoding, random window)
    """
    if config.data_source in LARGE_DATASETS:
        train_ds = StreamingDataset(train_corpus, tokenizer, config)
        val_ds   = StreamingDataset(val_corpus,   tokenizer, config)
    else:
        train_ids = _load_or_encode(train_corpus, tokenizer, TRAIN_IDS_FILE)
        val_ids   = _load_or_encode(val_corpus,   tokenizer, VAL_IDS_FILE)
        train_ds  = TextDataset(train_ids, config)
        val_ds    = TextDataset(val_ids,   config)

    train_loader = DataLoader(train_ds, batch_size=config.batch_size, shuffle=True)
    val_loader   = DataLoader(val_ds,   batch_size=config.batch_size, shuffle=False)
    return train_loader, val_loader


def _load_or_encode(
    corpus: list[str], tokenizer: BPETokenizer, cache_file: Path
) -> list[int]:
    """Load token IDs from cache or encode and save."""
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    token_ids: list[int] = []
    for sentence in corpus:
        token_ids.extend(tokenizer.encode(sentence))
    cache_file.write_text(json.dumps(token_ids))
    return token_ids


def save_batches_preview(
    dataloader: DataLoader, config: ModelConfig
) -> None:
    """Write a preview of the first 3 batches to batches_preview.txt."""
    if BATCHES_PREVIEW.exists():
        return
    lines = [
        f"Dataset        : {config.data_source}",
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
