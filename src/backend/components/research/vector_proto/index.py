from __future__ import annotations

import json
import math
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
        self._token_pattern = re.compile(r"[a-z0-9][a-z0-9._+\-/]*")
        self._doc_tokens: list[set[str]] = []
        self._token_doc_freq: dict[str, int] = {}
        self._inverted_index: dict[str, list[int]] = {}
        self._build_lexical_index()

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

    def _normalize_token(self, token: str) -> str:
        token = token.lower()
        if len(token) > 4 and token.endswith("ies"):
            return token[:-3] + "y"
        if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            return token[:-1]
        return token

    def _tokenize_normalized(self, text: str) -> set[str]:
        return {
            self._normalize_token(token)
            for token in self._token_pattern.findall(text.lower())
        }

    def _build_lexical_index(self) -> None:
        doc_freq: dict[str, int] = {}
        inverted: dict[str, list[int]] = {}
        doc_tokens: list[set[str]] = []
        for idx, record in enumerate(self.records):
            tokens = self._tokenize_normalized(record.text)
            doc_tokens.append(tokens)
            for token in tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1
                inverted.setdefault(token, []).append(idx)
        self._doc_tokens = doc_tokens
        self._token_doc_freq = doc_freq
        self._inverted_index = inverted

    def _idf(self, token: str) -> float:
        df = self._token_doc_freq.get(token, 0)
        n = max(len(self.records), 1)
        return math.log((n + 1.0) / (df + 1.0)) + 1.0

    def _lexical_scores(
        self,
        *,
        query_tokens: set[str],
        top_k: int,
    ) -> tuple[np.ndarray, dict[int, float]]:
        if not query_tokens:
            return np.array([], dtype=np.int32), {}
        query_weight = sum(self._idf(token) for token in query_tokens)
        if query_weight <= 0:
            return np.array([], dtype=np.int32), {}
        scores: dict[int, float] = {}
        for token in query_tokens:
            idf = self._idf(token)
            for idx in self._inverted_index.get(token, []):
                scores[idx] = scores.get(idx, 0.0) + idf
        for idx, score in list(scores.items()):
            scores[idx] = score / query_weight
        if not scores:
            return np.array([], dtype=np.int32), {}
        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        ids = np.array([idx for idx, _score in ordered[:top_k]], dtype=np.int32)
        return ids, scores

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
        apply_hybrid: bool = False,
        dense_weight: float = 0.75,
        lexical_weight: float = 0.25,
        candidate_pool: int = 400,
    ) -> list[SearchResult]:
        if not self.records:
            return []
        filters = filters or SearchFilters()
        q_vec = embedder.embed_texts([query])[0]
        cosine = np.dot(self.vectors, q_vec).astype(np.float32)
        pool = min(max(limit * 5, candidate_pool), len(self.records))
        dense_idx = np.argpartition(cosine, -pool)[-pool:]
        dense_idx = dense_idx[np.argsort(cosine[dense_idx])[::-1]]

        query_lower = query.lower()
        query_tokens = self._tokenize_normalized(query_lower)
        lexical_scores: dict[int, float] = {}
        lexical_idx = np.array([], dtype=np.int32)
        if apply_hybrid:
            lexical_idx, lexical_scores = self._lexical_scores(
                query_tokens=query_tokens,
                top_k=pool,
            )
        if len(lexical_idx):
            idx = np.unique(np.concatenate([dense_idx, lexical_idx]))
            idx = idx[np.argsort(cosine[idx])[::-1]]
        else:
            idx = dense_idx

        boosted: list[tuple[float, float, list[str], CorpusRecord]] = []
        for i in idx:
            record = self.records[int(i)]
            if not self._match_filters(record, filters):
                continue
            lexical_score = float(lexical_scores.get(int(i), 0.0))
            dense_score = float(cosine[int(i)])
            base_score = (
                dense_weight * dense_score + lexical_weight * lexical_score
                if apply_hybrid
                else dense_score
            )
            if apply_boosts:
                score, reasons = self._boost(
                    query_lower=query_lower,
                    query_tokens=query_tokens,
                    record=record,
                    cosine=base_score,
                    prefer_in_stock=prefer_in_stock,
                    prefer_basic=prefer_basic,
                )
            else:
                score = base_score
                reasons = [f"semantic={dense_score:.3f}"]
                if apply_hybrid:
                    reasons.append(f"lexical={lexical_score:.3f}")
            boosted.append((score, dense_score, reasons, record))

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
