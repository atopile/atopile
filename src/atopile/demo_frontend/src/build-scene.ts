import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import * as THREE from "three";
import { GLTFExporter } from "three/examples/jsm/exporters/GLTFExporter.js";

interface MeshPayload {
    mesh: {
        positions: [number, number, number][];
        triangles: [number, number, number][];
    };
    boardThicknessMm: number;
    bounds: {
        xmin: number;
        ymin: number;
        zmin: number;
        xmax: number;
        ymax: number;
        zmax: number;
    };
}

class NodeFileReader {
    readonly EMPTY = 0 as const;
    readonly LOADING = 1 as const;
    readonly DONE = 2 as const;
    error: DOMException | null = null;
    onabort: ((this: FileReader, ev: ProgressEvent<FileReader>) => unknown) | null = null;
    onerror: ((this: FileReader, ev: ProgressEvent<FileReader>) => unknown) | null = null;
    onload: ((this: FileReader, ev: ProgressEvent<FileReader>) => unknown) | null = null;
    onloadend: ((this: FileReader, ev: ProgressEvent<FileReader>) => unknown) | null = null;
    onloadstart: ((this: FileReader, ev: ProgressEvent<FileReader>) => unknown) | null = null;
    onprogress: ((this: FileReader, ev: ProgressEvent<FileReader>) => unknown) | null = null;
    readyState: 0 | 1 | 2 = this.EMPTY;
    result: string | ArrayBuffer | null = null;
    abort(): void {}
    addEventListener(): void {}
    dispatchEvent(): boolean { return true; }
    readAsArrayBuffer(blob: Blob): void {
        this.readyState = this.LOADING;
        void blob.arrayBuffer().then((buffer) => {
            this.result = buffer;
            this.readyState = this.DONE;
            this.onload?.call(this as unknown as FileReader, {} as ProgressEvent<FileReader>);
            this.onloadend?.call(this as unknown as FileReader, {} as ProgressEvent<FileReader>);
        }).catch((error: Error) => {
            this.error = new DOMException(error.message);
            this.readyState = this.DONE;
            this.onerror?.call(this as unknown as FileReader, {} as ProgressEvent<FileReader>);
            this.onloadend?.call(this as unknown as FileReader, {} as ProgressEvent<FileReader>);
        });
    }
    readAsBinaryString(): void { throw new Error("Not implemented"); }
    readAsDataURL(): void { throw new Error("Not implemented"); }
    readAsText(): void { throw new Error("Not implemented"); }
    removeEventListener(): void {}
    [Symbol.toStringTag] = "FileReader";
}

if (typeof globalThis.FileReader === "undefined") {
    Object.assign(globalThis, { FileReader: NodeFileReader as unknown as typeof FileReader });
}

function parseArgs() {
    const args = process.argv.slice(2);
    let meshPath: string | null = null;
    let outPath: string | null = null;
    for (let index = 0; index < args.length; index += 1) {
        const arg = args[index];
        if (arg === "--mesh") {
            meshPath = args[index + 1] ?? null;
            index += 1;
        } else if (arg === "--out") {
            outPath = args[index + 1] ?? null;
            index += 1;
        }
    }
    if (!meshPath || !outPath) {
        throw new Error("Usage: bun run build-scene --mesh <mesh.json> --out <board.glb>");
    }
    return { meshPath, outPath };
}

function buildBoardGeometry(payload: MeshPayload): THREE.BufferGeometry {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(payload.mesh.triangles.length * 9);
    const colors = new Float32Array(payload.mesh.triangles.length * 9);

    const centerX = (payload.bounds.xmin + payload.bounds.xmax) / 2;
    const centerY = (payload.bounds.ymin + payload.bounds.ymax) / 2;
    const centerZ = (payload.bounds.zmin + payload.bounds.zmax) / 2;
    const spanX = Math.max(payload.bounds.xmax - payload.bounds.xmin, 1);
    const spanY = Math.max(payload.bounds.ymax - payload.bounds.ymin, 1);
    const spanZ = Math.max(payload.bounds.zmax - payload.bounds.zmin, 1);

    let cursor = 0;
    for (const triangle of payload.mesh.triangles) {
        for (const index of triangle) {
            const [x, y, z] = payload.mesh.positions[index]!;
            positions[cursor * 3] = x - centerX;
            positions[cursor * 3 + 1] = z - centerZ;
            positions[cursor * 3 + 2] = -(y - centerY);

            const nx = (x - payload.bounds.xmin) / spanX;
            const ny = (y - payload.bounds.ymin) / spanY;
            const nz = (z - payload.bounds.zmin) / spanZ;
            colors[cursor * 3] = 0.07 + nz * 0.24 + nx * 0.1;
            colors[cursor * 3 + 1] = 0.28 + nz * 0.45 + ny * 0.08;
            colors[cursor * 3 + 2] = 0.12 + nx * 0.12 + ny * 0.08;
            cursor += 1;
        }
    }

    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    geometry.computeVertexNormals();
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();
    return geometry;
}

function buildPedestal(payload: MeshPayload): THREE.Mesh {
    const width = Math.max(payload.bounds.xmax - payload.bounds.xmin, 1) + 14;
    const depth = Math.max(payload.bounds.ymax - payload.bounds.ymin, 1) + 14;
    const height = Math.max(payload.boardThicknessMm, 1.6) * 0.35;
    const pedestalGeometry = new THREE.BoxGeometry(width, height, depth);
    const pedestalMaterial = new THREE.MeshStandardMaterial({
        color: new THREE.Color("#10161e"),
        roughness: 0.92,
        metalness: 0.08,
    });
    const pedestal = new THREE.Mesh(pedestalGeometry, pedestalMaterial);
    pedestal.position.set(0, -Math.max(payload.boardThicknessMm, 1.6) * 1.1, 0);
    pedestal.receiveShadow = true;
    return pedestal;
}

async function exportGlb(scene: THREE.Scene): Promise<ArrayBuffer> {
    const exporter = new GLTFExporter();
    return await new Promise<ArrayBuffer>((resolve, reject) => {
        exporter.parse(
            scene,
            (result) => {
                if (!(result instanceof ArrayBuffer)) {
                    reject(new Error("Expected binary GLB output"));
                    return;
                }
                resolve(result);
            },
            (error) => reject(error),
            {
                binary: true,
                includeCustomExtensions: false,
                trs: false,
                onlyVisible: true,
            },
        );
    });
}

const { meshPath, outPath } = parseArgs();
const payload = JSON.parse(await readFile(meshPath, "utf8")) as MeshPayload;

const scene = new THREE.Scene();
scene.background = null;

const boardGeometry = buildBoardGeometry(payload);
const boardMaterial = new THREE.MeshPhysicalMaterial({
    roughness: 0.56,
    metalness: 0.14,
    clearcoat: 0.42,
    clearcoatRoughness: 0.36,
    sheen: 0.18,
    vertexColors: true,
});

const board = new THREE.Mesh(boardGeometry, boardMaterial);
board.castShadow = true;
board.receiveShadow = true;
scene.add(board);
scene.add(buildPedestal(payload));

const keyLight = new THREE.DirectionalLight(0xfff2db, 2.8);
keyLight.position.set(24, 32, 18);
keyLight.target.position.set(0, 0, -1);
keyLight.add(keyLight.target);
scene.add(keyLight);

const fillLight = new THREE.DirectionalLight(0xa3d4ff, 1.3);
fillLight.position.set(-22, 16, -24);
fillLight.target.position.set(0, 0, -1);
fillLight.add(fillLight.target);
scene.add(fillLight);

const glb = await exportGlb(scene);
await mkdir(path.dirname(outPath), { recursive: true });
await writeFile(outPath, Buffer.from(glb));
