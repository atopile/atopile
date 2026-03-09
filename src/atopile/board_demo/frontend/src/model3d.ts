import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

function createEnvironmentMap(renderer: THREE.WebGLRenderer): THREE.Texture {
    const pmrem = new THREE.PMREMGenerator(renderer);
    const envScene = new THREE.Scene();
    const sky = new THREE.Mesh(
        new THREE.SphereGeometry(20, 32, 16),
        new THREE.MeshBasicMaterial({
            color: new THREE.Color("#b8b2a8"),
            side: THREE.BackSide,
        }),
    );
    envScene.add(sky);
    const warm = new THREE.PointLight(0xffddb0, 14, 0, 2);
    warm.position.set(7, 8, 5);
    envScene.add(warm);
    const accent = new THREE.PointLight(0xf95015, 5.5, 0, 2);
    accent.position.set(-3, 3.5, 9);
    envScene.add(accent);
    const cool = new THREE.PointLight(0x8cb9e6, 6, 0, 2);
    cool.position.set(-8, 6, -10);
    envScene.add(cool);
    const envTarget = pmrem.fromScene(envScene);
    const texture = envTarget.texture;
    pmrem.dispose();
    envScene.clear();
    return texture;
}

function looksLikeBoardSilkscreen(materialName: string, meshName: string): boolean {
    const material = materialName.toLowerCase();
    const mesh = meshName.toLowerCase();
    return mesh.includes("silkscreen") || material === "mat_22" || material === "mat_23";
}

function buildBackgroundGrid(bounds: THREE.Box3): THREE.Object3D {
    const spanX = Math.max(bounds.max.x - bounds.min.x, 1);
    const spanZ = Math.max(bounds.max.z - bounds.min.z, 1);
    const baseCellSize = 14;
    const majorCellInterval = 3;

    const targetSpan = Math.max(Math.max(spanX, spanZ) + baseCellSize * 4, baseCellSize * 6);
    const baseDivisions = Math.max(
        majorCellInterval * 2,
        Math.ceil(targetSpan / baseCellSize),
    );
    const spanDivisions = Math.ceil(baseDivisions / majorCellInterval) * majorCellInterval;

    const width = spanDivisions * baseCellSize;
    const height = spanDivisions / majorCellInterval;
    const floorHeight = bounds.max.y - bounds.min.y;
    const floorY = bounds.min.y - Math.max(floorHeight * 0.08, 0.02);

    const minorGrid = new THREE.GridHelper(width, spanDivisions, 0x202a36, 0x101922);
    minorGrid.material.opacity = 0.2;
    minorGrid.material.transparent = true;
    minorGrid.position.y = floorY;
    minorGrid.material.depthWrite = false;

    const majorGrid = new THREE.GridHelper(width, height, 0x2a3b4f, 0x2a3b4f);
    majorGrid.material.opacity = 0.4;
    majorGrid.material.transparent = true;
    majorGrid.position.y = floorY;
    majorGrid.material.depthWrite = false;

    const grid = new THREE.Group();
    grid.add(majorGrid, minorGrid);
    return grid;
}

function deQuantizeGeometry(geometry: THREE.BufferGeometry): THREE.BufferGeometry {
    for (const name of Object.keys(geometry.attributes)) {
        const attr = geometry.getAttribute(name);
        if (attr.array instanceof Float32Array) continue;
        const count = attr.count;
        const itemSize = attr.itemSize;
        const float32 = new Float32Array(count * itemSize);
        for (let i = 0; i < count; i++) {
            for (let j = 0; j < itemSize; j++) {
                float32[i * itemSize + j] = attr.getComponent(i, j);
            }
        }
        geometry.setAttribute(
            name,
            new THREE.BufferAttribute(float32, itemSize, false),
        );
    }
    const index = geometry.getIndex();
    if (index && !(index.array instanceof Uint32Array)) {
        const uint32 = new Uint32Array(index.count);
        for (let i = 0; i < index.count; i++) {
            uint32[i] = index.getX(i);
        }
        geometry.setIndex(new THREE.BufferAttribute(uint32, 1, false));
    }
    return geometry;
}

function buildMergedScene(root: THREE.Object3D): THREE.Object3D {
    root.updateMatrixWorld(true);

    const mergedRoot = new THREE.Group();
    const mergeBuckets = new Map<string, {
        material: THREE.Material;
        renderOrder: number;
        geometries: THREE.BufferGeometry[];
    }>();

    const addToBucket = (
        geometry: THREE.BufferGeometry,
        material: THREE.Material,
        worldMatrix: THREE.Matrix4,
        renderOrder: number,
    ) => {
        const transformed = deQuantizeGeometry(geometry.clone());
        transformed.applyMatrix4(worldMatrix);

        if (worldMatrix.determinant() < 0) {
            const index = transformed.getIndex();
            if (index) {
                const arr = index.array;
                for (let i = 0; i < arr.length; i += 3) {
                    const tmp = arr[i + 1]!;
                    arr[i + 1] = arr[i + 2]!;
                    arr[i + 2] = tmp;
                }
                index.needsUpdate = true;
            }
        }

        const key = `${material.uuid}::${renderOrder}`;
        const entry = mergeBuckets.get(key) ?? {
            material,
            renderOrder,
            geometries: [],
        };
        entry.geometries.push(transformed);
        mergeBuckets.set(key, entry);
    };

    root.traverse((node) => {
        if (!(node instanceof THREE.Mesh)) return;

        const geometry = node.geometry;
        const material = node.material;
        if (!(geometry instanceof THREE.BufferGeometry)) return;

        if (Array.isArray(material) || Object.keys(geometry.morphAttributes).length > 0) {
            const preserved = new THREE.Mesh(
                deQuantizeGeometry(geometry.clone()),
                material,
            );
            preserved.position.setFromMatrixPosition(node.matrixWorld);
            preserved.quaternion.setFromRotationMatrix(node.matrixWorld);
            preserved.scale.setFromMatrixScale(node.matrixWorld);
            preserved.matrixAutoUpdate = false;
            preserved.updateMatrix();
            preserved.renderOrder = node.renderOrder;
            mergedRoot.add(preserved);
            return;
        }

        if ((node as THREE.InstancedMesh).isInstancedMesh) {
            const instanced = node as THREE.InstancedMesh;
            const instanceMatrix = new THREE.Matrix4();
            const combinedMatrix = new THREE.Matrix4();
            for (let i = 0; i < instanced.count; i++) {
                instanced.getMatrixAt(i, instanceMatrix);
                combinedMatrix.multiplyMatrices(node.matrixWorld, instanceMatrix);
                addToBucket(geometry, material, combinedMatrix, node.renderOrder);
            }
            return;
        }

        addToBucket(geometry, material, node.matrixWorld, node.renderOrder);
    });

    for (const bucket of mergeBuckets.values()) {
        const mergedGeometry = bucket.geometries.length === 1
            ? bucket.geometries[0]!
            : mergeGeometries(bucket.geometries, false);
        if (!mergedGeometry) continue;

        const mesh = new THREE.Mesh(mergedGeometry, bucket.material);
        mesh.renderOrder = bucket.renderOrder;
        mesh.matrixAutoUpdate = false;
        mesh.updateMatrix();
        mergedRoot.add(mesh);
    }

    return mergedRoot;
}

function applyBoardMaterialStyle(
    node: THREE.Mesh,
    material: THREE.Material,
    materialCache: Map<string, THREE.Material>,
): THREE.Material {
    const meshName = node.name.toLowerCase();
    const materialName = material.name.toLowerCase();
    const styleKind = looksLikeBoardSilkscreen(materialName, meshName) ? "silkscreen" : "surface";
    const cacheKey = `${material.type}:${materialName}:${styleKind}`;
    const cached = materialCache.get(cacheKey);
    if (cached) {
        node.renderOrder = styleKind === "silkscreen" ? 10 : 0;
        return cached;
    }

    if (looksLikeBoardSilkscreen(materialName, meshName)) {
        const overlay = new THREE.MeshBasicMaterial({
            color: new THREE.Color("#f4f3ea"),
            side: THREE.DoubleSide,
            toneMapped: false,
            transparent: false,
            depthWrite: false,
            polygonOffset: true,
            polygonOffsetFactor: -4,
            polygonOffsetUnits: -4,
        });
        node.renderOrder = 10;
        materialCache.set(cacheKey, overlay);
        return overlay;
    }

    if (!(material instanceof THREE.MeshStandardMaterial)) {
        node.renderOrder = 0;
        materialCache.set(cacheKey, material);
        return material;
    }

    const styled = material.clone();

    if (materialName === "mat_24" || materialName === "mat_25") {
        styled.color = new THREE.Color("#161719");
        styled.roughness = 0.88;
        styled.metalness = 0.01;
        styled.envMapIntensity = 0.035;
        styled.opacity = 1;
        styled.transparent = false;
        styled.needsUpdate = true;
        node.renderOrder = 0;
        materialCache.set(cacheKey, styled);
        return styled;
    }

    if (materialName === "mat_26" || materialName === "mat_6") {
        styled.color = new THREE.Color("#202225");
        styled.roughness = 0.9;
        styled.metalness = 0.01;
        styled.envMapIntensity = 0.03;
        styled.needsUpdate = true;
        node.renderOrder = 0;
        materialCache.set(cacheKey, styled);
        return styled;
    }

    if (materialName === "mat_20" || materialName === "mat_21") {
        styled.color = new THREE.Color(
            materialName === "mat_20" ? "#c8a24a" : "#c7ccd3",
        );
        styled.roughness = materialName === "mat_20" ? 0.42 : 0.3;
        styled.metalness = 0.88;
        styled.envMapIntensity = materialName === "mat_20" ? 0.22 : 0.16;
        styled.needsUpdate = true;
        node.renderOrder = 0;
        materialCache.set(cacheKey, styled);
        return styled;
    }

    styled.envMapIntensity = 0.08;
    styled.roughness = Math.max(styled.roughness, 0.72);
    styled.metalness = Math.min(styled.metalness, 0.28);
    styled.needsUpdate = true;
    node.renderOrder = 0;
    materialCache.set(cacheKey, styled);
    return styled;
}

export async function mountModel3D(surface: HTMLElement, modelUrl: string): Promise<() => void> {
    const canvas = document.createElement("canvas");
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    canvas.style.display = "block";
    surface.appendChild(canvas);

    const stats = document.createElement("div");
    stats.className = "atopile-demo-model-stats";
    stats.textContent = "fps --\ncalls --\ntris --\nmem --";
    surface.appendChild(stats);

    const renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
    });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.22;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    const scene = new THREE.Scene();
    scene.background = null;
    const camera = new THREE.PerspectiveCamera(34, 1, 0.0001, 10);
    camera.position.set(0, 45, 120);
    scene.add(camera);

    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.autoRotate = false;
    controls.autoRotateSpeed = 0.8;
    controls.enablePan = false;
    controls.minDistance = 20;
    controls.maxDistance = 500;

    const envMap = createEnvironmentMap(renderer);
    scene.environment = envMap;
    scene.background = null;

    const hemi = new THREE.HemisphereLight(0xe7dccd, 0x0b0d10, 1.0);
    scene.add(hemi);

    const key = new THREE.DirectionalLight(0xffe4bd, 2.4);
    key.position.set(46, 72, 34);
    scene.add(key);

    const fill = new THREE.DirectionalLight(0x9bb8d4, 0.35);
    fill.position.set(-54, 28, -56);
    scene.add(fill);

    const rim = new THREE.DirectionalLight(0xfff1dc, 0.28);
    rim.position.set(-12, 18, 62);
    scene.add(rim);

    const glow = new THREE.PointLight(0xf95015, 0.7, 0, 2);
    glow.position.set(-28, 22, 18);
    scene.add(glow);

    const glowSecondary = new THREE.PointLight(0xff671f, 0.4, 0, 2);
    glowSecondary.position.set(32, 14, -6);
    scene.add(glowSecondary);

    const loader = new GLTFLoader();
    loader.setMeshoptDecoder(MeshoptDecoder);
    const gltf = await loader.loadAsync(modelUrl);
    const root = gltf.scene;
    scene.add(root);
    const materialCache = new Map<string, THREE.Material>();

    root.traverse((node) => {
        if (!(node instanceof THREE.Mesh)) return;
        node.castShadow = false;
        node.receiveShadow = false;
        const materials = Array.isArray(node.material) ? node.material : [node.material];
        const styledMaterials = materials
            .filter((material): material is THREE.Material => Boolean(material))
            .map((material) => applyBoardMaterialStyle(node, material, materialCache));
        node.material = Array.isArray(node.material) ? styledMaterials : styledMaterials[0]!;
    });

    const bounds = new THREE.Box3().setFromObject(root);
    const center = bounds.getCenter(new THREE.Vector3());
    root.position.sub(center);
    const centeredBounds = bounds.clone().translate(new THREE.Vector3(-center.x, -center.y, -center.z));
    const mergedRoot = buildMergedScene(root);
    scene.remove(root);
    scene.add(mergedRoot);
    scene.add(buildBackgroundGrid(centeredBounds));

    let currentRadius = 0.01;
    let requestRender: (() => void) | null = null;

    const setTopDownView = () => {
        const distance = currentRadius * 2.35;
        camera.up.set(0, 0, -1);
        camera.position.set(0, distance, 0.00001);
        controls.target.set(0, 0, 0);
        camera.lookAt(0, 0, 0);
        controls.update();
        requestRender?.();
    };

    const setPerspectiveView = () => {
        camera.up.set(0, 1, 0);
        const verticalFov = THREE.MathUtils.degToRad(camera.fov);
        const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect);
        const distance = 1.12 * Math.max(
            currentRadius / Math.tan(verticalFov / 2),
            currentRadius / Math.tan(horizontalFov / 2),
        );
        const viewDirection = new THREE.Vector3(0.72, 1.15, 0.88).normalize();
        camera.position.copy(viewDirection.multiplyScalar(distance));
        controls.target.set(0, 0, 0);
        camera.lookAt(0, 0, 0);
        controls.update();
        requestRender?.();
    };

    window.__ATOPILE_DEMO_SET_TOP_DOWN__ = setTopDownView;

    const resize = () => {
        const rect = surface.getBoundingClientRect();
        const width = Math.max(1, Math.round(rect.width));
        const height = Math.max(1, Math.round(rect.height));
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        currentRadius = Math.max(bounds.getBoundingSphere(new THREE.Sphere()).radius, 0.001);
        camera.near = Math.max(currentRadius / 200, 0.00001);
        camera.far = Math.max(currentRadius * 40, 1);
        camera.updateProjectionMatrix();
        controls.minDistance = currentRadius * 0.7;
        controls.maxDistance = currentRadius * 5;
        setPerspectiveView();
    };
    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(surface);

    let disposed = false;
    let animationFrameId: number | null = null;
    let framesSinceSample = 0;
    let sampleStart = performance.now();

    const updateStats = (now: number) => {
        framesSinceSample += 1;
        const elapsed = now - sampleStart;
        if (elapsed < 300) return;
        const { render, memory } = renderer.info;
        const fps = Math.round((framesSinceSample * 1000) / elapsed);
        stats.textContent = [
            `fps ${fps}`,
            `calls ${render.calls} tris ${render.triangles} lines ${render.lines}`,
            `pts ${render.points} geoms ${memory.geometries}`,
            `tex ${memory.textures} autoRotate off`,
        ].join("\n");
        framesSinceSample = 0;
        sampleStart = now;
    };

    const renderFrame = (now: number) => {
        animationFrameId = null;
        if (disposed) return;
        const changed = controls.update();
        renderer.render(scene, camera);
        updateStats(now);
        if (changed) {
            requestRender?.();
        }
    };

    requestRender = () => {
        if (disposed || animationFrameId !== null) return;
        animationFrameId = window.requestAnimationFrame(renderFrame);
    };

    controls.addEventListener("change", () => {
        requestRender?.();
    });
    requestRender();

    return () => {
        disposed = true;
        window.__ATOPILE_DEMO_SET_TOP_DOWN__ = null;
        resizeObserver.disconnect();
        if (animationFrameId !== null) {
            window.cancelAnimationFrame(animationFrameId);
        }
        controls.dispose();
        envMap.dispose();
        renderer.dispose();
        surface.replaceChildren();
    };
}
