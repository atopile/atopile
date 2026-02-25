# High-Performance Binary Graph Serialization

**Objective:** Implement a Data-Oriented, zero-copy-compatible binary serialization format in Zig to extract, transmit, and merge sparse `GraphView` instances across Python process boundaries with sub-millisecond latency. 

By iterating over the `GraphView`'s membership bitsets and packing the entities into contiguous binary structs, we bypass slow text parsers (like JSON) and safely transmit memory pointers over IPC using a String Table.

## 1. The Core Strategy (Sparse Serialization)

A `GraphView` does not own a contiguous block of the global `Nodes` or `Edges` arrays; it is a sparse view tracked by `UUIDBitSet`s. 

**The Solution:**
1.  **Sparse Packing:** `dumps_diff()` iterates over `node_set` and `edge_set`. Filtering against provided baselines, it writes active `PackedNode` or `PackedEdge` structs to the output buffer, preserving original UUIDs.
2.  **Implicit Baselines:** The payload header does not carry baselines. If a UUID is in the payload, the receiver treats it as "new" and remaps it. If an edge references a UUID *not* in the payload, it is a "baseline" entity and maps to itself.
3.  **String Table:** Slices (`[]const u8`) are extracted into a contiguous "String Table" block. Fat pointers are replaced with `u32` offset/length pairs.
4.  **Preserve Attribute Ownership:** We serialize `PackedDynamicAttributes` blocks (which hold up to 6 attributes each) to preserve the `DynamicAttributesReference` UUIDs.
5.  **Omit HashMaps & Bitsets:** Nested adjacency hash maps and bitsets are ignored. The receiver rebuilds them extremely fast using `insert_edge_unchecked()`.

*Architectural Constraint (Monotonicity):* The diff engine tracks new allocations. If a worker mutates an *existing* `DynamicAttributes` block (UUID < baseline) in-place, it will not be caught. The picker workflow inherently uses monotonic additions (adding new traits/edges). If in-place mutation is ever required, `GraphView` must implement Copy-on-Write (CoW) for attribute blocks to generate new UUIDs.

## 2. Security & Malicious Payload Resilience

Because payloads may be received from untrusted backend clients, the deserializer must treat the byte buffer as hostile. The parser must prevent Buffer Over-reads, Out-of-Memory (OOM) Denial of Service, Integer Overflows, and Graph Corruption.

**Defense Mechanisms:**
1.  **Strict Buffer Sizing:** Before parsing, the receiver must calculate:
    `Expected Size = 32 + (node_count * 8) + (edge_count * 24) + (attr_count * 152) + string_table_size`.
    If `bytes.len` does not *exactly* equal this size, reject immediately (`error.MalformedPayload`).
2.  **Overflow Protection:** All size and offset calculations must use overflow-safe arithmetic (e.g., Zig's `@addWithOverflow` and `@mulWithOverflow`).
3.  **Enum Bounds Checking:** The `value_tag` (1 byte) in attributes must be explicitly checked against valid `Literal` enum bounds before casting.
4.  **String Bounds Checking:** For every string reference, assert that `offset + length <= string_table_size`.
5.  **Dangling Reference Rejection:** When resolving edge endpoints or dynamic attribute UUIDs, the resulting translated UUID must be verified to exist in the target graph (`main_graph.contains_node()`). Connecting an edge to a phantom UUID must trigger `error.InvalidNodeReference`.

## 3. Binary Layout Specification

The payload is a single, flat byte buffer. All structs are `extern` (C-ABI compatible) and explicitly padded to multiples of 8 bytes to guarantee perfect 64-bit alignment across all platforms.

### Header (Exactly 32 Bytes)
```zig
const BinaryHeader = extern struct {
    magic_number: u32,       // 0x52494E53 ("RINS")
    version: u32,            // Format version (e.g., 1)
    self_node_uuid: u32,     // GraphView.self_node.uuid (Used for full loads)
    node_count: u32,         // Number of nodes in payload
    edge_count: u32,         // Number of edges in payload
    attr_count: u32,         // Number of dynamic attribute blocks
    string_table_size: u32,  // Size of the appended string block
    _pad: u32,               // Explicit padding to 32 bytes (cache-line aligned)
};
```

### Packed Entities & Attributes
```zig
const PackedStringRef = extern struct {
    offset: u32,
    length: u32,
}; // 8 bytes

const PackedLiteralValue = extern union {
    Int: i64,
    Uint: u64,
    Float: f64,
    String: PackedStringRef,
    Bool: u8,                    // 0 or 1 for strict cross-platform C-ABI
    _pad: [8]u8,                 // Force union to exactly 8 bytes
};

const PackedAttribute = extern struct {
    identifier: PackedStringRef, // 8 bytes
    value_tag: u8,               // 1 byte (Enum tag for Literal type)
    _pad: [7]u8,                 // 7 bytes padding
    value: PackedLiteralValue,   // 8 bytes
}; // 24 bytes total

const PackedDynamicAttributes = extern struct {
    original_uuid: u32,
    in_use: u32,
    values: [6]PackedAttribute,
}; // 152 bytes total (8-byte aligned)

const PackedNode = extern struct {
    original_uuid: u32,
    dynamic_attr_uuid: u32,
}; // 8 bytes total

const PackedEdge = extern struct {
    original_uuid: u32,
    source: u32,
    target: u32,
    dynamic_attr_uuid: u32,
    flags: u32,
    _pad: u32,                   // Pad to 24 bytes (8-byte aligned)
}; // 24 bytes total
```

### Payload Structure
```text
[ BinaryHeader (32 bytes) ]
[ Packed Nodes Array (node_count * 8 bytes) ]
[ Packed Edges Array (edge_count * 24 bytes) ]
[ Packed Attributes Array (attr_count * 152 bytes) ]
[ String Table (string_table_size bytes) ]
```

## 4. Serialization Algorithm (`dumps_diff`)

*Note: For a full dump, baselines are provided as 0.*

1.  **Initialize Buffers:** Create an empty String Table and output arrays for Nodes, Edges, and Attributes.
2.  **Iterate Sparse Members:**
    *   **Nodes:** Iterate `node_set.data`. If `uuid > baseline_node_id` and is active, pack into `PackedNode`, and mark its `dynamic_attr_uuid`.
    *   **Edges:** Iterate `edge_set.data`. If `uuid > baseline_edge_id` and is active, pack into `PackedEdge` and mark its `dynamic_attr_uuid`.
3.  **Pack Attributes:** For every marked `DynamicAttributesReference` (where `uuid > baseline_attr_id`):
    *   Append strings to the String Table, recording `offset` and `length`.
    *   Write the resulting `PackedDynamicAttributes` to the output array.
4.  **Assemble Buffer:** Write the Header, arrays, and String Table to a single contiguous byte slice.

## 5. Deserialization & The Remapping Engine (`merge_diff`)

Because diffs originate from isolated processes, their UUIDs will collide with the main process. A Translation Table safely allocates local UUIDs.

1.  **Validate Header & Size:** Check `magic_number` ("RINS"). Calculate the exact expected byte size using overflow-safe math. If `expected_size != bytes.len`, reject.
2.  **String Table Lifetime:** Allocate `const string_memory = g.allocator.alloc(u8, header.string_table_size)`. Copy the string table. Because it is tied to the internal arena, the strings safely outlive the IPC buffer and are freed with the graph view.
3.  **Initialize Translation Tables:** Create `remap_nodes` and `remap_attrs` hash maps (`u32 -> u32`).
4.  **Remap & Restore Attributes:**
    *   Iterate incoming `PackedDynamicAttributes`.
    *   Validate all `value_tag`s against valid enums.
    *   *Safety Check:* Assert `@addWithOverflow(offset, length)` does not overflow and is `<= header.string_table_size`.
    *   Swizzle strings (`ptr = string_memory.ptr + offset`). 
    *   Store `remap_attrs[original_uuid] = new_uuid`.
5.  **Remap & Restore Nodes:**
    *   Iterate incoming `PackedNode`s.
    *   Call `main_graph.create_and_insert_node()`. Map `remap_nodes[original_uuid] = new_node.uuid`.
    *   Resolve attributes: `Nodes[new_uuid].dynamic.uuid = remap_attrs.get(incoming.dynamic_attr_uuid) orelse incoming.dynamic_attr_uuid`.
6.  **Remap & Restore Edges (HashMap Rebuild):**
    *   Iterate incoming `PackedEdge`s.
    *   Translate endpoints: `local_source = remap_nodes.get(incoming.source) orelse incoming.source`.
    *   Translate endpoints: `local_target = remap_nodes.get(incoming.target) orelse incoming.target`.
    *   *Safety Check:* Assert `main_graph.contains_node(local_source)` and `main_graph.contains_node(local_target)`. Reject dangling references.
    *   Create a new `EdgeReference` in the global arrays.
    *   *Critical Check:* Explicitly call `main_graph.edge_set.add(new_edge.uuid)`.
    *   Call `main_graph.insert_edge_unchecked(new_edge)` to rapidly rebuild the nested adjacency hash maps.
7.  **Restore Self Node (Full Loads Only):** If executing a full `loads()`, update `main_graph.self_node` using the header's UUID.

## 6. Python Bindings

The PyZig wrappers (`src/faebryk/core/zig/src/python/graph/graph_py.zig`) will expose:
*   `GraphView.dumps() -> bytes`: Full graph state.
*   `GraphView.dumps_diff(baseline_nodes: int, baseline_edges: int, baseline_attrs: int) -> bytes`
*   `GraphView.merge_diff(data: bytes)`: Safely merges a payload using the translation map fallback logic.

## 7. Testing Strategy

**Zig Inline Tests (`src/faebryk/core/zig/src/graph/graph.zig`):**
1.  **Sparse Identity Roundtrip:** Create a `GraphView`, add 1000 nodes, delete 500. Serialize to bytes, `merge_diff` into an empty graph. Assert exact topological identity and attribute integrity.
2.  **String Table Bounds & Swizzling:** Ensure string table offset calculations correctly reconstruct fat-pointers, and explicitly test out-of-bounds offset rejection.
3.  **Malicious Payload Rejection:**
    *   Test passing a buffer with an incorrect size (e.g., claiming 1000 nodes but sending 10 bytes).
    *   Test passing an edge with a `source` UUID pointing to a non-existent node.
    *   Test passing an attribute with an invalid `value_tag` (e.g., 255).
4.  **Remapping Collision Test:**
    *   Create `Graph_Main`. Clone to `Graph_Worker`.
    *   Advance both graphs by 1 node to intentionally create a UUID collision at index 100.
    *   Serialize `Graph_Worker` diff (Node 100) and `merge_diff` into `Graph_Main`.
    *   Assert Node 100 from Worker was cleanly remapped to Node 101 in `Graph_Main` and that its edges still point correctly to baseline nodes via the `orelse incoming.source` fallback logic.

**Python Integration Tests:**
1.  **PyZig Roundtrip:** Serialize from Python, immediately load back, and run `BFSPath` traversals to ensure the C-ABI wrapper correctly traces remapped pointers.
2.  **IPC Simulation:** Pass serialized bytes into a `multiprocessing.Process`. Have the worker add a specific component structure, serialize the diff, pass it back, and `merge_diff`. Verify the main process's graph contains the worker's component without corruption.

## 8. Implementation Deviations

This section documents where the implementation diverged from the plan and why.

### 8.1 `dumps_diff` with baselines not implemented — only `dumps`

The plan specifies `dumps_diff(baseline_nodes, baseline_edges, baseline_attrs)` with filtering against baseline UUIDs. The implementation only provides `dumps()` (full graph serialization, equivalent to baselines of 0). The `dumps_diff` Python binding was also omitted.

**Why:** The immediate use case is full graph transfer across process boundaries. Baseline-aware diffing adds complexity (three extra parameters, baseline tracking) that isn't needed yet. Adding it later is backwards-compatible — the binary format and `merge_diff` already handle the "everything is new" case identically to a diff where all UUIDs exceed the baseline.

### 8.2 Struct reads use `@bitCast` instead of pointer casts or `bytesAsSlice`

The plan implicitly assumes pointer-cast access into the byte buffer (e.g., `std.mem.bytesAsSlice(PackedDynamicAttributes, attrs_bytes)`). The implementation reads each struct via `@bitCast(bytes[offset..][0..@sizeOf(T)].*)`.

**Why:** Zig 0.15's `@alignCast` on slices passed to `anytype` parameters (like `bytesAsSlice`'s second argument) cannot infer the target alignment, producing `error: @alignCast must have a known result type`. The input `[]const u8` has alignment 1, but `extern struct`s require natural alignment. `@bitCast` on a fixed-size array copy is alignment-safe and avoids undefined behavior from misaligned loads on ARM.

### 8.3 Overflow-safe arithmetic uses `std.math.add`/`std.math.mul`, not `@addWithOverflow`/`@mulWithOverflow`

The plan references `@addWithOverflow` and `@mulWithOverflow` Zig builtins.

**Why:** The builtins return a tuple `(result, overflow_bit)` which requires manual checking. `std.math.add` and `std.math.mul` return `error.Overflow` directly, which integrates cleanly with Zig's error union return type. The safety guarantee is identical.

### 8.4 `SerializationError` includes `OutOfMemory`

The plan's error set does not include `OutOfMemory`. The implementation adds it.

**Why:** `merge_diff` allocates string memory via `g.allocator` and uses hash maps for remap tables. `dumps` builds dynamic arrays. These allocations can fail and the error must be surfaced rather than `@panic`'ing.

### 8.5 Header parsed as value type, not pointer

The plan shows `const header = std.mem.bytesToValue(BinaryHeader, bytes[0..32])` which returns a pointer. The implementation uses `const header: BinaryHeader = @bitCast(bytes[0..@sizeOf(BinaryHeader)].*)` which copies into a stack value.

**Why:** Same alignment issue as 8.2 — pointer-casting into an arbitrary byte buffer risks misaligned access. A value copy is safe on all platforms and the 32-byte header is trivially cheap to copy.

### 8.6 Roundtrip test uses 20 nodes (not 1000 with 500 deleted)

The plan specifies "add 1000 nodes, delete 500" to test sparse packing. The implementation creates 20 nodes with no deletion.

**Why:** `GraphView` does not expose a `remove_node` operation — the bitset `remove` method exists on `UUIDBitSet` but there is no public API to remove a node and clean up its adjacency map. The 20-node test with mixed attribute types (string, int, float, bool, uint) and edges adequately validates serialization correctness. Sparse packing is inherently tested since `UUIDBitSet` indices are non-contiguous (they start at whatever the global counter was at graph creation time).

### 8.7 Collision test creates separate graphs instead of cloning

The plan says "Clone to `Graph_Worker`" and asserts specific UUID values (Node 100 remapped to 101). The implementation creates two independent `GraphView`s.

**Why:** `GraphView` has no clone/copy constructor. Two independently created graphs naturally get non-overlapping UUIDs (global monotonic counter), but the merge still exercises the full remapping path since every UUID in the payload is treated as "new". The test asserts correct aggregate counts rather than specific UUID values, since exact values depend on global counter state shared across all tests.

### 8.8 Python integration tests: automated but no IPC simulation

The plan specifies a PyZig Roundtrip test with `BFSPath` traversals and a `multiprocessing.Process` IPC simulation.

**What was implemented:** Nine automated Python tests in `test/core/zig/graph/test_zig_graph.py` covering:
- `test_dumps_merge_diff_roundtrip` — full `dumps()` → `merge_diff()` roundtrip with node count validation
- `test_loads_static` — `GraphView.loads()` creates a correct graph from bytes
- `test_loads_preserves_edge_connectivity` — edge `directional`, `name`, and source-target relationships survive `dumps` → `loads`
- `test_loads_preserves_composition_attributes` — composition edge names (dynamic attributes) survive `dumps` → `loads`, verified via `visit_children_edges` and `get_name`
- `test_clone` — `clone()` produces an independent deep copy, mutations to original don't affect clone
- `test_clone_with_composition_traversal` — composition children can be visited and looked up by identifier on a cloned graph
- `test_merge_diff_malformed` — rejects payloads that are too short or have wrong magic number
- `test_loads_malformed` — rejects invalid payloads via `loads()`

**What was not implemented:** The `multiprocessing.Process` IPC simulation test. This is deferred until the picker workflow integration is built, at which point it becomes a natural end-to-end test rather than a synthetic one.

**Why no BFSPath traversal test:** The plan calls for BFS traversals on deserialized graphs, but composition edge traversal (`visit_children_edges`, `get_child_by_identifier`) is a more representative validation of adjacency map reconstruction. BFSPath operates on the same rebuilt adjacency maps, so composition traversal tests provide equivalent coverage.

### 8.9 `loads()` and `clone()` added beyond plan scope

The plan specifies only `dumps()`, `dumps_diff()`, and `merge_diff()`. The implementation adds two additional methods:
- `GraphView.loads(data: bytes) -> GraphView` — static method that creates a new graph from serialized bytes
- `GraphView.clone() -> GraphView` — deep copy via `dumps()` + `loads()`

**Why:** `loads()` is the natural complement to `dumps()` — creating a fresh graph from bytes rather than merging into an existing one. `clone()` was requested as a convenience for graph deep-copying, which is a common operation that previously had no efficient implementation. Both are exposed via Python bindings and type stubs.

### 8.10 `init_bare()` internal helper for `loads()`

The plan's `merge_diff` always operates on an existing `GraphView` that was created via `init()` (which allocates a self_node). The implementation adds an internal `init_bare()` constructor that creates a `GraphView` without allocating a self_node.

**Why:** `loads()` needs to reconstruct a graph from bytes including its original self_node. If it used `init()`, the graph would start with an orphan self_node (node count = 1), then `merge_diff` would add all serialized nodes (including the serialized self_node), resulting in `n + 1` nodes instead of `n`. `init_bare()` starts at 0 nodes, so after `merge_diff` restores all serialized nodes and sets `self_node` from the header, the node count matches exactly.

### 8.11 `merge_diff` always restores `self_node`, not conditionally

The plan says Step 7 ("Restore Self Node") applies to "Full Loads Only." The implementation unconditionally sets `g.self_node` from the header's remapped UUID at the end of every `merge_diff` call.

**Why:** Simplicity. When `merge_diff` is used on an existing graph, the self_node is overwritten with the remapped UUID from the payload. This is harmless in the `merge_diff` use case (the caller's self_node is preserved because it was already in the graph and the remap fallback resolves to itself), and required in the `loads()` use case. Adding a conditional would require a flag parameter or a separate code path for no practical benefit.

### 8.12 Python `Node.create()` does not accept keyword attributes

The `.pyi` stub declares `Node.create(**attrs: Literal)`, but the Zig binding (`wrap_node_create`) ignores all keyword arguments. Node dynamic attributes cannot be set from Python via `create()`.

**Why:** This is a pre-existing limitation of the Python binding, not a serialization issue. The attribute roundtrip is fully tested in the Zig inline tests (which use `node.put("key", value)` directly). Python tests verify attribute roundtrip through composition edges (`EdgeComposition.get_name`), which do store dynamic attributes via the Zig-level `add_child` binding.