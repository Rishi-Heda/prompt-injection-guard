import json
import torch
from torch.utils.data import Dataset, DataLoader

class TrajectoryDataset(Dataset):
    def __init__(self, json_path):
        with open(json_path, 'r') as f:
            raw = json.load(f)
            
        # Handle dict format with "sequences" metadata wrapper
        if isinstance(raw, dict) and "sequences" in raw:
            self.data = [item["padded"] for item in raw["sequences"]]
        # Handle flat list of lists: [[0, 1, 2], ...]
        elif isinstance(raw, list):
            self.data = raw
        else:
            raise ValueError(f"Unrecognized data format in {json_path}")
            
    def __len__(self):
        return len(self.data)
        
    def __getitem__(self, idx):
        return torch.tensor(self.data[idx], dtype=torch.long)

def get_dataloader(json_path, batch_size=64, shuffle=True):
    dataset = TrajectoryDataset(json_path)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)