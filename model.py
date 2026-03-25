"""
model.py — Small Language Model architecture
---------------------------------------------
Stack of transformer blocks, each containing:

  Token IDs
      ↓
  InputEmbedding   — lookup table (vocab_size × embed_dim)
  PositionalEncoding — adds position information to each vector
      ↓  (repeated num_layers times)
  MultiHeadAttention — each token attends to all previous tokens
  FeedForward        — position-wise MLP applied to each token
  LayerNorm + Dropout
      ↓
  OutputProjection — (embed_dim → vocab_size) logits over next token
"""

import torch
import torch.nn as nn
from config import ModelConfig


class InputEmbedding(nn.Module):
    """
    Lookup table: token ID → embed_dim vector.
    Shape: (vocab_size, embed_dim)
    """

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.embedding = nn.Embedding(config.vocab_size, config.embed_dim)

    def forward(self, token_ids: torch.Tensor) -> torch.Tensor:
        """
        Args:
            token_ids : (batch, seq_len)  integer tensor
        Returns:
            (batch, seq_len, embed_dim)   float tensor
        """
        return self.embedding(token_ids)


class PositionalEncoding(nn.Module):
    """
    Adds a fixed or learned position vector to each token embedding
    so the model knows the order of tokens in the sequence.
    """

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()

        # build position encoding matrix once — shape (max_seq_len, embed_dim)
        pe = torch.zeros(config.max_seq_len, config.embed_dim)
        positions = torch.arange(config.max_seq_len).unsqueeze(1)          # (seq_len, 1)
        divisor   = 10000 ** (torch.arange(0, config.embed_dim, 2) / config.embed_dim)

        pe[:, 0::2] = torch.sin(positions / divisor)   # even dims
        pe[:, 1::2] = torch.cos(positions / divisor)   # odd dims

        # register as buffer — saved with model but not a trainable parameter
        self.register_buffer("pe", pe.unsqueeze(0))    # (1, seq_len, embed_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x : (batch, seq_len, embed_dim)
        Returns:
            (batch, seq_len, embed_dim)  — embeddings + position signal
        """
        return x + self.pe[:, :x.size(1)]


class MultiHeadAttention(nn.Module):
    """
    Splits embed_dim into num_heads separate attention heads.
    Each head learns to attend to different aspects of context.
    Uses causal masking so token i can only attend to tokens 0..i.
    """

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.num_heads = config.num_heads
        self.head_dim  = config.embed_dim // config.num_heads

        # single matrix for Q, K, V projections combined (3x for efficiency)
        self.qkv_proj = nn.Linear(config.embed_dim, 3 * config.embed_dim, bias=False)
        self.out_proj  = nn.Linear(config.embed_dim, config.embed_dim, bias=False)
        self.dropout   = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x : (batch, seq_len, embed_dim)
        Returns:
            (batch, seq_len, embed_dim)
        """
        batch, seq_len, embed_dim = x.shape

        # project x to Q, K, V — shape: (batch, seq_len, 3 * embed_dim)
        qkv = self.qkv_proj(x)
        q, k, v = qkv.split(embed_dim, dim=-1)   # each: (batch, seq_len, embed_dim)

        # reshape into heads — (batch, num_heads, seq_len, head_dim)
        q = q.view(batch, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        k = k.view(batch, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        v = v.view(batch, seq_len, self.num_heads, self.head_dim).transpose(1, 2)

        # attention scores — (batch, num_heads, seq_len, seq_len)
        scale  = self.head_dim ** -0.5
        scores = (q @ k.transpose(-2, -1)) * scale

        # causal mask — token i cannot attend to tokens after position i
        mask   = torch.triu(torch.ones(seq_len, seq_len, device=x.device), diagonal=1).bool()
        scores = scores.masked_fill(mask, float("-inf"))

        weights = self.dropout(torch.softmax(scores, dim=-1))

        # weighted sum of values — (batch, num_heads, seq_len, head_dim)
        out = weights @ v

        # merge heads back — (batch, seq_len, embed_dim)
        out = out.transpose(1, 2).contiguous().view(batch, seq_len, embed_dim)
        return self.out_proj(out)


class FeedForward(nn.Module):
    """
    Two-layer MLP applied independently to each token position:
        embed_dim → ffn_dim → embed_dim
    Adds capacity for the model to transform representations.
    """

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(config.embed_dim, config.ffn_dim),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.ffn_dim, config.embed_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x : (batch, seq_len, embed_dim)
        Returns:
            (batch, seq_len, embed_dim)
        """
        return self.net(x)


class TransformerBlock(nn.Module):
    """
    One transformer layer:
        x = x + Attention(LayerNorm(x))
        x = x + FeedForward(LayerNorm(x))
    """

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.norm1     = nn.LayerNorm(config.embed_dim)
        self.attention = MultiHeadAttention(config)
        self.norm2     = nn.LayerNorm(config.embed_dim)
        self.ff        = FeedForward(config)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x : (batch, seq_len, embed_dim)
        Returns:
            (batch, seq_len, embed_dim)
        """
        x = x + self.attention(self.norm1(x))   # residual around attention
        x = x + self.ff(self.norm2(x))           # residual around feedforward
        return x


class SLM(nn.Module):
    """
    Small Language Model — full architecture.

    Forward pass:
        token_ids → InputEmbedding → PositionalEncoding
                  → TransformerBlock × num_layers
                  → LayerNorm → Linear(embed_dim, vocab_size)
                  → logits   (batch, seq_len, vocab_size)

    The logits at position i represent the model's prediction for
    the token that comes after position i.
    """

    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.embedding = InputEmbedding(config)
        self.position  = PositionalEncoding(config)
        self.blocks    = nn.Sequential(*[TransformerBlock(config) for _ in range(config.num_layers)])
        self.norm      = nn.LayerNorm(config.embed_dim)
        self.head      = nn.Linear(config.embed_dim, config.vocab_size, bias=False)

    def forward(self, token_ids: torch.Tensor) -> torch.Tensor:
        """
        Args:
            token_ids : (batch, seq_len)
        Returns:
            logits    : (batch, seq_len, vocab_size)
        """
        x = self.embedding(token_ids)   # (batch, seq_len, embed_dim)
        x = self.position(x)            # (batch, seq_len, embed_dim)
        x = self.blocks(x)              # (batch, seq_len, embed_dim)
        x = self.norm(x)                # (batch, seq_len, embed_dim)
        return self.head(x)             # (batch, seq_len, vocab_size)

    def count_parameters(self) -> int:
        """Return total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
