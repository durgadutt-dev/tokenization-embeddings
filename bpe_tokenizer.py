"""
Byte Pair Encoding (BPE) Tokenizer — built from scratch
---------------------------------------------------------
Algorithm:
  1. Split corpus into words; represent each word as characters + </w> marker
  2. Count frequency of every adjacent pair across the corpus
  3. Merge the most frequent pair into a single new token
  4. Repeat until the vocabulary reaches the target size

Special tokens are registered before BPE training and are never split.
Text is split on special tokens first, then BPE is applied to each piece.

The learned merge rules are then applied in the same order to encode new text.
"""

import json
import re
from collections import Counter
from pathlib import Path


# Default special tokens — registered at fixed IDs before BPE vocab is built.
# Add or change tokens here to support different dataset formats.
DEFAULT_SPECIAL_TOKENS: dict[str, int] = {
    "<|unk|>":       0,   # unknown token fallback
    "<|pad|>":       1,   # padding shorter sequences to same length
    "<|bos|>":       2,   # beginning of sequence
    "<|eos|>":       3,   # end of sequence
    "<|endoftext|>": 4,   # document / story boundary (used by TinyStories)
}


class BPETokenizer:

    def __init__(self, special_tokens: dict[str, int] = DEFAULT_SPECIAL_TOKENS):
        self.special_tokens: dict[str, int] = special_tokens
        self.vocab: dict[str, int] = {}       # token string → id
        self.id_to_token: dict[int, str] = {} # id → token string
        self.merges: list[tuple[str, str]] = []  # ordered merge rules
        self._word_freq: Counter = Counter()

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, texts: list[str], vocab_size: int = 500,
              verbose: bool = True) -> None:
        """
        Build the BPE vocabulary from a list of text strings.
        Special tokens are added first at fixed IDs; BPE fills the rest.

        Args:
            texts      : raw text corpus (list of sentences / documents)
            vocab_size : target vocabulary size (special tokens + chars + merges)
            verbose    : print each merge step
        """
        # Step 1 — reserve special token IDs at the front of the vocab
        self.vocab = dict(self.special_tokens)

        # Step 2 — count word frequencies (special tokens excluded)
        self._word_freq = self._count_word_frequencies(texts)

        # Step 3 — represent every word as a list of characters + </w>
        word_tokens: dict[str, list[str]] = {
            word: list(word) + ["</w>"]
            for word in self._word_freq
        }

        # Step 4 — add all unique characters to vocab after special tokens
        initial_chars: set[str] = set()
        for tokens in word_tokens.values():
            initial_chars.update(tokens)

        next_id = max(self.vocab.values()) + 1
        for ch in sorted(initial_chars):
            if ch not in self.vocab:
                self.vocab[ch] = next_id
                next_id += 1

        if verbose:
            print(f"  Special tokens         : {len(self.special_tokens)}")
            print(f"  Corpus words (unique)  : {len(self._word_freq)}")
            print(f"  Initial vocab (chars)  : {len(self.vocab)}")
            print(f"  Target vocab size      : {vocab_size}")
            print(f"  Merges to perform      : {vocab_size - len(self.vocab)}")
            print()
            print(f"  {'Step':<6}  {'Pair':<30}  {'Freq':>6}  {'Vocab':>6}")
            print(f"  {'-'*6}  {'-'*30}  {'-'*6}  {'-'*6}")

        # Step 5 — BPE merge loop
        n_merges = vocab_size - len(self.vocab)
        for step in range(n_merges):
            pair_freq = self._count_pairs(word_tokens)
            if not pair_freq:
                break

            best = max(pair_freq, key=pair_freq.get)
            freq = pair_freq[best]
            merged = best[0] + best[1]

            self.merges.append(best)
            self.vocab[merged] = len(self.vocab)
            word_tokens = self._apply_merge(best, word_tokens)

            if verbose and (step < 30 or step % 50 == 0):
                pair_str = f"{best[0]!r} + {best[1]!r} → {merged!r}"
                print(f"  {step+1:<6}  {pair_str:<30}  {freq:>6}  {len(self.vocab):>6}")

        self.id_to_token = {v: k for k, v in self.vocab.items()}

        if verbose:
            print(f"\n  Final vocab size: {len(self.vocab)}")

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """
        Write vocab, merge rules, and special tokens to a JSON file on disk.

        Args:
            path : file path to save to (e.g. "tokenizer.json")
        """
        data = {
            "special_tokens": self.special_tokens,
            "vocab": self.vocab,
            "merges": self.merges,
        }
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, path: str) -> "BPETokenizer":
        """
        Load a previously saved tokenizer from disk — no retraining needed.

        Args:
            path : file path saved by save() (e.g. "tokenizer.json")

        Returns:
            BPETokenizer with special tokens, vocab, and merges restored
        """
        data = json.loads(Path(path).read_text())
        tokenizer = cls(special_tokens=data["special_tokens"])
        tokenizer.vocab = data["vocab"]
        tokenizer.merges = [tuple(pair) for pair in data["merges"]]
        tokenizer.id_to_token = {v: k for k, v in tokenizer.vocab.items()}
        return tokenizer

    # ------------------------------------------------------------------
    # Encoding / Decoding
    # ------------------------------------------------------------------

    def encode(self, text: str) -> list[int]:
        """
        Text → list of token IDs.
        Special tokens are preserved as single tokens; BPE is applied to
        the remaining pieces.
        """
        # build a regex that matches any special token literally
        special_pattern = "(" + "|".join(
            re.escape(tok) for tok in sorted(self.special_tokens, key=len, reverse=True)
        ) + ")"

        ids: list[int] = []
        for piece in re.split(special_pattern, text):
            if piece in self.special_tokens:
                ids.append(self.special_tokens[piece])
            else:
                for word in re.findall(r"\w+", piece.lower()):
                    ids.extend(self._encode_word(word))
        return ids

    def tokenize(self, text: str) -> list[str]:
        """Text → list of token strings (readable form of encode)."""
        return [self.id_to_token[i] for i in self.encode(text)]

    def decode(self, ids: list[int]) -> str:
        """Token IDs → reconstructed text (approximate)."""
        tokens = [self.id_to_token.get(i, "<|unk|>") for i in ids]
        return "".join(tokens).replace("</w>", " ").strip()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_word_frequencies(texts: list[str]) -> Counter:
        freq: Counter = Counter()
        for text in texts:
            for word in re.findall(r"\w+", text.lower()):
                freq[word] += 1
        return freq

    def _count_pairs(
        self, word_tokens: dict[str, list[str]]
    ) -> Counter:
        pairs: Counter = Counter()
        for word, tokens in word_tokens.items():
            freq = self._word_freq[word]
            for a, b in zip(tokens, tokens[1:]):
                pairs[(a, b)] += freq
        return pairs

    @staticmethod
    def _apply_merge(
        pair: tuple[str, str], word_tokens: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        a, b = pair
        merged = a + b
        result = {}
        for word, tokens in word_tokens.items():
            new: list[str] = []
            i = 0
            while i < len(tokens):
                if i < len(tokens) - 1 and tokens[i] == a and tokens[i + 1] == b:
                    new.append(merged)
                    i += 2
                else:
                    new.append(tokens[i])
                    i += 1
            result[word] = new
        return result

    def _encode_word(self, word: str) -> list[int]:
        tokens = list(word) + ["</w>"]
        for pair in self.merges:
            a, b = pair
            new: list[str] = []
            i = 0
            while i < len(tokens):
                if i < len(tokens) - 1 and tokens[i] == a and tokens[i + 1] == b:
                    new.append(a + b)
                    i += 2
                else:
                    new.append(tokens[i])
                    i += 1
            tokens = new
        unk_id = self.special_tokens.get("<|unk|>", 0)
        return [self.vocab.get(t, unk_id) for t in tokens]
