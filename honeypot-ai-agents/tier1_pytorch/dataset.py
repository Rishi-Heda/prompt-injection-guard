import json
import torch
from torch.utils.data import Dataset, DataLoader

class TrajectoryDataset(Dataset):
    def __init__(self, json_path):
        with open(json_path, 'r') as f:
            # Expecting a list of arrays like [[0, 0, 1, 2, 4], [0, 1, 2, 2, 1]]
            self.data = json.load(f)
            
    def __len__(self):
        return len(self.data)
        
    def __getitem__(self, idx):
        return torch.tensor(self.data[idx], dtype=torch.long)

def get_dataloader(json_path, batch_size=64):
    dataset = TrajectoryDataset(json_path)
    return DataLoader(dataset, batch_size=batch_size, shuffle=True)