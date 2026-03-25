"""
tokenization.py — BPE tokenizer training
-----------------------------------------
Trains BPE on the training corpus and returns the tokenizer
along with raw corpus text for downstream encoding.
"""

import json
from pathlib import Path

from bpe_tokenizer import BPETokenizer
from config import ModelConfig
import dataset_registry


DATA_DIR       = Path(__file__).parent / "data_files"
TOKENIZER_FILE = DATA_DIR / "tokenizer.json"


def build_tokenizer(
    config: ModelConfig,
) -> tuple[BPETokenizer, list[str], list[str]]:
    """
    Return a trained BPETokenizer and raw train/val corpus.

    - Tokenizer trained on train corpus only, cached to tokenizer.json
    - Returns raw text so data.py decides how to encode (cached vs streaming)

    Returns:
        tokenizer    : trained BPETokenizer
        train_corpus : list of training text strings
        val_corpus   : list of validation text strings
    """
    train_corpus, val_corpus = dataset_registry.load(config.data_source)

    if TOKENIZER_FILE.exists():
        tokenizer = BPETokenizer.load(str(TOKENIZER_FILE))
    else:
        tokenizer = BPETokenizer()
        tokenizer.train(train_corpus, vocab_size=config.vocab_size, verbose=False)
        tokenizer.save(str(TOKENIZER_FILE))

    return tokenizer, train_corpus, val_corpus
