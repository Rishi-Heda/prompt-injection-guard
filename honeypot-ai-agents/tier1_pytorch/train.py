import torch
torch.manual_seed(42)
import random
random.seed(42)
import numpy as np
np.random.seed(42)
import torch.nn as nn
import torch.optim as optim
import os
from dataset import get_dataloader
from model import TrajectoryAutoencoder

def train_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device}")

    epochs = 2000
    dataloader = get_dataloader("../data/traces/clean_windows_train.json", batch_size=128)
    model = TrajectoryAutoencoder().to(device)

    optimizer = optim.Adam(model.parameters(), lr=0.001)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=500, gamma=0.5)
    criterion = nn.MSELoss(reduction='none')

    embed_dim = model.embedding.embedding_dim
    model.train()

    best_loss = float('inf')

    for epoch in range(epochs):
        total_loss = 0
        for batch in dataloader:
            batch = batch.to(device)  # [B, window_size] token IDs
            optimizer.zero_grad()

            original_flattened, reconstructed = model(batch)

            # Mask out PAD (id 0) positions
            non_pad_mask = (batch != 0).unsqueeze(-1).expand(-1, -1, embed_dim)
            non_pad_mask = non_pad_mask.reshape(batch.size(0), -1).float()  # [B, input_dim]

            elementwise_loss = criterion(reconstructed, original_flattened)  # [B, input_dim]
            masked_loss = elementwise_loss * non_pad_mask

            # Per-sample normalization: each sample's own mean over its real tokens,
            # THEN averaged across the batch. Prevents short/long-trajectory batches
            # from skewing the loss unevenly.
            per_sample_denom = non_pad_mask.sum(dim=1).clamp(min=1.0)     # [B]
            per_sample_loss = masked_loss.sum(dim=1) / per_sample_denom  # [B]
            loss = per_sample_loss.mean()

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()

            total_loss += loss.item()

        avg_loss = total_loss / len(dataloader)
        scheduler.step()
        print(f"Epoch {epoch+1}/{epochs} | Loss: {avg_loss:.4f} | LR: {scheduler.get_last_lr()[0]:.5f}")

        if avg_loss < best_loss:
            best_loss = avg_loss
            os.makedirs("checkpoints", exist_ok=True)
            torch.save(model.state_dict(), "checkpoints/autoencoder.pt")

    print(f"Training complete. Best loss: {best_loss:.4f}. Weights saved to checkpoints/autoencoder.pt")

if __name__ == "__main__":
    train_model()