import os
import json
import numpy as np
import torch
import torch.nn as nn
from dataset import get_dataloader
from model import TrajectoryAutoencoder

def calibrate():
    device = torch.device("cpu")
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    CHECKPOINT_PATH = os.path.join(SCRIPT_DIR, "checkpoints", "autoencoder.pt")
    DATA_PATH = os.path.join(SCRIPT_DIR, "..", "data", "traces", "clean_windows_val.json")
    CONFIG_PATH = os.path.join(SCRIPT_DIR, "checkpoints", "config.json")

    model = TrajectoryAutoencoder().to(device)
    model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True))
    model.eval()

    dataloader = get_dataloader(DATA_PATH, batch_size=1)
    embed_dim = model.embedding.embedding_dim
    losses = []
    criterion = nn.MSELoss(reduction='none')

    print("Running inference on held-out clean validation data...")
    with torch.no_grad():
        for batch in dataloader:
            batch = batch.to(device)
            flattened, reconstructed = model(batch)

            non_pad_mask = (batch != 0).unsqueeze(-1).expand(-1, -1, embed_dim)
            non_pad_mask = non_pad_mask.reshape(batch.size(0), -1).float()

            elementwise_loss = criterion(reconstructed, flattened)
            masked_loss = elementwise_loss * non_pad_mask

            per_sample_denom = non_pad_mask.sum(dim=1).clamp(min=1.0)
            per_sample_loss = masked_loss.sum(dim=1) / per_sample_denom
            losses.append(per_sample_loss.item())

    # 99th percentile + safety buffer
    threshold = float(np.percentile(losses, 99) + 0.001)

    print(f"Max Clean Loss: {max(losses):.4f}")
    print(f"Mean Clean Loss: {np.mean(losses):.4f}")
    print(f"--- RECOMMENDED THRESHOLD (99th Percentile + Buffer): {threshold:.4f} ---")

    with open(CONFIG_PATH, "w") as f:
        json.dump({"threshold": threshold}, f, indent=2)
    print(f"Threshold saved to {CONFIG_PATH}")

if __name__ == "__main__":
    calibrate()