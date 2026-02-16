from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    dimension: int
    name: str

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        ...


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9._+\-/]*", text.lower())


@dataclass(frozen=True)
class HashingEmbedder:
    dimension: int = 384
    name: str = "hashing_v1"

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        mat = np.zeros((len(texts), self.dimension), dtype=np.float32)
        for row_idx, text in enumerate(texts):
            for token in _tokenize(text):
                digest = hashlib.blake2b(
                    token.encode("utf-8"), digest_size=8
                ).digest()
                hashed = int.from_bytes(digest, byteorder="little", signed=False)
                col = hashed % self.dimension
                sign = 1.0 if ((hashed >> 63) & 1) == 0 else -1.0
                mat[row_idx, col] += sign
            norm = float(np.linalg.norm(mat[row_idx]))
            if norm > 0:
                mat[row_idx] /= norm
        return mat


class SentenceTransformersEmbedder:
    def __init__(self, *, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Install it before using --embedding-backend sentence-transformers."
            ) from exc
        self._model = SentenceTransformer(model_name)
        probe = self._model.encode(["probe"], normalize_embeddings=True)
        self.dimension = int(probe.shape[1])
        self.name = f"sentence_transformers:{model_name}"

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        vectors = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)


def make_embedder(
    *,
    backend: str,
    dimension: int,
    model_name: str,
) -> Embedder:
    if backend == "hashing":
        return HashingEmbedder(dimension=dimension)
    if backend == "sentence-transformers":
        return SentenceTransformersEmbedder(model_name=model_name)
    raise ValueError(f"Unsupported embedding backend: {backend}")


def test_hashing_embedder_outputs_unit_norm_vectors() -> None:
    emb = HashingEmbedder(dimension=64)
    vectors = emb.embed_texts(["10k resistor 0402", "3.3v ldo"])
    assert vectors.shape == (2, 64)
    for row in vectors:
        assert abs(float(np.linalg.norm(row)) - 1.0) < 1e-5

