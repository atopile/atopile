import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import {
    onThreeDViewerStateChanged,
    getThreeDViewerState,
    type ThreeDViewerState,
} from '../common/3dmodel';
import { getExtension } from '../common/vscodeapi';
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
        const state = getThreeDViewerState();
        return this.buildHtmlForState(webview, state);
    }

    private buildHtmlForState(webview: vscode.Webview, state: ThreeDViewerState): string {
        // Failed state - show error
        if (state.state === 'failed') {
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
                        <div class="message">${state.message}</div>
                    </div>
                `,
            });
        }

        // Loading state - show spinner
        if (state.state === 'loading') {
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

        // Showing state - render the 3D model
        const modelPath = state.modelPath;
        if (!modelPath || !fs.existsSync(modelPath)) {
            // Model path is set but file doesn't exist - show loading
            return this.buildHtmlForState(webview, { state: 'loading' });
        }

        const modelWebUri = this.getWebviewUri(webview, modelPath);
        const extensionPath = getExtension().extensionUri.fsPath;
        const threeRoot = path.join(extensionPath, 'node_modules', 'three');
        const threeModulePath = path.join(threeRoot, 'build', 'three.module.js');
        const threeAddonsPath = path.join(threeRoot, 'examples', 'jsm');
        const dracoDecoderPath = path.join(threeRoot, 'examples', 'jsm', 'libs', 'draco');

        if (!fs.existsSync(threeModulePath) || !fs.existsSync(dracoDecoderPath)) {
            return this.getMissingResourceHtml('3D viewer runtime (three.js not packaged)');
        }

        const threeModuleUri = webview.asWebviewUri(vscode.Uri.file(threeModulePath));
        const threeAddonsUri = webview.asWebviewUri(vscode.Uri.file(threeAddonsPath));
        const dracoDecoderUri = webview.asWebviewUri(vscode.Uri.file(dracoDecoderPath));

        // Build status badge
        let statusBadge = '';
        if (state.isBuilding) {
            statusBadge = `<div class="status-badge building">
                <span class="badge-spinner"></span>
                <span>Building...</span>
            </div>`;
        } else if (state.isOptimizing) {
            statusBadge = `<div class="status-badge optimizing">
                <span class="badge-spinner"></span>
                <span>Optimizing...</span>
            </div>`;
        }

        // Three.js viewer script using locally packaged dependencies
        const viewerScript = `
            <script type="importmap">
            {
                "imports": {
                    "three": "${threeModuleUri.toString()}",
                    "three/addons/": "${threeAddonsUri.toString()}/"
                }
            }
            </script>
            <script type="module">
                import * as THREE from 'three';
                import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
                import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
                import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
                import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

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
                const pmremGenerator = new THREE.PMREMGenerator(renderer);
                pmremGenerator.compileEquirectangularShader();

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

                // Build local environment map from RoomEnvironment (no network dependency)
                function loadEnvironment() {
                    const envScene = new RoomEnvironment(renderer);
                    const envMap = pmremGenerator.fromScene(envScene).texture;
                    scene.environment = envMap;
                    scene.background = getThemeBackground();
                }

                // Load GLB model
                async function loadModel() {
                    const loader = new GLTFLoader();
                    const dracoLoader = new DRACOLoader();
                    dracoLoader.setDecoderPath('${dracoDecoderUri.toString()}/');
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
                    opacity: 0.8;
                    z-index: 10;
                    font-family: var(--vscode-font-family);
                    background: var(--vscode-editor-background);
                    padding: 4px 8px;
                    border-radius: 4px;
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
        const extensionPath = getExtension().extensionUri.fsPath;
        const threeRoot = path.join(extensionPath, 'node_modules', 'three');
        const threeBuildRoot = path.join(threeRoot, 'build');
        const threeAddonsRoot = path.join(threeRoot, 'examples', 'jsm');

        if (fs.existsSync(threeBuildRoot) && !roots.some((r) => r.fsPath === threeBuildRoot)) {
            roots.push(vscode.Uri.file(threeBuildRoot));
        }
        if (fs.existsSync(threeAddonsRoot) && !roots.some((r) => r.fsPath === threeAddonsRoot)) {
            roots.push(vscode.Uri.file(threeAddonsRoot));
        }

        const state = getThreeDViewerState();

        if (state.state === 'showing' && state.modelPath) {
            const modelDir = path.dirname(state.modelPath);
            if (fs.existsSync(modelDir) && !roots.some((r) => r.fsPath === modelDir)) {
                roots.push(vscode.Uri.file(modelDir));
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
    // Refresh the viewer when state changes
    context.subscriptions.push(
        onThreeDViewerStateChanged((_) => {
            if (modelViewer?.isOpen()) {
                openModelViewerPreview();
            }
        }),
    );
}

export function deactivate() {
    closeModelViewerPreview();
}
