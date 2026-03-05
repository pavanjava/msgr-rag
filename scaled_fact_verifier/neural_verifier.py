import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel
import numpy as np

class ScaleSpecificVerifier(nn.Module):
    def __init__(self, scale_name: str, embedding_dim: int = 768):
        super().__init__()
        self.scale_name = scale_name
        self.tokenizer = AutoTokenizer.from_pretrained("dmis-lab/biobert-base-cased-v1.2")
        self.bert = AutoModel.from_pretrained("dmis-lab/biobert-base-cased-v1.2")
        self.classifier = nn.Sequential(
            nn.Linear(embedding_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 1),
            nn.Sigmoid()
        )

    def embed_fact(self, fact_triple):
        """Embed fact triple (subject, predicate, object) for this scale"""
        subject, predicate, obj = fact_triple
        fact_text = f"{subject} {predicate} {obj}"

        inputs = self.tokenizer(fact_text, return_tensors="pt",
                                truncation=True, padding=True, max_length=128)

        with torch.no_grad():
            outputs = self.bert(**inputs)
            # Use [CLS] token embedding
            embedding = outputs.last_hidden_state[:, 0, :]

        return embedding

    def verify_fact(self, fact_triple):
        """Return verification score S_i(f) for this scale"""
        embedding = self.embed_fact(fact_triple)
        score = self.classifier(embedding)
        return score.item()

# Initialize verifiers for each scale
entity_verifier = ScaleSpecificVerifier("entity")
concept_verifier = ScaleSpecificVerifier("concept")
domain_verifier = ScaleSpecificVerifier("domain")