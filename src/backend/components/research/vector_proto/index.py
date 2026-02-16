from __future__ import annotations

import json
import math
import re
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

import numpy as np

from .corpus import CorpusRecord, load_corpus
from .embedding import Embedder
from .runtime import status


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
        self._inverted_index: dict[str, list[int] | np.ndarray] = {}
        self._component_type_index: dict[str, np.ndarray] = {}
        self._package_index: dict[str, np.ndarray] = {}
        self._in_stock_index: np.ndarray | None = None
        self._lexical_ready = False
        self._lexical_lock = threading.Lock()
        self._build_filter_indexes()

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
        vectors = np.load(index_dir / "vectors.npy", mmap_mode="r")
        manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
        backend = str(manifest["embedding_backend"])
        return cls(records=records, vectors=vectors, embedding_backend=backend)

    def _ensure_lexical_index(self) -> None:
        if self._lexical_ready:
            return
        with self._lexical_lock:
            if self._lexical_ready:
                return
            self._build_lexical_index()
            self._lexical_ready = True

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

    def _build_filter_indexes(self) -> None:
        component_type_idx: dict[str, list[int]] = {}
        package_idx: dict[str, list[int]] = {}
        in_stock_idx: list[int] = []
        for idx, record in enumerate(self.records):
            component_type_idx.setdefault(record.component_type, []).append(idx)
            package_idx.setdefault(record.package, []).append(idx)
            if record.stock > 0:
                in_stock_idx.append(idx)
        self._component_type_index = {
            key: np.array(values, dtype=np.int32)
            for key, values in component_type_idx.items()
        }
        self._package_index = {
            key: np.array(values, dtype=np.int32)
            for key, values in package_idx.items()
        }
        self._in_stock_index = np.array(in_stock_idx, dtype=np.int32)

    def _candidate_idx_from_filters(self, filters: SearchFilters) -> np.ndarray | None:
        idx: np.ndarray | None = None
        if filters.component_type:
            idx = self._component_type_index.get(filters.component_type)
            if idx is None:
                return np.array([], dtype=np.int32)
        if filters.package:
            pidx = self._package_index.get(filters.package)
            if pidx is None:
                return np.array([], dtype=np.int32)
            idx = pidx if idx is None else np.intersect1d(idx, pidx, assume_unique=False)
        if filters.in_stock_only:
            stock_idx = self._in_stock_index
            if stock_idx is None or len(stock_idx) == 0:
                return np.array([], dtype=np.int32)
            idx = (
                stock_idx
                if idx is None
                else np.intersect1d(idx, stock_idx, assume_unique=False)
            )
        return idx

    @staticmethod
    def _should_prefilter_with_lexical(
        *,
        lexical_count: int,
        candidate_pool: int,
    ) -> bool:
        # Avoid over-constraining semantic recall on narrow lexical queries
        # like exact MPN lookups ("BME280"), while still using lexical pruning
        # to keep latency bounded on broad queries.
        threshold = max(candidate_pool * 3, 5000)
        return lexical_count >= threshold

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
        base_filter_idx = self._candidate_idx_from_filters(filters)
        if base_filter_idx is not None and len(base_filter_idx) == 0:
            return []

        query_lower = query.lower()
        query_tokens = self._tokenize_normalized(query_lower)
        lexical_scores: dict[int, float] = {}
        lexical_idx = np.array([], dtype=np.int32)
        if apply_hybrid:
            self._ensure_lexical_index()
            lexical_idx, lexical_scores = self._lexical_scores(
                query_tokens=query_tokens,
                top_k=min(
                    len(self.records),
                    max(max(limit * 10, candidate_pool * 4), 4000),
                ),
            )

        dense_candidates: np.ndarray | None = base_filter_idx
        if apply_hybrid and len(lexical_idx) and self._should_prefilter_with_lexical(
            lexical_count=len(lexical_idx),
            candidate_pool=candidate_pool,
        ):
            dense_candidates = (
                lexical_idx
                if dense_candidates is None
                else np.intersect1d(dense_candidates, lexical_idx, assume_unique=False)
            )

        # Fallback to filtered universe if lexical prefilter eliminated everything.
        if dense_candidates is not None and len(dense_candidates) == 0:
            dense_candidates = base_filter_idx

        dense_scores: dict[int, float] = {}
        if dense_candidates is None:
            cosine = np.dot(self.vectors, q_vec).astype(np.float32)
            pool = min(max(limit * 5, candidate_pool), len(self.records))
            dense_idx = np.argpartition(cosine, -pool)[-pool:]
            dense_idx = dense_idx[np.argsort(cosine[dense_idx])[::-1]]
            for i in dense_idx:
                dense_scores[int(i)] = float(cosine[int(i)])
        else:
            if len(dense_candidates) == 0:
                dense_idx = np.array([], dtype=np.int32)
            else:
                sub_scores = np.dot(self.vectors[dense_candidates], q_vec).astype(np.float32)
                pool = min(max(limit * 5, candidate_pool), len(dense_candidates))
                local_idx = np.argpartition(sub_scores, -pool)[-pool:]
                local_idx = local_idx[np.argsort(sub_scores[local_idx])[::-1]]
                dense_idx = dense_candidates[local_idx]
                for loc in local_idx:
                    dense_scores[int(dense_candidates[int(loc)])] = float(sub_scores[int(loc)])

        if len(lexical_idx):
            idx = np.unique(np.concatenate([dense_idx, lexical_idx]))
        else:
            idx = dense_idx

        if len(idx) == 0:
            return []

        boosted: list[tuple[float, float, list[str], CorpusRecord]] = []
        for i in idx:
            record = self.records[int(i)]
            if not self._match_filters(record, filters):
                continue
            lexical_score = float(lexical_scores.get(int(i), 0.0))
            dense_score = dense_scores.get(int(i))
            if dense_score is None:
                dense_score = float(np.dot(self.vectors[int(i)], q_vec))
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


def test_build_index_files_streams_and_writes_manifest(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.jsonl"
    records = [
        CorpusRecord(
            lcsc_id=1,
            component_type="sensor",
            category="sensors",
            subcategory="temperature",
            manufacturer_name="Acme",
            part_number="TMP-1",
            package="SOT-23",
            description="temperature sensor",
            stock=10,
            is_basic=False,
            is_preferred=False,
            attrs={},
            text="lcsc C1 sensor temperature TMP-1",
        ),
        CorpusRecord(
            lcsc_id=2,
            component_type="mcu",
            category="ics",
            subcategory="microcontroller",
            manufacturer_name="Acme",
            part_number="MCU-2",
            package="QFN-32",
            description="small microcontroller",
            stock=20,
            is_basic=True,
            is_preferred=False,
            attrs={},
            text="lcsc C2 mcu qfn32",
        ),
    ]
    with corpus.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=True, sort_keys=True))
            f.write("\n")

    from .embedding import HashingEmbedder

    out_dir = tmp_path / "index"
    rows = build_index_files(
        corpus_path=corpus,
        out_dir=out_dir,
        embedder=HashingEmbedder(dimension=64),
        batch_size=1,
    )
    assert rows == 2
    loaded = VectorStore.load(out_dir)
    assert len(loaded.records) == 2
    assert loaded.vectors.shape == (2, 64)


def test_candidate_idx_filters_include_in_stock() -> None:
    records = [
        CorpusRecord(
            lcsc_id=11,
            component_type="sensor",
            category="sensors",
            subcategory="pressure",
            manufacturer_name="A",
            part_number="S-1",
            package="QFN-16",
            description="sensor one",
            stock=0,
            is_basic=False,
            is_preferred=False,
            attrs={},
            text="sensor one",
        ),
        CorpusRecord(
            lcsc_id=22,
            component_type="sensor",
            category="sensors",
            subcategory="pressure",
            manufacturer_name="B",
            part_number="S-2",
            package="QFN-16",
            description="sensor two",
            stock=12,
            is_basic=False,
            is_preferred=False,
            attrs={},
            text="sensor two",
        ),
    ]
    from .embedding import HashingEmbedder

    emb = HashingEmbedder(dimension=64)
    store = VectorStore(
        records=records,
        vectors=emb.embed_texts([r.text for r in records]),
        embedding_backend=emb.name,
    )
    idx = store._candidate_idx_from_filters(  # type: ignore[attr-defined]
        SearchFilters(component_type="sensor", in_stock_only=True)
    )
    assert idx is not None
    assert idx.tolist() == [1]


def test_should_prefilter_with_lexical_threshold() -> None:
    assert not VectorStore._should_prefilter_with_lexical(
        lexical_count=120,
        candidate_pool=400,
    )
    assert VectorStore._should_prefilter_with_lexical(
        lexical_count=5000,
        candidate_pool=400,
    )


def test_lazy_lexical_index_builds_only_for_hybrid() -> None:
    records = [
        CorpusRecord(
            lcsc_id=11,
            component_type="sensor",
            category="sensors",
            subcategory="pressure",
            manufacturer_name="A",
            part_number="S-1",
            package="QFN-16",
            description="pressure sensor",
            stock=10,
            is_basic=False,
            is_preferred=False,
            attrs={},
            text="pressure sensor qfn16",
        ),
        CorpusRecord(
            lcsc_id=22,
            component_type="sensor",
            category="sensors",
            subcategory="temperature",
            manufacturer_name="B",
            part_number="S-2",
            package="QFN-16",
            description="temperature sensor",
            stock=12,
            is_basic=False,
            is_preferred=False,
            attrs={},
            text="temperature sensor qfn16",
        ),
    ]
    from .embedding import HashingEmbedder

    emb = HashingEmbedder(dimension=64)
    store = VectorStore(
        records=records,
        vectors=emb.embed_texts([r.text for r in records]),
        embedding_backend=emb.name,
    )
    assert store._lexical_ready is False  # type: ignore[attr-defined]
    _ = store.search(query="pressure", embedder=emb, apply_hybrid=False, limit=2)
    assert store._lexical_ready is False  # type: ignore[attr-defined]
    _ = store.search(query="pressure", embedder=emb, apply_hybrid=True, limit=2)
    assert store._lexical_ready is True  # type: ignore[attr-defined]


def _parse_corpus_line(line: str) -> CorpusRecord:
    payload = json.loads(line)
    return CorpusRecord(
        lcsc_id=int(payload["lcsc_id"]),
        component_type=str(payload["component_type"]),
        category=str(payload["category"]),
        subcategory=str(payload["subcategory"]),
        manufacturer_name=payload.get("manufacturer_name"),
        part_number=str(payload["part_number"]),
        package=str(payload["package"]),
        description=str(payload["description"]),
        stock=int(payload["stock"]),
        is_basic=bool(payload["is_basic"]),
        is_preferred=bool(payload["is_preferred"]),
        attrs=payload.get("attrs", {}),
        text=str(payload["text"]),
    )


def _iter_corpus(corpus_path: Path) -> Iterator[CorpusRecord]:
    with corpus_path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            yield _parse_corpus_line(stripped)


def _count_corpus_rows(corpus_path: Path) -> int:
    with corpus_path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def build_index_files(
    *,
    corpus_path: Path,
    out_dir: Path,
    embedder: Embedder,
    batch_size: int = 2048,
    progress_every: int = 20000,
) -> int:
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    out_dir.mkdir(parents=True, exist_ok=True)

    total = _count_corpus_rows(corpus_path)
    status(f"build-index total_rows={total} batch_size={batch_size}")
    if total == 0:
        vectors = np.zeros((0, int(embedder.dimension)), dtype=np.float32)
        np.save(out_dir / "vectors.npy", vectors, allow_pickle=False)
        (out_dir / "records.jsonl").write_text("", encoding="utf-8")
        manifest = IndexManifest(
            embedding_backend=embedder.name,
            embedding_dimension=int(embedder.dimension),
            corpus_size=0,
            corpus_path=str(corpus_path),
        )
        (out_dir / "manifest.json").write_text(
            json.dumps(asdict(manifest), ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return 0

    vectors_mm = np.lib.format.open_memmap(
        out_dir / "vectors.npy",
        mode="w+",
        dtype=np.float32,
        shape=(total, int(embedder.dimension)),
    )

    written = 0
    last_logged = 0
    batch_records: list[CorpusRecord] = []
    batch_texts: list[str] = []
    with (out_dir / "records.jsonl").open("w", encoding="utf-8") as records_file:
        for record in _iter_corpus(corpus_path):
            batch_records.append(record)
            batch_texts.append(record.text)
            if len(batch_texts) < batch_size:
                continue

            batch_vectors = embedder.embed_texts(batch_texts)
            batch_n = len(batch_records)
            vectors_mm[written : written + batch_n] = batch_vectors
            for item in batch_records:
                records_file.write(json.dumps(asdict(item), ensure_ascii=True, sort_keys=True))
                records_file.write("\n")
            written += batch_n
            if (written - last_logged) >= progress_every or written == total:
                status(f"build-index embedded_rows={written}/{total}")
                last_logged = written
            batch_records.clear()
            batch_texts.clear()

        if batch_records:
            batch_vectors = embedder.embed_texts(batch_texts)
            batch_n = len(batch_records)
            vectors_mm[written : written + batch_n] = batch_vectors
            for item in batch_records:
                records_file.write(json.dumps(asdict(item), ensure_ascii=True, sort_keys=True))
                records_file.write("\n")
            written += batch_n
            if (written - last_logged) >= progress_every or written == total:
                status(f"build-index embedded_rows={written}/{total}")
                last_logged = written

    vectors_mm.flush()
    manifest = IndexManifest(
        embedding_backend=embedder.name,
        embedding_dimension=int(embedder.dimension),
        corpus_size=written,
        corpus_path=str(corpus_path),
    )
    (out_dir / "manifest.json").write_text(
        json.dumps(asdict(manifest), ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    status(f"build-index complete rows={written} out_dir={out_dir}")
    return written
