#!/usr/bin/env python3
"""Demo: Submit ESP32 minimal (with reuse blocks) to DeepPCB API.

Collapse USB-C + LDO into synthetic blocks, submit via the
DeepPCBAutolayout adapter (which handles resolve/confirm properly),
poll for completion, download result, expand blocks back.
"""

from __future__ import annotations

import json
import logging
import shutil
import sys
import time
from pathlib import Path

from faebryk.exporters.pcb.autolayout.deeppcb import DeepPCBAutolayout
from faebryk.exporters.pcb.deeppcb.transformer import DeepPCB_Transformer
from faebryk.libs.deeppcb import DeepPCBConfig
from faebryk.libs.kicad.fileformats import Property, kicad
from atopile.server.domains.autolayout.models import AutolayoutState, SubmitRequest

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("demo")


def _get_prop(fp, name: str) -> str | None:
    return Property.try_get_property(fp.propertys, name)


def main():
    project_root = Path("examples/esp32_minimal").resolve()
    pcb_path = project_root / "layouts/esp32_minimal/esp32_minimal.kicad_pcb"

    if not pcb_path.exists():
        print(f"ERROR: {pcb_path} not found")
        sys.exit(1)

    # Verify sub-PCBs exist
    usbc_sub = project_root / ".ato/modules/atopile/usb-connectors/layouts/default/default.kicad_pcb"
    ldo_sub = project_root / ".ato/modules/atopile/ti-tlv75901/layouts/default/default.kicad_pcb"
    if not usbc_sub.exists() or not ldo_sub.exists():
        print("ERROR: Sub-PCBs not found.")
        sys.exit(1)

    config = DeepPCBConfig()
    if not config.api_key:
        print("ERROR: ATO_DEEPPCB_API_KEY not set")
        sys.exit(1)

    adapter = DeepPCBAutolayout(config=config)

    print("=" * 70)
    print("DeepPCB Reuse Block Demo - ESP32 Minimal")
    print("=" * 70)
    print(f"API: {config.base_url}")

    # Step 1: Load and collapse
    print("\n[1] Collapsing reuse blocks...")
    if hasattr(kicad.loads, "cache"):
        kicad.loads.cache.clear()

    pcb_file = kicad.loads(kicad.pcb.PcbFile, pcb_path)
    pcb = pcb_file.kicad_pcb
    print(f"    Parent: {len(pcb.footprints)} fps, {len(pcb.segments)} segs, {len(pcb.nets)} nets")

    metadata: dict = {}
    board = DeepPCB_Transformer.from_kicad_file(
        pcb_file,
        provider_strict=True,
        project_root=project_root,
        reuse_block_metadata_out=metadata,
    )

    synth = [c for c in board.components if "REUSE_BLOCK:" in str(c.get("partNumber", ""))]
    print(f"    Collapsed: {len(board.components)} components ({len(synth)} synthetic)")
    for c in synth:
        defn = next((d for d in board.componentDefinitions if d["id"] == c["definition"]), None)
        pins = len(defn["pins"]) if defn else "?"
        print(f"      {c.get('partNumber')}: {pins} pins")

    # Save metadata
    work_dir = project_root / ".autolayout_demo"
    work_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = work_dir / "reuse_block_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Step 2: Dump DeepPCB JSON
    print("\n[2] Generating DeepPCB JSON...")
    deeppcb_path = work_dir / "esp32_minimal.deeppcb"
    DeepPCB_Transformer.dumps(board, deeppcb_path)
    size = deeppcb_path.stat().st_size
    print(f"    {deeppcb_path} ({size:,} bytes)")

    # Step 3: Submit via adapter (handles upload, create, resolve, wait, confirm)
    print("\n[3] Submitting via DeepPCBAutolayout adapter...")
    job_id = f"demo-reuse-{int(time.time())}"

    # Create a dummy input zip (required by SubmitRequest but not used for .deeppcb)
    dummy_zip = work_dir / "dummy_input.zip"
    if not dummy_zip.exists():
        import zipfile
        with zipfile.ZipFile(dummy_zip, "w") as zf:
            zf.writestr("placeholder.txt", "demo input")

    request = SubmitRequest(
        job_id=job_id,
        project_root=project_root,
        build_target="esp32_minimal",
        layout_path=pcb_path,
        provider_input_path=deeppcb_path,
        input_zip_path=dummy_zip,
        work_dir=work_dir,
        options={
            "allow_insecure_webhook_defaults": "true",
            "webhookToken": "demo-token",
            "jobType": "Routing",
            "timeout": 1,
            "maxBatchTimeout": 15,
            "timeToLive": 300,
        },
    )

    try:
        result = adapter.submit(request)
    except Exception as exc:
        print(f"    Submit failed: {exc}")
        sys.exit(1)

    board_id = result.external_job_id
    print(f"    Board ID: {board_id}")
    print(f"    State: {result.state}")
    print(f"    Message: {result.message}")
    print(f"    Candidates: {len(result.candidates)}")

    # Step 4: Poll for completion
    print("\n[4] Polling for completion...")
    for attempt in range(120):
        time.sleep(5)
        try:
            status = adapter.status(board_id)
            print(f"    [{attempt*5:3d}s] {status.state.value} "
                  f"candidates={len(status.candidates)} "
                  f"progress={status.progress} "
                  f"{status.message or ''}")

            if status.state in {
                AutolayoutState.COMPLETED,
                AutolayoutState.AWAITING_SELECTION,
            }:
                print(f"    Done! {len(status.candidates)} candidate(s)")
                break
            if status.state in {AutolayoutState.FAILED, AutolayoutState.CANCELLED}:
                print(f"    Failed: {status.message}")
                sys.exit(1)
        except Exception as exc:
            print(f"    [{attempt*5:3d}s] Poll error: {str(exc)[:200]}")
    else:
        print("    Timed out (10 min)")
        sys.exit(1)

    # Step 5: Download result
    print("\n[5] Downloading result...")
    candidates = adapter.list_candidates(board_id)
    if not candidates:
        print("    No candidates available")
        sys.exit(1)

    candidate = candidates[0]
    print(f"    Downloading candidate {candidate.candidate_id}: {candidate.label}")

    download_dir = work_dir / "download"
    if download_dir.exists():
        shutil.rmtree(download_dir)

    try:
        dl_result = adapter.download_candidate(
            board_id,
            candidate.candidate_id,
            download_dir,
        )
        downloaded = dl_result.layout_path
        print(f"    Downloaded: {downloaded}")
    except Exception as exc:
        print(f"    Download failed: {exc}")
        sys.exit(1)

    # Step 6: Expand reuse blocks
    print(f"\n[6] Expanding reuse blocks from {downloaded.name}...")
    if hasattr(kicad.loads, "cache"):
        kicad.loads.cache.clear()

    if downloaded.suffix == ".deeppcb":
        loaded_board = DeepPCB_Transformer.loads(downloaded)
        result_pcb = DeepPCB_Transformer.to_internal_pcb(loaded_board)
    else:
        result_pcb = kicad.loads(kicad.pcb.PcbFile, downloaded).kicad_pcb

    synth_fps = [fp for fp in result_pcb.footprints if str(fp.name).startswith("REUSE_BLOCK:")]
    print(f"    Before: {len(result_pcb.footprints)} fps ({len(synth_fps)} synthetic)")

    DeepPCB_Transformer.expand_reuse_blocks(result_pcb, metadata, project_root)

    synth_after = [fp for fp in result_pcb.footprints if str(fp.name).startswith("REUSE_BLOCK:")]
    print(f"    After:  {len(result_pcb.footprints)} fps ({len(synth_after)} synthetic)")
    print(f"    Segments: {len(result_pcb.segments)}, Vias: {len(result_pcb.vias)}")

    # Verify
    orig_addrs = sorted(filter(None, (_get_prop(fp, "atopile_address") for fp in pcb.footprints)))
    expanded_addrs = sorted(filter(None, (_get_prop(fp, "atopile_address") for fp in result_pcb.footprints)))
    if orig_addrs == expanded_addrs:
        print("    PASS: All atopile_addresses preserved!")
    else:
        missing = set(orig_addrs) - set(expanded_addrs)
        extra = set(expanded_addrs) - set(orig_addrs)
        if missing:
            print(f"    Missing: {sorted(missing)}")
        if extra:
            print(f"    Extra: {sorted(extra)}")

    expanded_path = work_dir / "esp32_minimal_expanded.kicad_pcb"
    kicad.dumps(kicad.pcb.PcbFile(kicad_pcb=result_pcb), expanded_path)
    print(f"    Saved: {expanded_path}")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
