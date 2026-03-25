"""
datasets.py — Dataset registry
--------------------------------
Each dataset is a loader function that returns (train_corpus, val_corpus)
as lists of strings.

To add a new dataset:
  1. Write a load_* function below
  2. Register it in DATASETS dict with a key

Then set config.data_source = "your_key" in config.py.
"""

from pathlib import Path

DATA_DIR = Path(__file__).parent / "data_files"


def load_txt() -> tuple[list[str], list[str]]:
    """Load from local train.txt and val.txt — one sentence per line."""
    with open(DATA_DIR / "train.txt") as f:
        train = [line.strip() for line in f if line.strip()]
    with open(DATA_DIR / "val.txt") as f:
        val = [line.strip() for line in f if line.strip()]
    return train, val


def load_tinystories() -> tuple[list[str], list[str]]:
    """Load TinyStories from HuggingFace datasets."""
    from datasets import load_dataset
    dataset = load_dataset("roneneldan/TinyStories")
    return dataset["train"]["text"], dataset["validation"]["text"]


def load_wikitext() -> tuple[list[str], list[str]]:
    """Load WikiText-2 from HuggingFace datasets."""
    from datasets import load_dataset
    dataset = load_dataset("wikitext", "wikitext-2-raw-v1")
    train = [t for t in dataset["train"]["text"] if t.strip()]
    val   = [t for t in dataset["validation"]["text"] if t.strip()]
    return train, val


# ── Registry — add new datasets here ─────────────────────────────────
DATASETS: dict[str, callable] = {
    "txt":         load_txt,
    "tinystories": load_tinystories,
    "wikitext":    load_wikitext,
}


def load(name: str) -> tuple[list[str], list[str]]:
    """
    Load a dataset by name.

    Args:
        name : dataset key from DATASETS (e.g. "txt", "tinystories")

    Returns:
        train_corpus, val_corpus — lists of text strings
    """
    if name not in DATASETS:
        raise ValueError(f"Unknown dataset {name!r}. Available: {list(DATASETS)}")
    return DATASETS[name]()
