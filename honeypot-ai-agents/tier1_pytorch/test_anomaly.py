import os
import json
import torch
import torch.nn as nn
from model import TrajectoryAutoencoder

def evaluate_splits():
    device = torch.device("cpu")
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    CHECKPOINT_PATH = os.path.join(SCRIPT_DIR, "checkpoints", "autoencoder.pt")
    CONFIG_PATH = os.path.join(SCRIPT_DIR, "checkpoints", "config.json")
    EVAL_ATTACK_PATH = os.path.join(SCRIPT_DIR, "..", "data", "eval_anomalous.json")
    VAL_CLEAN_PATH = os.path.join(SCRIPT_DIR, "..", "data", "traces", "clean_windows_val.json")

    with open(CONFIG_PATH, "r") as f:
        threshold = json.load(f)["threshold"]

    model = TrajectoryAutoencoder().to(device)
    model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True))
    model.eval()

    criterion = nn.MSELoss(reduction='none')
    embed_dim = model.embedding.embedding_dim

    def score_sequence(seq):
        tensor_seq = torch.tensor([seq], dtype=torch.long).to(device)
        flattened, reconstructed = model(tensor_seq)
        non_pad_mask = (tensor_seq != 0).unsqueeze(-1).expand(-1, -1, embed_dim).reshape(1, -1).float()
        masked_loss = criterion(reconstructed, flattened) * non_pad_mask
        denom = non_pad_mask.sum(dim=1).clamp(min=1.0)
        return (masked_loss.sum(dim=1) / denom).item()

    # Test clean holdout
    with open(VAL_CLEAN_PATH, "r") as f:
        clean_traces = json.load(f)
    clean_blocked = sum(1 for seq in clean_traces if score_sequence(seq) > threshold)

    # Test attacks
    with open(EVAL_ATTACK_PATH, "r") as f:
        attack_data = json.load(f)
    attack_traces = [item["padded"] for item in attack_data["sequences"]]
    attacks_blocked = sum(1 for seq in attack_traces if score_sequence(seq) > threshold)

    print(f"\n--- EVALUATION BENCHMARK (Threshold: {threshold:.4f}) ---")
    print(f"Clean Holdout False Positive Rate: {clean_blocked / len(clean_traces) * 100:.2f}% ({clean_blocked}/{len(clean_traces)})")
    print(f"Attack Detection Rate (Recall):    {attacks_blocked / len(attack_traces) * 100:.2f}% ({attacks_blocked}/{len(attack_traces)})\n")

if __name__ == "__main__":
    evaluate_splits()