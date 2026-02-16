from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runtime import apply_max_cores, status


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Vector prototype tooling for component search experiments."
    )
    parser.add_argument(
        "--max-cores",
        type=int,
        default=32,
        help="Limit CPU parallelism libraries to this many threads.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_export = sub.add_parser("export-corpus", help="Export corpus rows from detail.sqlite")
    p_export.add_argument("--detail-db", type=Path, required=True)
    p_export.add_argument("--out-jsonl", type=Path, required=True)
    p_export.add_argument("--limit", type=int, default=None)
    p_export.add_argument("--seed", type=int, default=7)

    p_export_balanced = sub.add_parser(
        "export-balanced-stage1",
        help="Export balanced 10k-ish corpus directly from stage-1 /home/jlc/cache.sqlite3",
    )
    p_export_balanced.add_argument("--cache-sqlite", type=Path, required=True)
    p_export_balanced.add_argument("--out-jsonl", type=Path, required=True)
    p_export_balanced.add_argument("--target-count", type=int, default=10000)
    p_export_balanced.add_argument("--per-subcategory-cap", type=int, default=600)

    p_export_full = sub.add_parser(
        "export-full-stage1",
        help="Export full corpus directly from stage-1 /home/jlc/cache.sqlite3",
    )
    p_export_full.add_argument("--cache-sqlite", type=Path, required=True)
    p_export_full.add_argument("--out-jsonl", type=Path, required=True)
    p_export_full.add_argument("--in-stock-only", action="store_true")

    p_index = sub.add_parser("build-index", help="Build vector index from corpus JSONL")
    p_index.add_argument("--corpus-jsonl", type=Path, required=True)
    p_index.add_argument("--out-dir", type=Path, required=True)
    p_index.add_argument("--batch-size", type=int, default=2048)
    p_index.add_argument(
        "--embedding-backend",
        choices=["hashing", "sentence-transformers"],
        default="hashing",
    )
    p_index.add_argument("--embedding-dim", type=int, default=384)
    p_index.add_argument(
        "--model-name",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Used only when --embedding-backend=sentence-transformers",
    )

    p_query = sub.add_parser("query", help="Run query against built index")
    p_query.add_argument("--index-dir", type=Path, required=True)
    p_query.add_argument("--query", required=True)
    p_query.add_argument("--limit", type=int, default=20)
    p_query.add_argument(
        "--embedding-backend",
        choices=["hashing", "sentence-transformers"],
        default="hashing",
    )
    p_query.add_argument("--embedding-dim", type=int, default=384)
    p_query.add_argument(
        "--model-name",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Used only when --embedding-backend=sentence-transformers",
    )
    p_query.add_argument("--component-type", default=None)
    p_query.add_argument("--package", default=None)
    p_query.add_argument("--in-stock-only", action="store_true")
    p_query.add_argument("--prefer-in-stock", action="store_true")
    p_query.add_argument("--prefer-basic", action="store_true")
    p_query.set_defaults(raw_vector_only=True)
    p_query.add_argument(
        "--raw-vector-only",
        action="store_true",
        help="Use cosine-only ranking (default).",
    )
    p_query.add_argument(
        "--enable-rerank",
        action="store_false",
        dest="raw_vector_only",
        help="Enable heuristic reranking/shortcuts on top of vector similarity.",
    )

    p_eval = sub.add_parser("eval", help="Run evaluation queries and emit report JSON")
    p_eval.add_argument("--index-dir", type=Path, required=True)
    p_eval.add_argument("--queries-jsonl", type=Path, required=True)
    p_eval.add_argument("--out-report", type=Path, required=True)
    p_eval.add_argument(
        "--embedding-backend",
        choices=["hashing", "sentence-transformers"],
        default="hashing",
    )
    p_eval.add_argument("--embedding-dim", type=int, default=384)
    p_eval.add_argument(
        "--model-name",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Used only when --embedding-backend=sentence-transformers",
    )
    p_eval.add_argument("--prefer-in-stock", action="store_true")
    p_eval.add_argument("--prefer-basic", action="store_true")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    apply_max_cores(args.max_cores)
    status(f"max_cores={args.max_cores}")

    if args.cmd == "export-corpus":
        from .corpus import export_corpus

        count = export_corpus(
            detail_db=args.detail_db,
            out_jsonl=args.out_jsonl,
            limit=args.limit,
            seed=args.seed,
        )
        print(json.dumps({"status": "ok", "rows": count, "out_jsonl": str(args.out_jsonl)}))
        return

    if args.cmd == "export-balanced-stage1":
        from .stage1_balanced import export_balanced_stage1_corpus

        count = export_balanced_stage1_corpus(
            cache_sqlite=args.cache_sqlite,
            out_jsonl=args.out_jsonl,
            target_count=args.target_count,
            per_subcategory_cap=args.per_subcategory_cap,
        )
        print(
            json.dumps(
                {
                    "status": "ok",
                    "rows": count,
                    "out_jsonl": str(args.out_jsonl),
                    "target_count": args.target_count,
                    "per_subcategory_cap": args.per_subcategory_cap,
                },
                sort_keys=True,
            )
        )
        return

    if args.cmd == "export-full-stage1":
        from .stage1_balanced import export_full_stage1_corpus

        count = export_full_stage1_corpus(
            cache_sqlite=args.cache_sqlite,
            out_jsonl=args.out_jsonl,
            in_stock_only=bool(args.in_stock_only),
        )
        print(
            json.dumps(
                {
                    "status": "ok",
                    "rows": count,
                    "out_jsonl": str(args.out_jsonl),
                    "in_stock_only": bool(args.in_stock_only),
                },
                sort_keys=True,
            )
        )
        return

    if args.cmd == "build-index":
        from .embedding import make_embedder
        from .index import build_index_files

        embedder = make_embedder(
            backend=args.embedding_backend,
            dimension=args.embedding_dim,
            model_name=args.model_name,
        )
        rows = build_index_files(
            corpus_path=args.corpus_jsonl,
            out_dir=args.out_dir,
            embedder=embedder,
            batch_size=args.batch_size,
        )
        print(
            json.dumps(
                {
                    "status": "ok",
                    "index_dir": str(args.out_dir),
                    "corpus_size": rows,
                    "embedding_backend": embedder.name,
                    "embedding_dim": int(embedder.dimension),
                },
                sort_keys=True,
            )
        )
        return

    if args.cmd == "query":
        from .embedding import make_embedder
        from .index import SearchFilters, VectorStore

        embedder = make_embedder(
            backend=args.embedding_backend,
            dimension=args.embedding_dim,
            model_name=args.model_name,
        )
        store = VectorStore.load(args.index_dir)
        results = store.search(
            query=args.query,
            embedder=embedder,
            limit=args.limit,
            filters=SearchFilters(
                component_type=args.component_type,
                package=args.package,
                in_stock_only=args.in_stock_only,
            ),
            prefer_in_stock=args.prefer_in_stock,
            prefer_basic=args.prefer_basic,
            apply_boosts=not args.raw_vector_only,
            apply_exact_shortcuts=not args.raw_vector_only,
        )
        print(
            json.dumps(
                [
                    {
                        "lcsc_id": item.lcsc_id,
                        "score": item.score,
                        "cosine_score": item.cosine_score,
                        "reasons": item.reasons,
                        "component_type": item.component_type,
                        "manufacturer_name": item.manufacturer_name,
                        "part_number": item.part_number,
                        "package": item.package,
                        "description": item.description,
                        "stock": item.stock,
                        "is_basic": item.is_basic,
                        "is_preferred": item.is_preferred,
                    }
                    for item in results
                ],
                ensure_ascii=True,
                indent=2,
            )
        )
        return

    if args.cmd == "eval":
        from .embedding import make_embedder
        from .eval import load_eval_queries, run_eval
        from .index import VectorStore

        embedder = make_embedder(
            backend=args.embedding_backend,
            dimension=args.embedding_dim,
            model_name=args.model_name,
        )
        store = VectorStore.load(args.index_dir)
        queries = load_eval_queries(args.queries_jsonl)
        report = run_eval(
            index=store,
            embedder=embedder,
            queries=queries,
            prefer_in_stock=args.prefer_in_stock,
            prefer_basic=args.prefer_basic,
        )
        args.out_report.parent.mkdir(parents=True, exist_ok=True)
        args.out_report.write_text(
            json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "status": "ok",
                    "out_report": str(args.out_report),
                    "query_count": report["query_count"],
                    "hit_at_1": report["hit_at_1"],
                    "hit_at_5": report["hit_at_5"],
                    "hit_at_10": report["hit_at_10"],
                    "mrr": report["mrr"],
                    "latency_ms_p50": report["latency_ms_p50"],
                    "latency_ms_p95": report["latency_ms_p95"],
                },
                sort_keys=True,
            )
        )
        return

    raise RuntimeError(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
