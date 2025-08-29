"""
image_embedding.py
Image embedding & similarity placeholder for Universal File Collector.

Later: integrate MobileNet or similar lightweight model for feature vectors.
"""

from pathlib import Path
import hashlib


def compute_embedding(image_path: Path) -> list[float]:
    """
    Generate a simple embedding for an image.

    Args:
        image_path (Path): Path to the image.

    Returns:
        list[float]: Fake embedding vector.
    """
    # TODO: Replace with TensorFlow MobileNet/ResNet features
    h = hashlib.sha256(image_path.name.encode("utf-8")).hexdigest()
    return [int(h[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]


def compare_embeddings(vec1: list[float], vec2: list[float]) -> float:
    """
    Compare two embeddings (cosine similarity placeholder).

    Args:
        vec1 (list[float]): First vector.
        vec2 (list[float]): Second vector.

    Returns:
        float: Similarity score 0.0–1.0.
    """
    # TODO: implement cosine similarity properly
    min_len = min(len(vec1), len(vec2))
    score = sum(1 - abs(a - b) for a, b in zip(vec1[:min_len], vec2[:min_len])) / min_len
    return round(score, 3)
