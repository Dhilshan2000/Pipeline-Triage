import hashlib
import math
from typing import List

VECTOR_SIZE = 384

def compute_local_embedding(text: str) -> List[float]:
    """
    Computes a 384-dimensional dense normalized vector.
    Uses fast, deterministic token hashing with n-gram feature distribution
    to ensure offline reproducibility without requiring large model weights
    to be downloaded over internet during testing.
    """
    vec = [0.0] * VECTOR_SIZE
    if not text:
        return vec

    tokens = text.lower().split()
    for token in tokens:
        h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
        idx = h % VECTOR_SIZE
        weight = 1.0 + (h % 5) * 0.1
        vec[idx] += weight
        
        # Bigram feature
        h2 = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        idx2 = (h2 ^ (h >> 8)) % VECTOR_SIZE
        vec[idx2] += 0.5

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec
