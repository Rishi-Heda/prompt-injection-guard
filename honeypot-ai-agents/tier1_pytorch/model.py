import torch
import torch.nn as nn

class TrajectoryAutoencoder(nn.Module):
    def __init__(self, vocab_size=8, embed_dim=8, window_size=12, latent_dim=2):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        
        input_dim = window_size * embed_dim  # 12 * 8 = 96
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, latent_dim),
            nn.ReLU()
        )
        
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 32),
            nn.ReLU(),
            nn.Linear(32, input_dim)
        )

    def forward(self, x):
        # x: [batch_size, window_size]
        embedded = self.embedding(x)
        flattened = embedded.view(x.size(0), -1)
        
        latent = self.encoder(flattened)
        reconstructed = self.decoder(latent)
        
        return flattened, reconstructed