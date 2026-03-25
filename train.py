"""
train.py — Training loop
-------------------------
Trains the SLM to predict the next token at each position.

Loss: cross-entropy between predicted logits and target token IDs
      (standard language modelling objective)

Each step:
  1. Forward pass  → logits (batch, seq_len, vocab_size)
  2. Compute loss  → cross-entropy vs target (batch, seq_len)
  3. Backward pass → gradients
  4. Optimizer step → update weights
  5. Zero gradients
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from model import SLM
from config import ModelConfig


def train(
    model: SLM,
    train_loader: DataLoader,
    val_loader: DataLoader,
    config: ModelConfig,
) -> None:
    """
    Run the full training loop for config.epochs epochs,
    printing train and validation loss after each epoch.

    Args:
        model        : SLM instance (untrained)
        train_loader : DataLoader for training data
        val_loader   : DataLoader for validation data
        config       : ModelConfig (reads epochs, learning_rate)
    """
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    loss_fn   = nn.CrossEntropyLoss()

    for epoch in range(1, config.epochs + 1):
        model.train()
        total_loss = 0.0

        for inputs, targets in train_loader:
            inputs  = inputs.to(config.device)
            targets = targets.to(config.device)
            logits  = model(inputs)
            loss    = loss_fn(
                logits.view(-1, logits.size(-1)),
                targets.view(-1),
            )
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        train_loss = total_loss / len(train_loader)
        val_loss   = evaluate(model, val_loader)
        print(f"Epoch {epoch:>3}/{config.epochs}  train: {train_loss:.4f}  val: {val_loss:.4f}")


def evaluate(
    model: SLM,
    dataloader: DataLoader,
) -> float:
    """
    Compute average cross-entropy loss over the dataloader
    without updating weights (model.eval(), no_grad).

    Args:
        model      : trained SLM
        dataloader : validation DataLoader

    Returns:
        Average loss as a float
    """
    loss_fn = nn.CrossEntropyLoss()
    model.eval()
    total_loss = 0.0

    device = next(model.parameters()).device
    with torch.no_grad():
        for inputs, targets in dataloader:
            inputs  = inputs.to(device)
            targets = targets.to(device)
            logits  = model(inputs)
            loss   = loss_fn(
                logits.view(-1, logits.size(-1)),
                targets.view(-1),
            )
            total_loss += loss.item()

    return total_loss / len(dataloader)
