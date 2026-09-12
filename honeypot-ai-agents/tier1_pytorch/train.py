import os
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from dataset import get_dataloader
from model import TrajectoryAutoencoder

torch.manual_seed(42)
random.seed(42)
np.random.seed(42)

def train_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device}")

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_PATH = os.path.join(SCRIPT_DIR, "..", "data", "traces", "clean_windows_train.json")
    CHECKPOINT_DIR = os.path.join(SCRIPT_DIR, "checkpoints")
    CHECKPOINT_PATH = os.path.join(CHECKPOINT_DIR, "autoencoder.pt")
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    epochs = 200
    batch_size = 128
    dataloader = get_dataloader(DATA_PATH, batch_size=batch_size, shuffle=True)
    
    # window_size=12, tighter latent_dim=2 to prevent over-memorization
    model = TrajectoryAutoencoder(vocab_size=8, embed_dim=8, window_size=12, latent_dim=2).to(device)

    optimizer = optim.Adam(model.parameters(), lr=0.001)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=50, gamma=0.5)
    criterion = nn.MSELoss(reduction='none')

    embed_dim = model.embedding.embedding_dim
    model.train()
    best_loss = float('inf')

    for epoch in range(epochs):
        total_loss = 0.0
        
        for batch in dataloader:
            batch = batch.to(device)
            optimizer.zero_grad()

            original_flattened, reconstructed = model(batch)

            # Strict mask: only compute loss on non-zero (non-PAD) token embeddings
            non_pad_mask = (batch != 0).unsqueeze(-1).expand(-1, -1, embed_dim).reshape(batch.size(0), -1).float()

            elementwise_loss = criterion(reconstructed, original_flattened)
            masked_loss = elementwise_loss * non_pad_mask

            # Normalize exclusively by active elements
            active_elements = non_pad_mask.sum().clamp(min=1.0)
            loss = masked_loss.sum() / active_elements

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            total_loss += loss.item()

        avg_loss = total_loss / len(dataloader)
        scheduler.step()

        if (epoch + 1) % 10 == 0 or epoch == epochs - 1:
            print(f"Epoch {epoch+1:03d}/{epochs} | Loss: {avg_loss:.4f} | LR: {scheduler.get_last_lr()[0]:.5f}")

        if avg_loss < best_loss:
            best_loss = avg_loss
            torch.save(model.state_dict(), CHECKPOINT_PATH)

        # Early stop when convergence reaches the desired nonzero sweet spot
        if avg_loss <= 0.0030:
            print(f"\nTarget convergence reached at epoch {epoch+1} (Loss: {avg_loss:.4f}). Stopping early to retain anomaly sensitivity.")
            torch.save(model.state_dict(), CHECKPOINT_PATH)
            break

    print(f"Training complete. Best loss: {best_loss:.4f}. Weights saved to {CHECKPOINT_PATH}")

if __name__ == "__main__":
    train_model()