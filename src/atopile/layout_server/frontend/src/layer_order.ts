const IN_ROOT_RE = /^In(\d+)$/i;

const SUFFIX_PRIORITY = new Map<string, number>([
    ["Cu", 0],
    ["Drill", 1],
    ["Fab", 2],
    ["Mask", 3],
    ["Nets", 4],
    ["PadNumbers", 5],
    ["Paste", 6],
    ["SilkS", 7],
    ["User", 8],
]);

function naturalCompare(a: string, b: string): number {
    return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" });
}

function rootKey(root: string): [number, number, string] {
    if (root === "F") return [0, 0, root];
    const inMatch = root.match(IN_ROOT_RE);
    if (inMatch) return [1, Number.parseInt(inMatch[1]!, 10), root];
    if (root === "B") return [2, 0, root];
    return [3, 0, root];
}

function paintRootKey(root: string): [number, number, string] {
    // Paint order is bottom-to-top so top copper ends up visually on top.
    // B first, then inner layers from deepest to nearest-top, then F.
    if (root === "B") return [0, 0, root];
    const inMatch = root.match(IN_ROOT_RE);
    if (inMatch) return [1, -Number.parseInt(inMatch[1]!, 10), root];
    if (root === "F") return [2, 0, root];
    return [3, 0, root];
}

function splitLayerName(layerName: string): { root: string; suffix: string } {
    const dotIdx = layerName.indexOf(".");
    if (dotIdx < 0) {
        return { root: layerName, suffix: "" };
    }
    return {
        root: layerName.substring(0, dotIdx),
        suffix: layerName.substring(dotIdx + 1),
    };
}

export function compareLayerNames(a: string, b: string): number {
    const aSplit = splitLayerName(a);
    const bSplit = splitLayerName(b);
    const aRoot = rootKey(aSplit.root);
    const bRoot = rootKey(bSplit.root);

    if (aRoot[0] !== bRoot[0]) return aRoot[0] - bRoot[0];
    if (aRoot[1] !== bRoot[1]) return aRoot[1] - bRoot[1];
    const rootNameCmp = naturalCompare(aRoot[2], bRoot[2]);
    if (rootNameCmp !== 0) return rootNameCmp;

    const aSuffixPriority = SUFFIX_PRIORITY.get(aSplit.suffix) ?? 99;
    const bSuffixPriority = SUFFIX_PRIORITY.get(bSplit.suffix) ?? 99;
    if (aSuffixPriority !== bSuffixPriority) return aSuffixPriority - bSuffixPriority;

    const suffixCmp = naturalCompare(aSplit.suffix, bSplit.suffix);
    if (suffixCmp !== 0) return suffixCmp;
    return naturalCompare(a, b);
}

export function compareLayerNamesForPaint(a: string, b: string): number {
    const aSplit = splitLayerName(a);
    const bSplit = splitLayerName(b);
    const aRoot = paintRootKey(aSplit.root);
    const bRoot = paintRootKey(bSplit.root);

    if (aRoot[0] !== bRoot[0]) return aRoot[0] - bRoot[0];
    if (aRoot[1] !== bRoot[1]) return aRoot[1] - bRoot[1];
    const rootNameCmp = naturalCompare(aRoot[2], bRoot[2]);
    if (rootNameCmp !== 0) return rootNameCmp;

    const aSuffixPriority = SUFFIX_PRIORITY.get(aSplit.suffix) ?? 99;
    const bSuffixPriority = SUFFIX_PRIORITY.get(bSplit.suffix) ?? 99;
    if (aSuffixPriority !== bSuffixPriority) return aSuffixPriority - bSuffixPriority;

    const suffixCmp = naturalCompare(aSplit.suffix, bSplit.suffix);
    if (suffixCmp !== 0) return suffixCmp;
    return naturalCompare(a, b);
}

export function sortLayerNames<T extends string>(layerNames: Iterable<T>): T[] {
    return [...layerNames].sort(compareLayerNames);
}

export function sortLayerNamesForPaint<T extends string>(layerNames: Iterable<T>): T[] {
    return [...layerNames].sort(compareLayerNamesForPaint);
}
