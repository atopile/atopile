from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

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
        self._embedder = make_embedder(
            backend=backend,
            dimension=dimension,
            model_name=model_name,
        )
        self._store = VectorStore.load(config.index_dir)
        self._index_dir = config.index_dir

    @property
    def index_dir(self) -> Path:
        return self._index_dir

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
        return self._store.search(
            query=query,
            embedder=self._embedder,
            limit=limit,
            filters=filters,
            prefer_in_stock=prefer_in_stock,
            prefer_basic=prefer_basic,
            apply_boosts=False,
            apply_exact_shortcuts=False,
            apply_hybrid=mode == "hybrid",
        )
