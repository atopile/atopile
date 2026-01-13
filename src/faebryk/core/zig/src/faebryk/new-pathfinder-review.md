# New Pathfinder vs Pathfinder Notes

These notes capture the differences and potential regressions to review later.

## Potential Behavior Differences / Regressions

- [x] `filter_path_by_same_node_type` is implicitly enforced by type-path selection.
  - New behavior only returns paths whose `TypeElementList` matches the start node, which keeps end node types aligned.

- [x] Sibling traversal should be blocked by `child_identifier` checks during down traversal.
  - Paths that attempt child->parent->child across different identifiers should not be returned.

- Path minimality is no longer guaranteed.
  - Old behavior returned BFS-order paths (shortest-first).
  - New behavior dedups by end node and can keep a longer path while discarding a shorter one discovered later.

- [x] Down-traverse is constrained to the current `child_identifier` (intended).
  - After a horizontal traversal, the new pathfinder only descends into the child with the same identifier.
  - This prunes paths that hop to a different child name after a parent-level horizontal move.

- [x] Shallow link filtering now uses type-path length instead of edge depth (no known regressions so far).
  - Old rule: shallow link invalid when `depth > 0`.
  - New rule: shallow link invalid when `current_type_path_len > start_type_path_len`.

## Algorithm / Data Structure Differences

- Old pathfinder: single BFS over composition + interface edges with filter chain.
- New pathfinder: horizontal BFS over interface edges, then explicit up/down traversal using `TypeElementList`/`TypePathList`.
- New pathfinder stores full instance paths per type-path key and dedups by end node.
- New pathfinder returns only paths at the same hierarchy level as the start node.

## Pros / Cons / Performance Notes

- Old pathfinder:
  - Pros: explicit filter semantics, shortest paths, robust to missing child identifiers.
  - Cons: can explore many paths; higher CPU/memory cost.

- New pathfinder:
  - Pros: hierarchy-aware pruning; likely faster on large graphs.
  - Cons: semantic changes listed above; path length not guaranteed minimal.
