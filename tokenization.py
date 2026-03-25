"""
tokenization.py — BPE tokenizer training + encoding
-----------------------------------------------------
Trains BPE on train.txt, encodes both train.txt and val.txt,
and caches everything to disk for subsequent runs.
"""

import json
from pathlib import Path

from bpe_tokenizer import BPETokenizer
from config import ModelConfig


DATA_DIR       = Path(__file__).parent / "data_files"
TRAIN_FILE     = DATA_DIR / "train.txt"
VAL_FILE       = DATA_DIR / "val.txt"
TOKENIZER_FILE = DATA_DIR / "tokenizer.json"
TRAIN_IDS_FILE = DATA_DIR / "train_tokens.json"
VAL_IDS_FILE   = DATA_DIR / "val_tokens.json"


def build_tokenizer(config: ModelConfig) -> tuple[BPETokenizer, list[int], list[int]]:
    """
    Return a trained BPETokenizer, train token IDs, and val token IDs.

    - Tokenizer is trained on train.txt only
    - Both splits are encoded with the same tokenizer
    - All outputs are cached on disk; reloaded on subsequent runs

    Returns:
        tokenizer : trained BPETokenizer
        train_ids : flat list of token IDs for train.txt
        val_ids   : flat list of token IDs for val.txt
    """
    with open(TRAIN_FILE) as f:
        train_corpus = [line.strip() for line in f if line.strip()]
    with open(VAL_FILE) as f:
        val_corpus = [line.strip() for line in f if line.strip()]

    if TOKENIZER_FILE.exists():
        tokenizer = BPETokenizer.load(str(TOKENIZER_FILE))
    else:
        tokenizer = BPETokenizer()
        tokenizer.train(train_corpus, vocab_size=config.vocab_size, verbose=False)
        tokenizer.save(str(TOKENIZER_FILE))

    if TRAIN_IDS_FILE.exists():
        train_ids: list[int] = json.loads(TRAIN_IDS_FILE.read_text())
    else:
        train_ids = []
        for sentence in train_corpus:
            train_ids.extend(tokenizer.encode(sentence))
        TRAIN_IDS_FILE.write_text(json.dumps(train_ids))

    if VAL_IDS_FILE.exists():
        val_ids: list[int] = json.loads(VAL_IDS_FILE.read_text())
    else:
        val_ids = []
        for sentence in val_corpus:
            val_ids.extend(tokenizer.encode(sentence))
        VAL_IDS_FILE.write_text(json.dumps(val_ids))

    return tokenizer, train_ids, val_ids
