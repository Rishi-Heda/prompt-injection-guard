import os
import json
import torch
import torch.nn as nn
from model import TrajectoryAutoencoder

def run_test():
    device = torch.device("cpu")
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    CHECKPOINT_PATH = os.path.join(SCRIPT_DIR, "checkpoints", "autoencoder.pt")
    CONFIG_PATH = os.path.join(SCRIPT_DIR, "checkpoints", "config.json")

    with open(CONFIG_PATH, "r") as f:
        threshold = json.load(f)["threshold"]

    model = TrajectoryAutoencoder().to(device)
    model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True))
    model.eval()
    criterion = nn.MSELoss(reduction='none')

    embed_dim = model.embedding.embedding_dim

    clean_sequence = [0, 0, 5, 1, 2]
    attack_sequence = [0, 3, 3, 4, 4]

    print(f"\n--- ACTIVE THRESHOLD: {threshold:.4f} ---\n")

    with torch.no_grad():
        for name, seq in [("CLEAN BEHAVIOR", clean_sequence), ("HIJACKED BEHAVIOR", attack_sequence)]:
            tensor_seq = torch.tensor([seq], dtype=torch.long).to(device)
            flattened, reconstructed = model(tensor_seq)

            # Same masked, per-sample scoring used in train.py / calibrate_threshold.py
            non_pad_mask = (tensor_seq != 0).unsqueeze(-1).expand(-1, -1, embed_dim)
            non_pad_mask = non_pad_mask.reshape(tensor_seq.size(0), -1).float()

            elementwise_loss = criterion(reconstructed, flattened)
            masked_loss = elementwise_loss * non_pad_mask
            per_sample_denom = non_pad_mask.sum(dim=1).clamp(min=1.0)
            score = (masked_loss.sum(dim=1) / per_sample_denom).item()

            status = "🔴 BLOCKED (ANOMALY)" if score > threshold else "🟢 ALLOWED (CLEAN)"
            print(f"[{name}] Sequence {seq}")
            print(f"Reconstruction Loss: {score:.4f} -> {status}\n")

if __name__ == "__main__":
    run_test()