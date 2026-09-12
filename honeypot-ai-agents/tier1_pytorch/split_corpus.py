import json
import os
import random

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
TRACES_DIR = os.path.join(DATA_DIR, "traces")
os.makedirs(TRACES_DIR, exist_ok=True)

with open(os.path.join(DATA_DIR, "train_normal.json"), "r") as f:
    raw_data = json.load(f)

# Extract only the padded arrays [MAX_SEQ_LEN]
all_padded = [item["padded"] for item in raw_data["sequences"]]
random.seed(42)
random.shuffle(all_padded)

# 80/20 train/val split
split_idx = int(len(all_padded) * 0.8)
train_windows = all_padded[:split_idx]
val_windows = all_padded[split_idx:]

with open(os.path.join(TRACES_DIR, "clean_windows_train.json"), "w") as f:
    json.dump(train_windows, f)

with open(os.path.join(TRACES_DIR, "clean_windows_val.json"), "w") as f:
    json.dump(val_windows, f)

print(f"Generated {len(train_windows)} train traces and {len(val_windows)} val traces in {TRACES_DIR}")