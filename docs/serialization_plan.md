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