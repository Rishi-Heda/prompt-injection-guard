import torch
import torch.nn as nn

class TrajectoryAutoencoder(nn.Module):
    def __init__(self, vocab_size=8, embed_dim=8, window_size=5, bottleneck_dim=4):
        super().__init__()
        self.embedding = nn.Embedding(num_embeddings=vocab_size, embedding_dim=embed_dim)
        
        input_dim = window_size * embed_dim
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, bottleneck_dim),
            nn.ReLU()
        )
        
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, 16),
            nn.ReLU(),
            nn.Linear(16, input_dim)
        )

    def forward(self, x):
        embedded = self.embedding(x)
        flattened = embedded.view(x.size(0), -1) 
        latent = self.encoder(flattened)
        reconstructed = self.decoder(latent)
        return flattened, reconstructed