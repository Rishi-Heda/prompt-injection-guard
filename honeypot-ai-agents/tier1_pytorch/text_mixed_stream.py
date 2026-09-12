import os
import json
import random
import torch
import torch.nn as nn
from model import TrajectoryAutoencoder

def evaluate_mixed_stream():
    device = torch.device("cpu")
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    CHECKPOINT_PATH = os.path.join(SCRIPT_DIR, "checkpoints", "autoencoder.pt")
    CONFIG_PATH = os.path.join(SCRIPT_DIR, "checkpoints", "config.json")
    VAL_CLEAN_PATH = os.path.join(SCRIPT_DIR, "..", "data", "traces", "clean_windows_val.json")
    EVAL_ATTACK_PATH = os.path.join(SCRIPT_DIR, "..", "data", "eval_anomalous.json")

    with open(CONFIG_PATH, "r") as f:
        threshold = json.load(f)["threshold"]

    model = TrajectoryAutoencoder().to(device)
    model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True))
    model.eval()

    criterion = nn.MSELoss(reduction='none')
    embed_dim = model.embedding.embedding_dim

    # Load data
    with open(VAL_CLEAN_PATH, "r") as f:
        clean_traces = json.load(f)
    
    with open(EVAL_ATTACK_PATH, "r") as f:
        attack_data = json.load(f)
        attack_traces = [item["padded"] for item in attack_data["sequences"]]

    # Build a combined, randomized stream (e.g., 1000 clean, 1000 attacks)
    stream = []
    for seq in clean_traces[:1000]:
        stream.append({"sequence": seq, "true_label": 0}) # 0 = Benign
    for seq in attack_traces[:1000]:
        stream.append({"sequence": seq, "true_label": 1}) # 1 = Attack

    random.seed(42)
    random.shuffle(stream)

    tp = fp = tn = fn = 0

    print(f"Streaming {len(stream)} mixed requests through Tier 1 Sentinel (Threshold: {threshold:.4f})...")

    with torch.no_grad():
        for item in stream:
            seq = item["sequence"]
            is_attack = item["true_label"]

            tensor_seq = torch.tensor([seq], dtype=torch.long).to(device)
            flattened, reconstructed = model(tensor_seq)
            
            non_pad_mask = (tensor_seq != 0).unsqueeze(-1).expand(-1, -1, embed_dim).reshape(1, -1).float()
            masked_loss = criterion(reconstructed, flattened) * non_pad_mask
            denom = non_pad_mask.sum(dim=1).clamp(min=1.0)
            score = (masked_loss.sum(dim=1) / denom).item()

            # Prediction: 1 if score > threshold (Block), 0 if safe (Allow)
            pred = 1 if score > threshold else 0

            if is_attack == 1 and pred == 1:
                tp += 1
            elif is_attack == 0 and pred == 1:
                fp += 1
            elif is_attack == 0 and pred == 0:
                tn += 1
            elif is_attack == 1 and pred == 0:
                fn += 1

    # Metrics
    accuracy = (tp + tn) / len(stream) * 100
    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 100.0
    recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0.0
    fpr = fp / (tn + fp) * 100 if (tn + fp) > 0 else 0.0

    print("\n--- LIVE STREAM CONFUSION MATRIX ---")
    print(f"Total Evaluated Packets: {len(stream)}")
    print(f"True Positives (Attacks Blocked):  {tp}")
    print(f"False Positives (Clean Blocked):   {fp} (FPR: {fpr:.2f}%)")
    print(f"True Negatives (Clean Passed):     {tn}")
    print(f"False Negatives (Attacks Missed):  {fn}")
    print("-" * 35)
    print(f"Overall Accuracy:  {accuracy:.2f}%")
    print(f"Precision:         {precision:.2f}%")
    print(f"Recall (Sensitivity): {recall:.2f}%\n")

if __name__ == "__main__":
    evaluate_mixed_stream()