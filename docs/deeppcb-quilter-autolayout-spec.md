# DeepPCB + Quilter Autolayout Integration Spec and Test Plan

Status: Draft  
Date: 2026-02-13  
Authors: atopile team

## 1. Goals

Build an in-tool autolayout workflow so users can go from `ato` design to manufacturable outputs without leaving atopile.

Primary goals:
- Run AI placement/routing from the manufacturing panel and CLI.
- Preserve atopile/KiCad round-trippability and reproducibility.
- Export manufacturing artifacts (`gerber`, BOM, pick-and-place, 3D) from the generated layout.
- Support constraints from project config and graph metadata.

## 2. Non-goals

- Replacing existing manual KiCad workflow.
- Implementing custom PCB solving locally.
- Depending on undocumented/private provider APIs for production paths.

## 3. External Facts and Constraints (from vendor sites)

### Quilter
- Quilter Help Center states Quilter does **not** offer public API access.
- Quilter is currently web-app workflow first (upload files, configure parameters/constraints, review candidates, download outputs).
- Quilter supports constraints via UI and CAD-encoded rules/objects (for example keepouts, net widths, pre-placed components).

Implication:
- Direct programmatic Quilter integration is blocked unless private API access is granted.

### DeepPCB
- DeepPCB publicly advertises API access and API key-based integration.
- DeepPCB advertises support for major EDA tool flows and constraints.
- The blog API documentation link (`https://api.deeppcb.ai/...`) currently resolves to 404 from automated fetch.

Implication:
- DeepPCB is the primary near-term automation path, but endpoint-level contracts must be validated with vendor during implementation.

## 4. Product Strategy

- Implement a provider abstraction now.
- Ship DeepPCB as the first provider.
- Add Quilter as:
  - `mode=manual-export` (generate upload package + instructions), or
  - `mode=api` only when private/public API access is confirmed.

This prevents architecture rework when Quilter API status changes.

## 5. Proposed Architecture

## 5.1 Backend modules

Add:
- `src/atopile/server/domains/autolayout/models.py`
- `src/atopile/server/domains/autolayout/providers/base.py`
- `src/atopile/server/domains/autolayout/providers/deeppcb.py`
- `src/atopile/server/domains/autolayout/providers/quilter_manual.py`
- `src/atopile/server/domains/autolayout/service.py`

Integrate:
- `src/atopile/server/domains/actions.py` (new websocket actions)
- `src/atopile/server/routes/manufacturing.py` (optional REST parity)
- `src/atopile/config.py` (project/build-level autolayout config schema)

## 5.2 Frontend modules

Integrate:
- `src/ui-server/src/components/manufacturing/ManufacturingPanel.tsx`
- `src/ui-server/src/components/manufacturing/types.ts`
- `src/ui-server/src/store/index.ts`

## 5.3 CLI

Add:
- `src/atopile/cli/autolayout.py`
- register in `src/atopile/cli/cli.py`

Suggested commands:
- `ato autolayout run --build <target> --provider deeppcb`
- `ato autolayout status <job-id>`
- `ato autolayout apply <job-id> [--candidate <id>]`

## 5.4 Provider interface

```python
class AutolayoutProvider(Protocol):
    name: str
    capabilities: ProviderCapabilities

    def submit(job: SubmitRequest) -> ProviderJobRef: ...
    def status(ref: ProviderJobRef) -> ProviderJobStatus: ...
    def list_candidates(ref: ProviderJobRef) -> list[Candidate]: ...
    def download_candidate(ref: ProviderJobRef, candidate_id: str, out_dir: Path) -> DownloadResult: ...
    def cancel(ref: ProviderJobRef) -> None: ...
```

## 5.5 Job model

Persisted `AutolayoutJob`:
- `job_id`
- `project_root`
- `build_target`
- `provider`
- `state` (`queued|running|awaiting_selection|completed|failed|cancelled`)
- `provider_job_ref`
- `input_fingerprint`
- `candidate_ids`
- `selected_candidate_id`
- `artifacts_dir`
- `error`
- timestamps

Persistence option:
- Add a SQLite table similar to build history.

## 6. End-to-End Workflow

## 6.1 "One-click to manufacturing" (DeepPCB)

1. Build base design to ensure fresh layout + netlist context:
   - `ato build --build <target> --target build-design`
2. Package provider input from build target:
   - KiCad board/project/schematic bundle + constraint JSON.
3. Submit autolayout job to provider.
4. Poll status and stream progress to UI.
5. Fetch candidate list and rank by policy (default: provider recommended).
6. Download selected candidate.
7. Apply candidate into `config.build.paths.layout` (atomic replace + backup).
8. Validate and export manufacturing files:
   - `ato build --build <target> --target mfg-data --frozen`
9. Surface outputs in existing manufacturing panel.

## 6.2 Quilter path (until API exists)

1. Generate Quilter-compatible package from current target.
2. Open packaged directory + checklist/instructions in UI.
3. User uploads manually in Quilter app.
4. User imports returned board file back into layout path.
5. Run `mfg-data --frozen` locally.

## 7. Input/Output File Contract

## 7.1 Input (v1 scope: KiCad-first)

Required:
- `<target>.kicad_pcb`
- `<target>.kicad_sch` (if available)
- project file metadata when present
- constraints payload generated by atopile

Optional:
- stackup/fab preference overrides
- locked component regions and keepouts

## 7.2 Output

Expected output from provider apply step:
- updated KiCad PCB file (and project metadata if provider modifies it)

Expected output from atopile export step:
- `.gerber.zip`
- `.bom.csv`, `.bom.json`
- `.pick_and_place.csv`, `.jlcpcb_pick_and_place.csv`
- `.pcba.step`, `.pcba.glb`
- `.pcb_summary.json`

## 8. Constraints Model

Introduce optional config block under build target:

```yaml
builds:
  default:
    entry: app.ato:App
    autolayout:
      provider: deeppcb
      objective: "balanced"
      candidate_count: 6
      auto_apply: false
      constraints:
        lock_preplaced_components: true
        preserve_keepouts: true
        preserve_existing_copper: false
        net_classes:
          - name: power
            nets: ["VIN", "VBAT", "3V3"]
            min_width_mm: 0.4
            min_clearance_mm: 0.2
        differential_pairs:
          - p: "USB_DP"
            n: "USB_DN"
            target_impedance_ohm: 90
            length_match_tolerance_mm: 0.5
```

Mapping rules:
- Keepouts from KiCad are exported as hard constraints.
- Pre-placed components are locked by default.
- Net names from `has_net_name` feed routing constraints.
- Differential pairs from graph traits map to provider pair constraints when available.

## 9. Internal API Contract (WebSocket-first)

Add actions:
- `startAutolayout`
- `getAutolayoutStatus`
- `listAutolayoutCandidates`
- `selectAutolayoutCandidate`
- `applyAutolayoutCandidate`
- `cancelAutolayout`
- `exportQuilterPackage`

Event stream:
- `autolayout_changed`
- `autolayout_candidate_ready`
- `autolayout_failed`

REST parity (optional):
- `POST /api/manufacturing/autolayout/start`
- `GET /api/manufacturing/autolayout/{job_id}`
- `POST /api/manufacturing/autolayout/{job_id}/apply`
- `POST /api/manufacturing/autolayout/{job_id}/cancel`

## 10. Security and Secrets

- API keys from env (`ATO_DEEPPCB_API_KEY`) for server process.
- Optional extension secret-store support in later phase.
- Never store keys in `ato.yaml` or logs.
- Redact provider request headers/payload in user-facing logs.

## 11. Observability

Track:
- provider submit latency
- provider solve time
- candidate count
- apply success rate
- frozen validation pass/fail
- export success rate

Add build-linked log events so autolayout appears in existing logs UI.

## 12. Complexity Estimate

## 12.1 Engineering complexity

- DeepPCB provider integration: Medium-High
- Constraint mapping: High
- UI/UX integration in manufacturing panel: Medium
- Quilter automation via API: Blocked (current)

## 12.2 Time estimate (single team)

- Phase 0 (contract spike, provider sandbox): 1 week
- Phase 1 (DeepPCB MVP: submit/status/apply/export): 2-3 weeks
- Phase 2 (constraints depth + candidate UX + retries): 2-4 weeks
- Phase 3 (hardening, docs, rollout): 1-2 weeks

Total: 6-10 weeks for production-grade DeepPCB flow.

## 13. Testing Plan

## 13.1 Test strategy

Pyramid:
- Unit tests for config parsing, mapping, provider adapters.
- Contract tests for provider HTTP client behavior.
- Integration tests for websocket actions + job lifecycle.
- E2E tests for manufacturing flow with golden boards.

## 13.2 Unit tests

Backend:
- Parse/validate `autolayout` config schema.
- Constraint translation:
  - keepouts
  - net classes
  - differential pairs
  - locked component mapping
- Candidate scoring/ranking logic.
- Atomic apply/rollback on file replacement.
- Secret redaction in logs.

Frontend:
- State transitions in manufacturing store for autolayout states.
- Candidate selection UI logic.
- Error and retry UX behavior.

## 13.3 Contract tests (provider)

Use `respx`/`httpx` mocks (or equivalent):
- submit success
- submit validation error
- polling transitions
- timeout/retry/backoff
- malformed payload handling
- candidate download and checksum validation

For DeepPCB specifically:
- keep endpoint paths and required fields in one versioned adapter fixture.
- fail fast on schema drift with explicit error messages.

## 13.4 Integration tests (server)

Add tests for websocket actions in `src/atopile/server/routes/tests.py` or dedicated module:
- `startAutolayout` creates job and returns `job_id`.
- `getAutolayoutStatus` reflects progression.
- `applyAutolayoutCandidate` updates layout and triggers export pipeline.
- cancellation and idempotency behavior.

## 13.5 End-to-end tests

Add E2E scenarios under `test/end_to_end/`:
- Happy path:
  - run autolayout
  - apply candidate
  - run `mfg-data --frozen`
  - verify expected artifacts exist
- Failure path:
  - provider timeout
  - candidate apply failure (corrupt file)
  - frozen mismatch detection
- Reproducibility:
  - same input + same candidate -> stable artifact set

## 13.6 Performance and reliability tests

- 10 concurrent autolayout jobs across sample projects.
- provider polling load bounds.
- large-board scenario near provider limits.
- retry storm protection (circuit breaker + max retry cap).

## 13.7 Manual UAT checklist

- Start autolayout from manufacturing panel.
- Observe stage updates in logs panel.
- Compare at least two candidates.
- Apply selected candidate.
- Export manufacturing package.
- Open output in KiCad and verify board integrity.

## 14. Rollout Plan

- Feature flag: `ATO_ENABLE_AUTOLAYOUT`.
- Provider flag: `ATO_AUTOLAYOUT_PROVIDER=deeppcb|quilter_manual`.
- Internal alpha -> selected projects -> default on.

## 15. Open Risks and Questions

- DeepPCB endpoint and schema availability: docs link currently returns 404 from automation fetch.
- Quilter API availability: currently no public API.
- Constraint coverage mismatch between atopile model and provider capabilities.
- IP/data-handling requirements for enterprise users (cloud vs private deployment).

## 16. Acceptance Criteria (MVP)

- User can run autolayout from atopile UI without leaving tool.
- At least one candidate can be applied to target layout path.
- `mfg-data --frozen` passes and exports artifacts from applied candidate.
- Failures are recoverable with actionable messages.
- No secret leakage in logs/config/artifacts.
