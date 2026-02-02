import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import {
    onThreeDModelChanged,
    onThreeDModelStatusChanged,
    getCurrentThreeDModel,
    getThreeDModelStatus,
    getOptimizedPath,
    setThreeDModelStatusFromViewer,
    startOptimizationFromViewer,
} from '../common/3dmodel';
import { BaseWebview } from './webview-base';
import { buildHtml } from './html-builder';

class ModelViewerWebview extends BaseWebview {
    constructor() {
        super({
            id: 'modelviewer_preview',
            title: '3D Model',
            iconName: 'cube-icon.svg',
        });
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        const model = getCurrentThreeDModel();
        const status = getThreeDModelStatus();

        // Determine which GLB path to use based on status
        let modelPath: string | undefined;
        let isBuilding = false;

        if (status.state === 'optimized') {
            // Use optimized version
            modelPath = status.optimizedPath;
        } else if (status.state === 'optimizing') {
            // Show raw while optimizing
            modelPath = status.rawPath;
        } else if (status.state === 'raw_ready') {
            // Show raw GLB
            modelPath = status.rawPath;
        } else if (status.state === 'building') {
            // While building, keep showing existing model if available
            // Prefer optimized > raw > model watcher path
            isBuilding = true;
            if (model?.path) {
                const optimizedPath = model.path.replace(/\.glb$/, '.optimized.glb');
                if (fs.existsSync(optimizedPath)) {
                    modelPath = optimizedPath;
                } else if (fs.existsSync(model.path)) {
                    modelPath = model.path;
                }
            }
        } else if (model?.path) {
            // Fall back to model watcher path
            modelPath = model.path;
        }

        if (status.state === 'failed') {
            return buildHtml({
                title: '3D Model Preview',
                styles: `
                    html, body {height: 100%;}
                    body {display: flex; align-items: center; justify-content: center;}
                    .state {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        gap: 12px;
                        font-family: var(--vscode-font-family);
                        color: var(--vscode-foreground);
                        text-align: center;
                        max-width: 360px;
                    }
                    .icon {
                        width: 0;
                        height: 0;
                        border-left: 16px solid transparent;
                        border-right: 16px solid transparent;
                        border-bottom: 28px solid var(--vscode-warningForeground);
                        position: relative;
                    }
                    .icon::after {
                        content: '!';
                        position: absolute;
                        left: -3px;
                        top: 8px;
                        color: var(--vscode-editor-background);
                        font-weight: 700;
                        font-size: 14px;
                    }
                    .title { font-size: 0.95rem; font-weight: 600; }
                    .message { font-size: 0.85rem; color: var(--vscode-descriptionForeground); }
                `,
                body: `
                    <div class="state">
                        <div class="icon">!</div>
                        <div class="title">3D export failed</div>
                        <div class="message">${status.message}</div>
                    </div>
                `,
            });
        }

        // Show building spinner only if no model path available
        // (when building with existing model, we keep showing the old model)
        if (!modelPath || !fs.existsSync(modelPath)) {
            return buildHtml({
                title: '3D Model Preview',
                styles: `
                    html, body {height: 100%;}
                    body {display: flex; align-items: center; justify-content: center;}
                    .state {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        gap: 12px;
                        font-family: var(--vscode-font-family);
                        color: var(--vscode-foreground);
                        text-align: center;
                        max-width: 360px;
                    }
                    .spinner {
                        width: 36px;
                        height: 36px;
                        border: 3px solid var(--vscode-editorWidget-border);
                        border-top-color: var(--vscode-progressBar-background);
                        border-radius: 50%;
                        animation: spin 1s linear infinite;
                    }
                    .title { font-size: 0.95rem; font-weight: 600; }
                    .message { font-size: 0.85rem; color: var(--vscode-descriptionForeground); }
                    @keyframes spin { to { transform: rotate(360deg); } }
                `,
                body: `
                    <div class="state">
                        <div class="spinner" aria-label="Loading"></div>
                        <div class="title">Generating 3D model</div>
                    </div>
                `,
            });
        }

        const modelWebUri = this.getWebviewUri(webview, modelPath);

        // Build status badge - only show when building with existing model
        const statusBadge = (isBuilding && modelPath)
            ? `<div class="status-badge">
                   <span class="badge-spinner"></span>
                   <span>Building...</span>
               </div>`
            : '';

        // Three.js enhanced viewer script
        const viewerScript = `
            <script type="importmap">
            {
                "imports": {
                    "three": "https://cdn.jsdelivr.net/npm/three@0.162.0/build/three.module.js",
                    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.162.0/examples/jsm/"
                }
            }
            </script>
            <script type="module">
                import * as THREE from 'three';
                import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
                import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
                import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
                import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';

                const container = document.getElementById('container');

                // Scene setup
                const scene = new THREE.Scene();
                const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.01, 1000);

                // High-quality WebGL renderer
                const renderer = new THREE.WebGLRenderer({
                    antialias: true,
                    powerPreference: 'high-performance'
                });
                renderer.setSize(container.clientWidth, container.clientHeight);
                renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
                renderer.toneMapping = THREE.ACESFilmicToneMapping;
                renderer.toneMappingExposure = 1.2;
                renderer.outputColorSpace = THREE.SRGBColorSpace;
                container.appendChild(renderer.domElement);

                // Controls
                const controls = new OrbitControls(camera, renderer.domElement);
                controls.enableDamping = true;
                controls.dampingFactor = 0.05;
                controls.minDistance = 0.01;

                // Get background color from VSCode theme
                function getThemeBackground() {
                    const style = getComputedStyle(document.body);
                    const bgColor = style.getPropertyValue('--vscode-editor-background').trim();
                    return new THREE.Color(bgColor || '#1e1e1e');
                }

                // Load HDR environment
                async function loadEnvironment() {
                    const bgColor = getThemeBackground();
                    const rgbeLoader = new RGBELoader();
                    try {
                        const envMap = await rgbeLoader.loadAsync('https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/1k/studio_small_08_1k.hdr');
                        envMap.mapping = THREE.EquirectangularReflectionMapping;
                        scene.environment = envMap;
                        scene.background = bgColor;
                    } catch (e) {
                        console.warn('Failed to load HDR', e);
                        scene.background = bgColor;
                    }
                }

                // Load GLB model
                async function loadModel() {
                    const loader = new GLTFLoader();
                    const dracoLoader = new DRACOLoader();
                    dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.6/');
                    loader.setDRACOLoader(dracoLoader);

                    try {
                        const gltf = await loader.loadAsync('${modelWebUri}');
                        const model = gltf.scene;

                        // Enhance materials for realistic PCB rendering
                        model.traverse((child) => {
                            if (child.isMesh && child.material) {
                                    const oldMat = child.material;

                                    if (oldMat.map) {
                                        // Process texture to enhance PCB appearance
                                        const canvas = document.createElement('canvas');
                                        const img = oldMat.map.image;
                                        canvas.width = img.width;
                                        canvas.height = img.height;
                                        const ctx = canvas.getContext('2d');
                                        ctx.drawImage(img, 0, 0);

                                        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                                        const data = imageData.data;

                                        for (let i = 0; i < data.length; i += 4) {
                                            const r = data[i], g = data[i + 1], b = data[i + 2];

                                            // Green soldermask -> matte black
                                            if (g > 80 && g > r * 1.3 && g > b * 1.3) {
                                                data[i] = 30;
                                                data[i + 1] = 32;
                                                data[i + 2] = 35;
                                            }
                                            // FR4 edge enhancement
                                            else if (r > 150 && g > 120 && b > 60 && r > b * 1.5) {
                                                data[i] = Math.min(255, r * 0.85);
                                                data[i + 1] = Math.min(255, g * 0.8);
                                                data[i + 2] = Math.min(255, b * 0.6);
                                            }
                                        }

                                        ctx.putImageData(imageData, 0, 0);

                                        const newTexture = new THREE.CanvasTexture(canvas);
                                        newTexture.flipY = oldMat.map.flipY;
                                        newTexture.colorSpace = THREE.SRGBColorSpace;

                                        const mat = new THREE.MeshPhysicalMaterial({
                                            map: newTexture,
                                            roughness: 0.6,
                                            metalness: 0.0,
                                            clearcoat: 0.15,
                                            clearcoatRoughness: 0.4,
                                            envMapIntensity: 0.8,
                                        });
                                        child.material = mat;
                                        oldMat.dispose();
                                    } else {
                                        const mat = new THREE.MeshPhysicalMaterial({
                                            color: oldMat.color,
                                            roughness: 0.5,
                                            metalness: 0.0,
                                            envMapIntensity: 1.0,
                                        });
                                        child.material = mat;
                                        oldMat.dispose();
                                    }
                                }
                        });

                        // Center and frame model
                        const box = new THREE.Box3().setFromObject(model);
                        const center = box.getCenter(new THREE.Vector3());
                        const size = box.getSize(new THREE.Vector3());
                        const maxDim = Math.max(size.x, size.y, size.z);

                        model.position.sub(center);

                        const distance = maxDim * 2;
                        camera.position.set(distance * 0.7, distance * 0.5, distance * 0.7);
                        camera.lookAt(0, 0, 0);
                        controls.target.set(0, 0, 0);
                        controls.update();

                        scene.add(model);

                        // Three-point lighting (no shadows - using HDR environment instead)
                        const keyLight = new THREE.DirectionalLight(0xffffff, 1.5);
                        keyLight.position.set(5, 10, 5);
                        scene.add(keyLight);

                        const fillLight = new THREE.DirectionalLight(0xffffff, 0.5);
                        fillLight.position.set(-5, 5, -5);
                        scene.add(fillLight);

                        const rimLight = new THREE.DirectionalLight(0xffffff, 0.6);
                        rimLight.position.set(0, 5, -10);
                        scene.add(rimLight);

                    } catch (error) {
                        console.error('Failed to load model:', error);
                    }
                }

                // Animation loop
                function animate() {
                    requestAnimationFrame(animate);
                    controls.update();
                    renderer.render(scene, camera);
                }

                // Resize handler
                const resizeObserver = new ResizeObserver(() => {
                    camera.aspect = container.clientWidth / container.clientHeight;
                    camera.updateProjectionMatrix();
                    renderer.setSize(container.clientWidth, container.clientHeight);
                });
                resizeObserver.observe(container);

                // Watch for theme changes
                const themeObserver = new MutationObserver(() => {
                    const bgColor = getThemeBackground();
                    scene.background = bgColor;
                    renderer.setClearColor(bgColor);
                });
                themeObserver.observe(document.body, {
                    attributes: true,
                    attributeFilter: ['class', 'style']
                });

                // Initialize
                loadEnvironment();
                loadModel();
                animate();
            </script>
        `;

        return buildHtml({
            title: '3D Model Preview',
            styles: `
                html, body, #container {height: 100%; width: 100%; margin: 0; padding: 0; overflow: hidden;}
                #container {position: relative; background: var(--vscode-editor-background);}
                canvas {display: block;}
                .status-badge {
                    position: absolute;
                    bottom: 8px;
                    left: 10px;
                    display: flex;
                    align-items: center;
                    gap: 5px;
                    font-size: 11px;
                    color: var(--vscode-descriptionForeground);
                    opacity: 0.7;
                    z-index: 10;
                    font-family: var(--vscode-font-family);
                }
                .badge-spinner {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    border: 1.5px solid var(--vscode-descriptionForeground);
                    border-top-color: transparent;
                    animation: spin 0.8s linear infinite;
                    opacity: 0.7;
                }
                @keyframes spin { to { transform: rotate(360deg); } }
            `,
            body: `
                <div id="container">
                    ${statusBadge}
                </div>
                ${viewerScript}
            `,
        });
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        const roots = super.getLocalResourceRoots();
        const model = getCurrentThreeDModel();
        const status = getThreeDModelStatus();

        // Add the model directory for both raw and optimized paths
        if (model && fs.existsSync(model.path)) {
            roots.push(vscode.Uri.file(path.dirname(model.path)));
        }

        // Also add paths from status if they exist (for optimization states)
        if (status.state === 'optimizing' || status.state === 'raw_ready') {
            const rawDir = path.dirname(status.rawPath);
            if (!roots.some((r) => r.fsPath === rawDir)) {
                roots.push(vscode.Uri.file(rawDir));
            }
        } else if (status.state === 'optimized') {
            const optimizedDir = path.dirname(status.optimizedPath);
            if (!roots.some((r) => r.fsPath === optimizedDir)) {
                roots.push(vscode.Uri.file(optimizedDir));
            }
        }

        return roots;
    }

    protected setupPanel(): void {}
}

let modelViewer: ModelViewerWebview | undefined;

export async function openModelViewerPreview() {
    if (!modelViewer) {
        modelViewer = new ModelViewerWebview();
    }

    // Check if we need to start optimization when opening the viewer
    const status = getThreeDModelStatus();
    const model = getCurrentThreeDModel();

    // If we're in idle state with an existing model, check if we need to optimize
    if (status.state === 'idle' && model?.exists && model.path) {
        const optimizedPath = getOptimizedPath(model.path);

        if (fs.existsSync(optimizedPath)) {
            const rawMtime = fs.statSync(model.path).mtimeMs;
            const optimizedMtime = fs.statSync(optimizedPath).mtimeMs;
            if (optimizedMtime >= rawMtime) {
                // Optimized version is up to date
                setThreeDModelStatusFromViewer({ state: 'optimized', rawPath: model.path, optimizedPath });
            } else {
                // Need to re-optimize
                setThreeDModelStatusFromViewer({ state: 'raw_ready', rawPath: model.path });
                startOptimizationFromViewer(model.path);
            }
        } else {
            // No optimized version exists - start optimization
            setThreeDModelStatusFromViewer({ state: 'raw_ready', rawPath: model.path });
            startOptimizationFromViewer(model.path);
        }
    }

    await modelViewer.open();
}

export function closeModelViewerPreview() {
    modelViewer?.dispose();
    modelViewer = undefined;
}

export function isModelViewerOpen(): boolean {
    return modelViewer?.isOpen() ?? false;
}

export async function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        onThreeDModelChanged((_) => {
            if (modelViewer?.isOpen()) {
                openModelViewerPreview();
            }
        }),
    );
    context.subscriptions.push(
        onThreeDModelStatusChanged((_) => {
            if (modelViewer?.isOpen()) {
                openModelViewerPreview();
            }
        }),
    );
}

export function deactivate() {
    closeModelViewerPreview();
}
