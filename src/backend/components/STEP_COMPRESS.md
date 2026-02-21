# STEP Binary Compression Investigation Plan

## Goal

Build and benchmark a custom binary representation for STEP files that reduces entropy before `zstd`, to estimate the practical and theoretical compression limits for stage-1 model storage.

## Scope

1. Input: `*.step` / `*.stp` component model files (stage-1 artifacts).
2. Output: compressed payload suitable for object-store storage.
3. Primary metric: total bytes on disk.
4. Secondary metrics: compress/decompress wall time and implementation complexity.
5. This doc explicitly allows impractical ideas if they help define upper bounds.

## Current State In Repo

1. Current storage path is raw bytes -> `zstd` -> object store.
2. Existing STEP handling is minimal:
   - `/Users/narayanpowderly/projects/atopile/src/faebryk/libs/kicad/other_fileformats.py`
   - `C_kicad_model_file` validates STEP header and extracts limited header metadata.
3. There is no full STEP decoder/parser in-repo yet.
4. Recent corpus benchmarking indicates:
   - `zstd -10` is a strong practical baseline.
   - higher levels improve size but cost more CPU.
   - long mode and trained dictionaries did not show compelling wins for STEP in current corpora.

## Success Criteria

1. Produce at least one binary transform that round-trips to the same STEP semantics (preferably byte-identical for v1).
2. Beat baseline `zstd -10` on holdout corpus by a meaningful margin.
3. Quantify both:
   - practical winner (size + speed balance)
   - theoretical winner (size-priority, even if slow/complex)
4. Document whether complexity is justified for production adoption.

## Investigation Tracks

### Track A: Lossless Lexical IR (No External CAD Kernel)

1. Implement a strict STEP lexer for ISO-10303-21 exchange structure.
2. Parse into normalized token streams:
   - entity ids
   - entity type names
   - references
   - strings
   - numerics
   - punctuation/opcodes
3. Build compact binary blocks:
   - string table with dedup
   - entity type table with dedup
   - varint-coded references and ids
   - numeric stream (typed encoding)
   - opcode stream
4. Re-emit canonical STEP text for round-trip checks.
5. Compress binary container with `zstd`.

### Track B: Semantic CAD IR (Off-the-Shelf Decoder)

1. Evaluate external STEP decoders (priority order by viability):
   - OpenCascade-based Python bindings (for full semantic decode)
   - STEPcode bindings/tools (if practical in environment)
   - any lightweight parser with stable AST and re-serializer
2. If viable, export a canonical semantic IR:
   - normalized topology/geometry record ordering
   - deduplicated repeated structures
   - compact binary encoding of typed fields
3. Compress semantic IR with `zstd`.
4. Use this track mainly to estimate upper bound, not immediate production path.

### Track C: Theoretical Lower-Bound Probing

1. Entropy analysis on STEP token classes:
   - Shannon entropy estimates per stream
   - contribution by stream (strings, numerics, refs, opcodes)
2. Test stronger but impractical encodings:
   - aggressive numeric transforms
   - stream-specific coding choices
   - optional multi-stage preprocessing before `zstd`
3. Use results to estimate how close practical implementations are to theoretical ceiling.

## Corpus Plan

1. Build large corpus from local projects:
   - deduplicate by SHA-256
   - track source path and size
2. Use deterministic train/test splits by hash.
3. Run two suites:
   - component-scale files only (primary production relevance)
   - full corpus including large board-level STEP files (stress case)
4. Minimum target for each benchmark run:
   - at least 300 train files
   - at least 70 holdout files

## Benchmark Matrix

1. Baselines:
   - raw + `zstd -10`
   - raw + `zstd -14`
   - raw + `zstd -16`
2. Candidates:
   - lexical IR v0 + `zstd -10/-14/-16`
   - lexical IR v1 + `zstd -10/-14/-16`
   - semantic IR (if decoder available) + `zstd -10/-14/-16`
3. Report:
   - compressed bytes
   - ratio vs raw
   - delta vs baseline
   - compress ms
   - decompress ms
   - memory footprint estimate
4. Keep one reproducible JSON result artifact per run.

## Binary Format Sketch (Initial)

1. File header:
   - magic (`ASTEPBIN`)
   - version
   - flags
   - checksum
2. Sections (length-prefixed):
   - metadata
   - entity type table
   - string table
   - numeric table/stream
   - reference stream
   - opcode/token stream
3. All integers varint-encoded.
4. Section-local checksums for corruption isolation.
5. Deterministic serialization for stable hashing and tests.

## Round-Trip Test Levels

1. Level 0: binary -> binary decode equality.
2. Level 1: STEP text byte-equality after encode/decode (strict).
3. Level 2: canonical STEP equality (allow cosmetic text differences).
4. Level 3: semantic equality through external CAD kernel, if available.

## Risks

1. STEP grammar complexity is high; parser edge cases can consume time.
2. Decoder dependencies may be heavy and hard to package.
3. Gains may remain small relative to plain `zstd -14/-16`.
4. Canonicalization may accidentally break uncommon STEP variants.

## Decision Gates

1. Gate A (continue to production prototype):
   - at least 10% size win vs `zstd -10` on component-scale holdout
   - no catastrophic speed regressions for decompression
2. Gate B (consider replacing current default):
   - at least 5% size win vs best plain-zstd policy selected for production
   - manageable implementation and maintenance complexity
3. If gates fail:
   - keep plain-zstd policy
   - archive findings and revisit only with new ideas or tools

## Execution Plan

1. Phase 1: Corpus + baseline benchmark harness.
2. Phase 2: Lexical parser and IR v0 (lossless, deterministic).
3. Phase 3: IR v1 optimizations (string/ref/numeric stream tuning).
4. Phase 4: External decoder feasibility spike.
5. Phase 5: Final comparison report and go/no-go recommendation.

## Deliverables

1. `step_ir` prototype module (parser + encoder + decoder).
2. Bench scripts and reproducible JSON outputs.
3. Compression comparison report with recommendation.
4. Migration plan if production adoption is justified.
