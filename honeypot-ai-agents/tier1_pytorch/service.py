import os
import json
import torch
import torch.nn as nn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
from tier1_pytorch.model import TrajectoryAutoencoder

app = FastAPI(
    title="Sentinel Tier 1 Trajectory Firewall",
    description="Sub-15ms behavioral anomaly detection for LLM agent tool sequences.",
    version="1.0.0"
)

# Configuration & Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKPOINT_PATH = os.path.join(SCRIPT_DIR, "checkpoints", "autoencoder.pt")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "checkpoints", "config.json")

MAX_SEQ_LEN = 12
VOCAB_SIZE = 8
EMBED_DIM = 8
LATENT_DIM = 2

# Global runtime state
device = torch.device("cpu")
model = None
threshold = 0.0060
criterion = nn.MSELoss(reduction='none')


class TrajectoryRequest(BaseModel):
    sequence: List[int] = Field(
        ..., 
        description="Tool ID trajectory sequence (e.g. [1, 5, 2])",
        example=[1, 5, 2]
    )


class TrajectoryResponse(BaseModel):
    anomaly_score: float
    threshold: float
    decision: str  # "ALLOW", "BLOCK", or "ESCALATE_TIER2"
    escalate_to_tier2: bool
    latency_note: str


@app.on_event("startup")
def load_model_and_config():
    global model, threshold

    if not os.path.exists(CHECKPOINT_PATH):
        raise RuntimeError(f"Checkpoint not found at {CHECKPOINT_PATH}")

    if not os.path.exists(CONFIG_PATH):
        raise RuntimeError(f"Config not found at {CONFIG_PATH}")

    # Load calibrated threshold
    with open(CONFIG_PATH, "r") as f:
        config_data = json.load(f)
        threshold = float(config_data.get("threshold", 0.0060))

    # Load Model
    model = TrajectoryAutoencoder(
        vocab_size=VOCAB_SIZE,
        embed_dim=EMBED_DIM,
        window_size=MAX_SEQ_LEN,
        latent_dim=LATENT_DIM
    ).to(device)

    model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True))
    model.eval()
    print(f"[*] Tier 1 Model loaded successfully. Active threshold: {threshold:.4f}")


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "calibrated_threshold": threshold
    }


@app.post("/evaluate", response_model=TrajectoryResponse)
def evaluate_trajectory(payload: TrajectoryRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded.")

    seq = payload.sequence
    if not seq:
        raise HTTPException(status_code=400, detail="Sequence cannot be empty.")

    # Slice or pad sequence to MAX_SEQ_LEN
    padded_seq = seq[:MAX_SEQ_LEN]
    padded_seq = padded_seq + [0] * (MAX_SEQ_LEN - len(padded_seq))

    tensor_input = torch.tensor([padded_seq], dtype=torch.long).to(device)

    with torch.no_grad():
        flattened, reconstructed = model(tensor_input)

        # Build mask for non-padded elements (ID != 0)
        non_pad_mask = (tensor_input != 0).unsqueeze(-1).expand(-1, -1, EMBED_DIM).reshape(1, -1).float()
        
        elementwise_loss = criterion(reconstructed, flattened)
        masked_loss = elementwise_loss * non_pad_mask
        denom = non_pad_mask.sum(dim=1).clamp(min=1.0)
        
        anomaly_score = float((masked_loss.sum(dim=1) / denom).item())

    # Tier 2 Gray Zone: Scores sitting just below the cutoff (70% - 100% of threshold)
    gray_zone_lower = threshold * 0.70

    if anomaly_score > threshold:
        decision = "BLOCK"
        escalate = False
    elif anomaly_score >= gray_zone_lower:
        decision = "ESCALATE_TIER2"
        escalate = True
    else:
        decision = "ALLOW"
        escalate = False

    return TrajectoryResponse(
        anomaly_score=round(anomaly_score, 6),
        threshold=round(threshold, 6),
        decision=decision,
        escalate_to_tier2=escalate,
        latency_note="Sub-15ms local inference"
    )