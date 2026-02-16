from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.components.research.vector_proto.embedding import make_embedder
from backend.components.research.vector_proto.index import SearchFilters, VectorStore
from backend.components.research.vector_proto.runtime import apply_max_cores


@dataclass(frozen=True)
class VectorSearchConfig:
    index_dir: Path
    max_cores: int = 32


class PrototypeVectorSearchService:
    def __init__(self, config: VectorSearchConfig):
        if not config.index_dir.exists():
            raise FileNotFoundError(f"vector index dir not found: {config.index_dir}")
        manifest_path = config.index_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"vector index manifest not found: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        backend_name = str(manifest.get("embedding_backend", "hashing_v1"))
        dimension = int(manifest.get("embedding_dimension", 384))

        if backend_name.startswith("sentence_transformers:"):
            model_name = backend_name.split(":", 1)[1]
            backend = "sentence-transformers"
        else:
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
            backend = "hashing"

        apply_max_cores(config.max_cores)
        self._backend = backend
        self._dimension = dimension
        self._model_name = model_name
        self._embedder = None
        self._store = None
        self._init_lock = threading.Lock()
        self._index_dir = config.index_dir

    @property
    def index_dir(self) -> Path:
        return self._index_dir

    def _ensure_loaded(self) -> tuple[VectorStore, Any]:
        if self._store is not None and self._embedder is not None:
            return self._store, self._embedder
        with self._init_lock:
            if self._store is None:
                self._store = VectorStore.load(self._index_dir)
            if self._embedder is None:
                self._embedder = make_embedder(
                    backend=self._backend,
                    dimension=self._dimension,
                    model_name=self._model_name,
                )
        if self._store is None or self._embedder is None:
            raise RuntimeError("vector search service initialization failed")
        return self._store, self._embedder

    def search(
        self,
        *,
        query: str,
        limit: int,
        component_type: str | None,
        package: str | None,
        in_stock_only: bool,
        prefer_in_stock: bool,
        prefer_basic: bool,
        search_mode: str,
    ):
        filters = SearchFilters(
            component_type=component_type,
            package=package,
            in_stock_only=in_stock_only,
        )
        mode = (search_mode or "hybrid").strip().lower()
        if mode not in {"hybrid", "raw_vector"}:
            mode = "hybrid"
        store, embedder = self._ensure_loaded()
        return store.search(
            query=query,
            embedder=embedder,
            limit=limit,
            filters=filters,
            prefer_in_stock=prefer_in_stock,
            prefer_basic=prefer_basic,
            apply_boosts=False,
            apply_exact_shortcuts=False,
            apply_hybrid=mode == "hybrid",
        )
