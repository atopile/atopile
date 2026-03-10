import { LOGO_GLB_BASE64 } from "./logo_b64.js";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

// Extrude an image into a 3D geometry
function createImageExtrusion(imageUrl: string, thickness: number, scale: number): Promise<THREE.Object3D> {
    return new Promise((resolve) => {
        const image = new Image();
        image.src = imageUrl;
        image.onload = () => {
            const canvas = document.createElement('canvas');
            canvas.width = image.width;
            canvas.height = image.height;
            const ctx = canvas.getContext('2d')!;
            ctx.drawImage(image, 0, 0);
            
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const data = imageData.data;
            
            // Simple contour finding (this is a basic approximation)
            // A more robust implementation would use a marching squares algorithm
            // For now, we'll just create a box with the image as a texture to represent the logo
            
            const group = new THREE.Group();
            
            // Texture for front and back
            const texture = new THREE.Texture(image);
            texture.needsUpdate = true;
            texture.colorSpace = THREE.SRGBColorSpace;
            
            // Materials
            const frontMaterial = new THREE.MeshStandardMaterial({ 
                map: texture,
                emissive: 0xff5500,
                emissiveIntensity: 0.8,
                emissiveMap: texture,
                transparent: true,
                alphaTest: 0.5
            });
            
            const sideMaterial = new THREE.MeshStandardMaterial({ 
                color: 0xff5500,
                emissive: 0xff5500,
                emissiveIntensity: 0.5
            });
            
            // For a complex shape like a logo, we'll use a simplified approach:
            // Two planes with the texture, and a rim connecting them
            // In a real implementation we'd trace the contour, but that's complex to do purely in JS here
            // We'll use a simple cylinder that approximations a coin-shaped logo for now
            
            // Or better yet, just a double-sided plane with glow
            const geometry = new THREE.PlaneGeometry(scale, scale * (image.height / image.width));
            
            const meshFront = new THREE.Mesh(geometry, frontMaterial);
            meshFront.position.z = thickness / 2;
            
            const meshBack = new THREE.Mesh(geometry, frontMaterial);
            meshBack.position.z = -thickness / 2;
            meshBack.rotation.y = Math.PI; // flip back
            
            group.add(meshFront);
            group.add(meshBack);
            
            // Create a halo effect
            const haloGeo = new THREE.PlaneGeometry(scale * 1.2, scale * 1.2 * (image.height / image.width));
            const haloMat = new THREE.MeshBasicMaterial({
                color: 0xff5500,
                transparent: true,
                opacity: 0.3,
                blending: THREE.AdditiveBlending,
                depthWrite: false
            });
            const halo = new THREE.Mesh(haloGeo, haloMat);
            group.add(halo);
            
            resolve(group);
        };
    });
}

interface PointLightPreset {
    color: number | string;
    intensity: number;
    position: [number, number, number];
    distance?: number;
    decay?: number;
}

interface DirectionalLightPreset {
    color: number | string;
    intensity: number;
    position: [number, number, number];
}

interface HemisphereLightPreset {
    skyColor: number | string;
    groundColor: number | string;
    intensity: number;
}

interface EnvironmentPreset {
    skyColor: string;
    skyRadius: number;
    skySegments: [number, number];
    lights: PointLightPreset[];
}

interface GridPreset {
    baseCellSize: number;
    majorCellInterval: number;
    minMinorDivisions: number;
    minorColor: number;
    majorColor: number;
    minorOpacity: number;
    majorOpacity: number;
}

interface CameraPreset {
    fov: number;
    initialPosition: [number, number, number];
    perspectiveDirection: [number, number, number];
    perspectiveDistanceScale: number;
    topDownDistanceScale: number;
}

interface ControlsPreset {
    enableDamping: boolean;
    autoRotate: boolean;
    autoRotateSpeed: number;
    enablePan: boolean;
    minDistance: number;
    maxDistance: number;
}

interface RendererPreset {
    antialias: boolean;
    alpha: boolean;
    powerPreference: WebGLPowerPreference;
    toneMappingExposure: number;
    maxPixelRatio: number;
}

interface MaterialStylePreset {
    silkscreenColor: string;
    solderMaskColors: Record<string, string>;
    metallicColors: Record<string, string>;
}

interface ScenePreset {
    renderer: RendererPreset;
    camera: CameraPreset;
    controls: ControlsPreset;
    environment: EnvironmentPreset;
    hemisphereLight: HemisphereLightPreset;
    directionalLights: DirectionalLightPreset[];
    pointLights: PointLightPreset[];
    grid: GridPreset;
    materials: MaterialStylePreset;
}

const STUDIO_PRESET: ScenePreset = {
    renderer: {
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
        toneMappingExposure: 1.22,
        maxPixelRatio: 2,
    },
    camera: {
        fov: 30,
        initialPosition: [0, 45, 50],
        perspectiveDirection: [0.95, 1.2, 0.8],
        perspectiveDistanceScale: 2.6,
        topDownDistanceScale: 2.35,
    },
    controls: {
        enableDamping: true,
        autoRotate: true,
        autoRotateSpeed: 0.8,
        enablePan: false,
        minDistance: 20,
        maxDistance: 500,
    },
    environment: {
        skyColor: "#b8b2a8",
        skyRadius: 20,
        skySegments: [32, 16],
        lights: [
            { color: 0xffddb0, intensity: 14, position: [7, 8, 5], distance: 0, decay: 2 },
            { color: 0xf95015, intensity: 5.5, position: [-3, 3.5, 9], distance: 0, decay: 2 },
            { color: 0x8cb9e6, intensity: 6, position: [-8, 6, -10], distance: 0, decay: 2 },
        ],
    },
    hemisphereLight: {
        skyColor: 0xe7dccd,
        groundColor: 0x0b0d10,
        intensity: 1.0,
    },
    directionalLights: [
        { color: 0xffe4bd, intensity: 2.4, position: [46, 72, 34] },
        { color: 0x9bb8d4, intensity: 0.35, position: [-54, 28, -56] },
        { color: 0xfff1dc, intensity: 0.28, position: [-12, 18, 62] },
    ],
    pointLights: [
        { color: 0xf95015, intensity: 0.7, position: [-28, 22, 18], distance: 0, decay: 2 },
        { color: 0xff671f, intensity: 0.4, position: [32, 14, -6], distance: 0, decay: 2 },
    ],
    grid: {
        baseCellSize: 22,
        majorCellInterval: 4,
        minMinorDivisions: 28,
        minorColor: 0xf95015,
        majorColor: 0xf95015,
        minorOpacity: 0.04,
        majorOpacity: 0.1,
    },
    materials: {
        silkscreenColor: "#f4f3ea",
        solderMaskColors: {
            mat_24: "#161719",
            mat_25: "#161719",
            mat_26: "#202225",
            mat_6: "#202225",
        },
        metallicColors: {
            mat_20: "#c8a24a",
            mat_21: "#c7ccd3",
        },
    },
};

function applyRendererPreset(
    renderer: THREE.WebGLRenderer,
    preset: RendererPreset,
): void {
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = preset.toneMappingExposure;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, preset.maxPixelRatio));
}

function createEnvironmentMap(
    renderer: THREE.WebGLRenderer,
    preset: EnvironmentPreset,
): THREE.Texture {
    const pmrem = new THREE.PMREMGenerator(renderer);
    const envScene = new THREE.Scene();
    const sky = new THREE.Mesh(
        new THREE.SphereGeometry(
            preset.skyRadius,
            preset.skySegments[0],
            preset.skySegments[1],
        ),
        new THREE.MeshBasicMaterial({
            color: new THREE.Color(preset.skyColor),
            side: THREE.BackSide,
        }),
    );
    envScene.add(sky);
    for (const light of preset.lights) {
        envScene.add(createPointLight(light));
    }
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
    const spanX = bounds.max.x - bounds.min.x;
    const spanZ = bounds.max.z - bounds.min.z;
    const maxSpan = Math.max(spanX, spanZ, 0.001);

    const { majorCellInterval } = STUDIO_PRESET.grid;

    const idealMinorStep = maxSpan / 25;
    const exponent = Math.floor(Math.log10(idealMinorStep));
    const fraction = idealMinorStep / Math.pow(10, exponent);

    let niceFraction;
    if (fraction < 1.5) niceFraction = 1;
    else if (fraction < 3) niceFraction = 2;
    else if (fraction < 7) niceFraction = 5;
    else niceFraction = 10;

    const step = niceFraction * Math.pow(10, exponent);
    
    const planeSize = maxSpan * 4;
    const halfSteps = Math.ceil((planeSize / 2) / step);
    const actualHalf = halfSteps * step;

    const floorHeight = bounds.max.y - bounds.min.y;
    const floorY = bounds.min.y - Math.max(floorHeight * 0.08, maxSpan * 0.02);

    const minorVertices: number[] = [];
    const majorVertices: number[] = [];
    
    for (let i = -halfSteps; i <= halfSteps; i++) {
        const p = i * step;
        const target = i % majorCellInterval === 0 ? majorVertices : minorVertices;
        target.push(-actualHalf, floorY, p, actualHalf, floorY, p);
        target.push(p, floorY, -actualHalf, p, floorY, actualHalf);
    }

    const minorGrid = new THREE.LineSegments(
        new THREE.BufferGeometry(),
        new THREE.LineBasicMaterial({
            color: STUDIO_PRESET.grid.minorColor,
            transparent: true,
            opacity: STUDIO_PRESET.grid.minorOpacity,
            depthWrite: false,
            toneMapped: false,
        }),
    );
    minorGrid.geometry.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(minorVertices, 3),
    );
    minorGrid.renderOrder = -2;

    const majorGrid = new THREE.LineSegments(
        new THREE.BufferGeometry(),
        new THREE.LineBasicMaterial({
            color: STUDIO_PRESET.grid.majorColor,
            transparent: true,
            opacity: STUDIO_PRESET.grid.majorOpacity,
            depthWrite: false,
            toneMapped: false,
        }),
    );
    majorGrid.geometry.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(majorVertices, 3),
    );
    majorGrid.renderOrder = -1;

    const grid = new THREE.Group();
    grid.add(minorGrid, majorGrid);
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
            color: new THREE.Color(STUDIO_PRESET.materials.silkscreenColor),
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

    if (materialName in STUDIO_PRESET.materials.solderMaskColors) {
        styled.color = new THREE.Color(
            STUDIO_PRESET.materials.solderMaskColors[materialName]!,
        );
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
        styled.color = new THREE.Color(
            STUDIO_PRESET.materials.solderMaskColors[materialName]!,
        );
        styled.roughness = 0.9;
        styled.metalness = 0.01;
        styled.envMapIntensity = 0.03;
        styled.needsUpdate = true;
        node.renderOrder = 0;
        materialCache.set(cacheKey, styled);
        return styled;
    }

    if (materialName in STUDIO_PRESET.materials.metallicColors) {
        styled.color = new THREE.Color(
            STUDIO_PRESET.materials.metallicColors[materialName]!,
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

function createDirectionalLight(preset: DirectionalLightPreset): THREE.DirectionalLight {
    const light = new THREE.DirectionalLight(preset.color, preset.intensity);
    light.position.set(...preset.position);
    return light;
}

function createPointLight(preset: PointLightPreset): THREE.PointLight {
    const light = new THREE.PointLight(
        preset.color,
        preset.intensity,
        preset.distance ?? 0,
        preset.decay ?? 2,
    );
    light.position.set(...preset.position);
    return light;
}

function createHemisphereLight(preset: HemisphereLightPreset): THREE.HemisphereLight {
    return new THREE.HemisphereLight(
        preset.skyColor,
        preset.groundColor,
        preset.intensity,
    );
}

function createCamera(preset: CameraPreset): THREE.PerspectiveCamera {
    const camera = new THREE.PerspectiveCamera(preset.fov, 1, 0.0001, 10);
    camera.position.set(...preset.initialPosition);
    return camera;
}

function applyControlsPreset(
    controls: OrbitControls,
    preset: ControlsPreset,
): void {
    controls.enableDamping = preset.enableDamping;
    controls.autoRotate = preset.autoRotate;
    controls.autoRotateSpeed = preset.autoRotateSpeed;
    controls.enablePan = preset.enablePan;
    controls.minDistance = preset.minDistance;
    controls.maxDistance = preset.maxDistance;
}

async function createLightShaft(color: number, radius: number, height: number, intensity: number): Promise<THREE.Object3D> {
    const group = new THREE.Group();

    // The actual point light
    const light = new THREE.PointLight(color, intensity, height * 2, 2);
    group.add(light);

    const logoScale = radius * 4.0;
    
    // Load the pre-extruded logo GLB
    const loader = new GLTFLoader();
    const dataUri = "data:application/octet-stream;base64," + LOGO_GLB_BASE64;
    try {
        const gltf = await loader.loadAsync(dataUri);
        const logoMesh = gltf.scene;
        
        // Scale and position the logo
        logoMesh.scale.setScalar(logoScale / 500);
        logoMesh.position.y = radius * 0.11;
        logoMesh.rotation.x = -Math.PI / 2;
        
        // Apply emissive material to it
        logoMesh.traverse((node) => {
            if (node instanceof THREE.Mesh) {
                node.material = new THREE.MeshStandardMaterial({
                    color: 0xffffff,
                    emissive: 0xff5500,
                    emissiveIntensity: 5.0, // High intensity for a glowing effect
                    toneMapped: false,      // Prevent the bloom/glow from being suppressed
                });
            }
        });
        
        group.add(logoMesh);
    } catch (e) {
        console.error("Failed to load logo GLB", e);
    }

    // The godray cone
    const coneGeometry = new THREE.CylinderGeometry(radius * 0.05, radius * 2.5, height, 32, 1, true);
    coneGeometry.translate(0, -height / 2, 0);

    const colorValues = typeof color === 'string' ? new THREE.Color(color) : new THREE.Color(color);
    
    // Add a core highlight to make it look like a bright light source
    const coreMat = new THREE.MeshBasicMaterial({
        color: 0xffffee,
        transparent: true,
        opacity: 0.9,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
    });
    
    // An inner halo around the logo
    const haloSize = radius * 1.0;
    const haloGeo = new THREE.PlaneGeometry(haloSize, haloSize);
    const haloMat = new THREE.ShaderMaterial({
        uniforms: {
            color: { value: colorValues }
        },
        vertexShader: `
            varying vec2 vUv;
            void main() {
                vUv = uv;
                gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
        `,
        fragmentShader: `
            uniform vec3 color;
            varying vec2 vUv;
            void main() {
                vec2 center = vec2(0.5, 0.5);
                float dist = distance(vUv, center);
                float alpha = smoothstep(0.5, 0.0, dist);
                // Make the center intense and white-ish, fading out to the color
                vec3 finalColor = mix(color, vec3(1.0), alpha * 0.5);
                gl_FragColor = vec4(finalColor, alpha * 0.8);
            }
        `,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
    });
    const haloMesh = new THREE.Mesh(haloGeo, haloMat);
    haloMesh.position.y = radius * 0.15;
    haloMesh.rotation.x = -Math.PI / 2;
    group.add(haloMesh);

    const coneMaterial = new THREE.ShaderMaterial({
        uniforms: {
            color: { value: colorValues },
            fadePow: { value: 2.5 },
        },
        vertexShader: `
            varying vec2 vUv;
            varying vec3 vNormal;
            varying vec3 vViewPosition;
            void main() {
                vUv = uv;
                vNormal = normalize(normalMatrix * normal);
                vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
                vViewPosition = -mvPosition.xyz;
                gl_Position = projectionMatrix * mvPosition;
            }
        `,
        fragmentShader: `
            uniform vec3 color;
            uniform float fadePow;
            varying vec2 vUv;
            varying vec3 vNormal;
            varying vec3 vViewPosition;
            void main() {
                float alpha = pow(vUv.y, fadePow);
                vec3 normal = normalize(vNormal);
                vec3 viewDir = normalize(vViewPosition);
                
                // Creates a soft core and faded edges
                float thickness = max(0.0, abs(dot(viewDir, normal)));
                // Boost alpha slightly to make it look bright
                gl_FragColor = vec4(color, alpha * thickness * 0.6);
            }
        `,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        side: THREE.DoubleSide,
    });
    
    const cone = new THREE.Mesh(coneGeometry, coneMaterial);
    // Move cone slightly down so the logo sits inside the tip
    cone.position.y = radius * 0.1;
    group.add(cone);

    return group;
}

export interface Model3DOptions {
    showStats?: boolean;
}

export async function mountModel3D(surface: HTMLElement, modelUrl: string, options: Model3DOptions = {}): Promise<() => void> {
    const canvas = document.createElement("canvas");
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    canvas.style.display = "block";
    surface.appendChild(canvas);

    const showStats = options.showStats ?? false;
    const stats = document.createElement("div");
    stats.className = "atopile-demo-model-stats";
    if (showStats) {
        stats.textContent = "fps --\ncalls --\ntris --\nmem --";
    } else {
        stats.style.display = "none";
    }
    surface.appendChild(stats);

    const renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: STUDIO_PRESET.renderer.antialias,
        alpha: STUDIO_PRESET.renderer.alpha,
        powerPreference: STUDIO_PRESET.renderer.powerPreference,
    });
    applyRendererPreset(renderer, STUDIO_PRESET.renderer);

    const scene = new THREE.Scene();
    scene.background = null;
    const camera = createCamera(STUDIO_PRESET.camera);
    scene.add(camera);

    const controls = new OrbitControls(camera, canvas);
    applyControlsPreset(controls, STUDIO_PRESET.controls);

    const envMap = createEnvironmentMap(renderer, STUDIO_PRESET.environment);
    scene.environment = envMap;
    scene.background = null;

    scene.add(createHemisphereLight(STUDIO_PRESET.hemisphereLight));
    for (const light of STUDIO_PRESET.directionalLights) {
        scene.add(createDirectionalLight(light));
    }
    for (const light of STUDIO_PRESET.pointLights) {
        scene.add(createPointLight(light));
    }

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

    const boardMaxSpan = Math.max(
        centeredBounds.max.x - centeredBounds.min.x,
        centeredBounds.max.z - centeredBounds.min.z,
        0.001
    );
    
    // Bottom orange underglow
    const underglow = new THREE.PointLight(0xff5500, 0.5, boardMaxSpan * 4, 2);
    underglow.position.set(0, centeredBounds.min.y - boardMaxSpan * 0.1, 0);
    scene.add(underglow);

    // Top orange glow with godrays
    const topglow = await createLightShaft(0xff5500, boardMaxSpan, boardMaxSpan * 1.5, 0.01);
    topglow.position.set(0, centeredBounds.max.y + boardMaxSpan * 1.0, 0);
    scene.add(topglow);

    let currentRadius = 0.01;
    let requestRender: (() => void) | null = null;

    const setTopDownView = () => {
        const distance = currentRadius * STUDIO_PRESET.camera.topDownDistanceScale;
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
        const distance = STUDIO_PRESET.camera.perspectiveDistanceScale * Math.max(
            currentRadius / Math.tan(verticalFov / 2),
            currentRadius / Math.tan(horizontalFov / 2),
        );
        const viewDirection = new THREE.Vector3(
            ...STUDIO_PRESET.camera.perspectiveDirection,
        ).normalize();
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
    let demandFrameId: number | null = null;
    let continuousFrameId: number | null = null;
    let framesSinceSample = 0;
    let sampleStart = performance.now();
    let lastFrameTime = performance.now();
    let smoothFps = 0;

    const renderStats = (fps: string | number) => {
        const { render, memory } = renderer.info;
        stats.textContent = [
            `fps ${fps}`,
            `calls ${render.calls} tris ${render.triangles} lines ${render.lines}`,
            `pts ${render.points} geoms ${memory.geometries}`,
            `tex ${memory.textures} autoRotate ${STUDIO_PRESET.controls.autoRotate ? "on" : "off"}`,
        ].join("\n");
    };

    const updateStats = (now: number) => {
        framesSinceSample += 1;
        const elapsed = now - sampleStart;
        if (elapsed < 500) return;
        const rawFps = (framesSinceSample * 1000) / elapsed;
        smoothFps = smoothFps === 0 ? rawFps : smoothFps * 0.8 + rawFps * 0.2;
        renderStats(Math.round(smoothFps));
        framesSinceSample = 0;
        sampleStart = now;
    };

    const renderFrame = (now: number) => {
        const deltaSeconds = Math.max((now - lastFrameTime) / 1000, 1 / 240);
        lastFrameTime = now;
        return controls.update(deltaSeconds);
    };

    const renderOnce = (now: number) => {
        demandFrameId = null;
        if (disposed) return;
        const changed = renderFrame(now);
        renderer.render(scene, camera);
        updateStats(now);
        if (!STUDIO_PRESET.controls.autoRotate && changed) {
            requestRender?.();
        }
    };

    const renderLoop = (now: number) => {
        if (disposed) return;
        renderFrame(now);
        renderer.render(scene, camera);
        updateStats(now);
        continuousFrameId = window.requestAnimationFrame(renderLoop);
    };

    requestRender = () => {
        if (disposed || STUDIO_PRESET.controls.autoRotate || demandFrameId !== null) return;
        demandFrameId = window.requestAnimationFrame(renderOnce);
    };

    controls.addEventListener("change", () => {
        requestRender?.();
    });
    if (STUDIO_PRESET.controls.autoRotate) {
        renderer.render(scene, camera);
        updateStats(performance.now());
        continuousFrameId = window.requestAnimationFrame(renderLoop);
    } else {
        requestRender();
    }

    return () => {
        disposed = true;
        window.__ATOPILE_DEMO_SET_TOP_DOWN__ = null;
        resizeObserver.disconnect();
        if (demandFrameId !== null) {
            window.cancelAnimationFrame(demandFrameId);
        }
        if (continuousFrameId !== null) {
            window.cancelAnimationFrame(continuousFrameId);
        }
        controls.dispose();
        envMap.dispose();
        renderer.dispose();
        surface.replaceChildren();
    };
}
