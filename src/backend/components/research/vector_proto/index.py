from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .corpus import CorpusRecord, load_corpus
from .embedding import Embedder


@dataclass(frozen=True)
class SearchFilters:
    component_type: str | None = None
    package: str | None = None
    in_stock_only: bool = False


@dataclass(frozen=True)
class SearchResult:
    lcsc_id: int
    score: float
    cosine_score: float
    reasons: list[str]
    component_type: str
    manufacturer_name: str | None
    part_number: str
    package: str
    description: str
    stock: int
    is_basic: bool
    is_preferred: bool


@dataclass(frozen=True)
class IndexManifest:
    embedding_backend: str
    embedding_dimension: int
    corpus_size: int
    corpus_path: str


class VectorStore:
    def __init__(
        self,
        *,
        records: list[CorpusRecord],
        vectors: np.ndarray,
        embedding_backend: str,
    ):
        if vectors.ndim != 2:
            raise ValueError("vectors must be a 2D matrix")
        if vectors.shape[0] != len(records):
            raise ValueError("vector row count must match records")
        self.records = records
        self.vectors = vectors.astype(np.float32, copy=False)
        self.embedding_backend = embedding_backend
        self._id_to_idx = {record.lcsc_id: idx for idx, record in enumerate(records)}

    @property
    def dimension(self) -> int:
        return int(self.vectors.shape[1])

    def save(self, out_dir: Path, *, corpus_path: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        np.save(out_dir / "vectors.npy", self.vectors, allow_pickle=False)
        with (out_dir / "records.jsonl").open("w", encoding="utf-8") as f:
            for record in self.records:
                f.write(json.dumps(asdict(record), ensure_ascii=True, sort_keys=True))
                f.write("\n")
        manifest = IndexManifest(
            embedding_backend=self.embedding_backend,
            embedding_dimension=self.dimension,
            corpus_size=len(self.records),
            corpus_path=str(corpus_path),
        )
        (out_dir / "manifest.json").write_text(
            json.dumps(asdict(manifest), ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    @classmethod
    def from_corpus(
        cls,
        *,
        corpus_path: Path,
        embedder: Embedder,
    ) -> "VectorStore":
        records = load_corpus(corpus_path)
        vectors = embedder.embed_texts([record.text for record in records])
        return cls(records=records, vectors=vectors, embedding_backend=embedder.name)

    @classmethod
    def load(cls, index_dir: Path) -> "VectorStore":
        records = load_corpus(index_dir / "records.jsonl")
        vectors = np.load(index_dir / "vectors.npy")
        manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
        backend = str(manifest["embedding_backend"])
        return cls(records=records, vectors=vectors, embedding_backend=backend)

    def _match_filters(self, record: CorpusRecord, filters: SearchFilters) -> bool:
        if filters.component_type and record.component_type != filters.component_type:
            return False
        if filters.package and record.package != filters.package:
            return False
        return (not filters.in_stock_only) or record.stock > 0

    def _extract_lcsc_hint(self, query: str) -> int | None:
        match = re.search(r"\bC?(\d{3,})\b", query.upper())
        if not match:
            return None
        return int(match.group(1))

    def _boost(
        self,
        *,
        query_lower: str,
        query_tokens: set[str],
        record: CorpusRecord,
        cosine: float,
        prefer_in_stock: bool,
        prefer_basic: bool,
    ) -> tuple[float, list[str]]:
        score = cosine
        reasons: list[str] = [f"semantic={cosine:.3f}"]
        mpn_lower = record.part_number.lower()
        if mpn_lower and mpn_lower in query_lower:
            score += 0.45
            reasons.append("exact_mpn")
        if prefer_in_stock and record.stock > 0:
            score += 0.10
            reasons.append("in_stock")
        if prefer_basic and record.is_basic:
            score += 0.08
            reasons.append("basic")
        overlap = query_tokens.intersection(set(mpn_lower.split("-")))
        if overlap:
            score += 0.05
            reasons.append("mpn_token_overlap")
        return score, reasons

    def search(
        self,
        *,
        query: str,
        embedder: Embedder,
        limit: int = 20,
        filters: SearchFilters | None = None,
        prefer_in_stock: bool = True,
        prefer_basic: bool = True,
        apply_boosts: bool = True,
        apply_exact_shortcuts: bool = True,
        candidate_pool: int = 400,
    ) -> list[SearchResult]:
        if not self.records:
            return []
        filters = filters or SearchFilters()
        q_vec = embedder.embed_texts([query])[0]
        cosine = np.dot(self.vectors, q_vec).astype(np.float32)
        pool = min(max(limit * 5, candidate_pool), len(self.records))
        idx = np.argpartition(cosine, -pool)[-pool:]
        idx = idx[np.argsort(cosine[idx])[::-1]]

        query_lower = query.lower()
        query_tokens = set(re.findall(r"[a-z0-9._+\-/]+", query_lower))
        boosted: list[tuple[float, float, list[str], CorpusRecord]] = []
        for i in idx:
            record = self.records[int(i)]
            if not self._match_filters(record, filters):
                continue
            if apply_boosts:
                score, reasons = self._boost(
                    query_lower=query_lower,
                    query_tokens=query_tokens,
                    record=record,
                    cosine=float(cosine[int(i)]),
                    prefer_in_stock=prefer_in_stock,
                    prefer_basic=prefer_basic,
                )
            else:
                score = float(cosine[int(i)])
                reasons = [f"semantic={score:.3f}"]
            boosted.append((score, float(cosine[int(i)]), reasons, record))

        if apply_exact_shortcuts:
            lcsc_hint = self._extract_lcsc_hint(query)
            if lcsc_hint is not None and lcsc_hint in self._id_to_idx:
                hit = self.records[self._id_to_idx[lcsc_hint]]
                if self._match_filters(hit, filters):
                    boosted.append((2.0, 1.0, ["exact_lcsc"], hit))

        boosted.sort(key=lambda item: item[0], reverse=True)
        dedup: set[int] = set()
        out: list[SearchResult] = []
        for score, cos_score, reasons, record in boosted:
            if record.lcsc_id in dedup:
                continue
            dedup.add(record.lcsc_id)
            out.append(
                SearchResult(
                    lcsc_id=record.lcsc_id,
                    score=score,
                    cosine_score=cos_score,
                    reasons=reasons,
                    component_type=record.component_type,
                    manufacturer_name=record.manufacturer_name,
                    part_number=record.part_number,
                    package=record.package,
                    description=record.description,
                    stock=record.stock,
                    is_basic=record.is_basic,
                    is_preferred=record.is_preferred,
                )
            )
            if len(out) >= limit:
                break
        return out


def test_vector_store_exact_lcsc_boosts_to_top() -> None:
    records = [
        CorpusRecord(
            lcsc_id=1001,
            component_type="resistor",
            category="passive",
            subcategory="chip resistor",
            manufacturer_name="A",
            part_number="R-10K",
            package="0402",
            description="10k resistor",
            stock=100,
            is_basic=True,
            is_preferred=False,
            attrs={},
            text="lcsc C1001 resistor 10k 0402",
        ),
        CorpusRecord(
            lcsc_id=2002,
            component_type="resistor",
            category="passive",
            subcategory="chip resistor",
            manufacturer_name="B",
            part_number="R-1K",
            package="0402",
            description="1k resistor",
            stock=100,
            is_basic=True,
            is_preferred=False,
            attrs={},
            text="lcsc C2002 resistor 1k 0402",
        ),
    ]
    from .embedding import HashingEmbedder

    emb = HashingEmbedder(dimension=64)
    vectors = emb.embed_texts([record.text for record in records])
    store = VectorStore(records=records, vectors=vectors, embedding_backend=emb.name)
    results = store.search(query="C2002", embedder=emb, limit=1)
    assert results[0].lcsc_id == 2002
