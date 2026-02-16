from __future__ import annotations

import os
import sys
import time


def apply_max_cores(max_cores: int) -> None:
    value = str(max_cores)
    for key in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "BLIS_NUM_THREADS",
        "TBB_NUM_THREADS",
        "RAYON_NUM_THREADS",
    ):
        os.environ[key] = value
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    try:  # pragma: no cover - torch is optional
        import torch

        torch.set_num_threads(max_cores)
        torch.set_num_interop_threads(min(max_cores, 8))
    except Exception:
        pass


def status(message: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {message}", file=sys.stderr, flush=True)

