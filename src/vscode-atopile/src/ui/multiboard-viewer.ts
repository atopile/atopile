import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { BaseWebview } from './webview-base';
import { buildHtml } from './html-builder';

interface BoardEntry {
    name: string;
    build_target: string;
    glb_path: string;
}

interface HarnessEndpoint {
    board: string;
    connector?: string;
    position?: { x: number; y: number };
}

interface HarnessEntry {
    name: string;
    type: string;
    from?: HarnessEndpoint;
    to?: HarnessEndpoint;
}

// Legacy v1.0 format
interface LegacyCableEntry {
    name: string;
    type: string;
    from: string;
    to: string;
}

interface MultiboardManifest {
    version: string;
    type: string;
    boards: BoardEntry[];
    harnesses?: HarnessEntry[];
    cables?: LegacyCableEntry[];  // backward compat for v1.0
}

class MultiboardViewerWebview extends BaseWebview {
    private manifestPath: string | undefined;

    constructor() {
        super({
            id: 'multiboard_viewer',
            title: 'Multiboard 3D',
            iconName: 'cube-icon.svg',
        });
    }

    public setManifestPath(manifestPath: string): void {
        this.manifestPath = manifestPath;
    }

    protected getHtmlContent(webview: vscode.Webview): string {
        if (!this.manifestPath || !fs.existsSync(this.manifestPath)) {
            return this.getMissingResourceHtml('multiboard manifest');
        }

        let manifest: MultiboardManifest;
        try {
            const raw = fs.readFileSync(this.manifestPath, 'utf-8');
            manifest = JSON.parse(raw);
        } catch {
            return this.getMissingResourceHtml('multiboard manifest');
        }

        if (!manifest.boards || manifest.boards.length === 0) {
            return this.getMissingResourceHtml('boards in multiboard manifest');
        }

        const manifestDir = path.dirname(this.manifestPath);

        // Resolve each board's glb_path relative to manifest dir and get webview URIs
        const boardsData = manifest.boards.map((board) => {
            const resolvedPath = path.resolve(manifestDir, board.glb_path);
            const uri = fs.existsSync(resolvedPath)
                ? this.getWebviewUri(webview, resolvedPath).toString()
                : '';
            return {
                name: board.name,
                build_target: board.build_target,
                glb_uri: uri,
            };
        });

        const boardsJson = JSON.stringify(boardsData);

        // Normalize harnesses: support both v1.1 (harnesses) and v1.0 (cables) format
        let normalizedHarnesses: { name: string; fromBoard: string; toBoard: string; fromPosition?: {x: number, y: number}; toPosition?: {x: number, y: number} }[] = [];
        if (manifest.harnesses) {
            normalizedHarnesses = manifest.harnesses.map(h => ({
                name: h.name,
                fromBoard: h.from?.board || '',
                toBoard: h.to?.board || '',
                fromPosition: h.from?.position,
                toPosition: h.to?.position,
            }));
        } else if (manifest.cables) {
            normalizedHarnesses = manifest.cables.map(c => ({
                name: c.name,
                fromBoard: c.from || '',
                toBoard: c.to || '',
            }));
        }
        const harnessesJson = JSON.stringify(normalizedHarnesses);

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

                const container = document.getElementById('container');
                const boards = ${boardsJson};
                const harnesses = ${harnessesJson};
                const statusEl = document.getElementById('status-info');

                function setStatus(msg) {
                    if (statusEl) statusEl.textContent = msg;
                }

                // Scene setup
                const scene = new THREE.Scene();
                const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100000);

                const renderer = new THREE.WebGLRenderer({ antialias: true, logarithmicDepthBuffer: true });
                renderer.setSize(container.clientWidth, container.clientHeight);
                renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
                renderer.outputColorSpace = THREE.SRGBColorSpace;
                container.appendChild(renderer.domElement);

                const controls = new OrbitControls(camera, renderer.domElement);
                controls.enableDamping = true;
                controls.dampingFactor = 0.05;

                function getThemeBackground() {
                    const style = getComputedStyle(document.body);
                    const bgColor = style.getPropertyValue('--vscode-editor-background').trim();
                    return new THREE.Color(bgColor || '#1e1e1e');
                }
                scene.background = getThemeBackground();

                // Ambient light so nothing is ever fully black
                scene.add(new THREE.AmbientLight(0xffffff, 0.6));

                function createTextSprite(text, position) {
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    canvas.width = 256;
                    canvas.height = 64;
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    ctx.font = 'bold 32px monospace';
                    ctx.fillStyle = '#88aaff';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(text, canvas.width / 2, canvas.height / 2);
                    const texture = new THREE.CanvasTexture(canvas);
                    const spriteMaterial = new THREE.SpriteMaterial({
                        map: texture,
                        transparent: true,
                        depthTest: false,
                        sizeAttenuation: false,
                    });
                    const sprite = new THREE.Sprite(spriteMaterial);
                    sprite.position.copy(position);
                    sprite.scale.set(0.18, 0.045, 1);
                    return sprite;
                }

                // --- Shared state ---
                let masterGroup = null;
                const loadedBoards = [];
                const harnessObjects = [];

                // --- Drag state ---
                const raycaster = new THREE.Raycaster();
                const pointer = new THREE.Vector2();
                const dragPlane = new THREE.Plane();
                let draggedBoard = null;
                const dragStartBoardPos = new THREE.Vector3();
                const dragStartHit = new THREE.Vector3();
                let hoveredBoard = null;

                // --- Board center helper ---
                // The GLB origin (0,0,0) in boardGroup-local = boardGroup.position in masterGroup-local
                function getBoardCenterLocal(board) {
                    return board.group.position.clone();
                }

                // --- Connector position helper ---
                // KiCad PCB coords are in mm; GLB from KiCad uses meters (GLTF spec)
                // PCB X right, Y down → GLB X right, Z = -Y (forward)
                // boardGroup.position is the GLB origin offset in masterGroup space
                const MM_TO_M = 0.001;
                function getConnectorPosition(board, position) {
                    if (!position) return getBoardCenterLocal(board);
                    return new THREE.Vector3(
                        board.group.position.x + position.x * MM_TO_M,
                        board.group.position.y + board.size.y,
                        board.group.position.z + position.y * MM_TO_M
                    );
                }

                // --- Cable helpers ---
                function createCableCurve(fromPos, toPos) {
                    return new THREE.LineCurve3(fromPos, toPos);
                }

                function updateHarness(harnessObj) {
                    const fromBoard = loadedBoards.find(b => b.name === harnessObj.fromName);
                    const toBoard = loadedBoards.find(b => b.name === harnessObj.toName);
                    if (!fromBoard || !toBoard) return;

                    const fromPos = getConnectorPosition(fromBoard, harnessObj.fromPosition);
                    const toPos = getConnectorPosition(toBoard, harnessObj.toPosition);
                    const curve = createCableCurve(fromPos, toPos);

                    harnessObj.mesh.geometry.dispose();
                    harnessObj.mesh.geometry = new THREE.TubeGeometry(curve, 32, harnessObj.radius, 8, false);

                    if (harnessObj.label) {
                        const mid = new THREE.Vector3().addVectors(fromPos, toPos).multiplyScalar(0.5);
                        mid.y += harnessObj.radius * 4;
                        harnessObj.label.position.copy(mid);
                    }
                }

                // --- Hover highlight ---
                function setHighlight(board, on) {
                    board.group.traverse(child => {
                        if (child.isMesh && child.material) {
                            const mat = child.material;
                            if (on) {
                                if (!mat._origEmissive) {
                                    mat._origEmissive = mat.emissive ? mat.emissive.clone() : new THREE.Color(0, 0, 0);
                                }
                                mat.emissive = new THREE.Color(0x334466);
                            } else if (mat._origEmissive) {
                                mat.emissive.copy(mat._origEmissive);
                                delete mat._origEmissive;
                            }
                        }
                    });
                }

                // --- Pointer helpers ---
                function getPointerNDC(event) {
                    const rect = renderer.domElement.getBoundingClientRect();
                    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                }

                function findHitBoard(event) {
                    if (loadedBoards.length === 0) return null;
                    getPointerNDC(event);
                    raycaster.setFromCamera(pointer, camera);
                    const meshes = [];
                    for (const board of loadedBoards) {
                        board.group.traverse(child => {
                            if (child.isMesh) {
                                child.userData._boardRef = board;
                                meshes.push(child);
                            }
                        });
                    }
                    const hits = raycaster.intersectObjects(meshes, false);
                    return hits.length > 0 ? hits[0].object.userData._boardRef : null;
                }

                // --- Pointer events for drag & hover ---
                renderer.domElement.addEventListener('pointerdown', (event) => {
                    const board = findHitBoard(event);
                    if (!board) return;

                    renderer.domElement.setPointerCapture(event.pointerId);
                    draggedBoard = board;
                    controls.enabled = false;
                    renderer.domElement.style.cursor = 'grabbing';

                    // Snapshot the board's starting position (local to masterGroup)
                    dragStartBoardPos.copy(board.group.position);

                    // Set drag plane at the board's world Y so raycasting
                    // produces movement strictly in the XZ world plane
                    masterGroup.updateMatrixWorld(true);
                    const worldPos = new THREE.Vector3();
                    board.group.getWorldPosition(worldPos);
                    dragPlane.setFromNormalAndCoplanarPoint(
                        new THREE.Vector3(0, 1, 0),
                        worldPos
                    );

                    // Record where on the plane the pointer first hit
                    getPointerNDC(event);
                    raycaster.setFromCamera(pointer, camera);
                    raycaster.ray.intersectPlane(dragPlane, dragStartHit);
                });

                renderer.domElement.addEventListener('pointermove', (event) => {
                    if (draggedBoard) {
                        getPointerNDC(event);
                        raycaster.setFromCamera(pointer, camera);
                        const planeHit = new THREE.Vector3();
                        if (raycaster.ray.intersectPlane(dragPlane, planeHit)) {
                            // Delta in world XZ — equals local delta since
                            // masterGroup has no rotation, only translation
                            const dx = planeHit.x - dragStartHit.x;
                            const dz = planeHit.z - dragStartHit.z;
                            draggedBoard.group.position.x = dragStartBoardPos.x + dx;
                            draggedBoard.group.position.z = dragStartBoardPos.z + dz;
                            // Y is never touched — stays at original value

                            // Update all harnesses connected to this board
                            for (const harness of harnessObjects) {
                                if (harness.fromName === draggedBoard.name || harness.toName === draggedBoard.name) {
                                    updateHarness(harness);
                                }
                            }
                        }
                    } else {
                        // Hover detection
                        const board = findHitBoard(event);
                        if (board !== hoveredBoard) {
                            if (hoveredBoard) setHighlight(hoveredBoard, false);
                            hoveredBoard = board;
                            if (hoveredBoard) setHighlight(hoveredBoard, true);
                            renderer.domElement.style.cursor = hoveredBoard ? 'grab' : '';
                        }
                    }
                });

                renderer.domElement.addEventListener('pointerup', (event) => {
                    if (draggedBoard) {
                        renderer.domElement.releasePointerCapture(event.pointerId);
                        draggedBoard = null;
                        controls.enabled = true;
                        renderer.domElement.style.cursor = hoveredBoard ? 'grab' : '';
                    }
                });

                async function loadBoards() {
                    const loader = new GLTFLoader();

                    masterGroup = new THREE.Group();
                    let xOffset = 0;

                    setStatus('Loading ' + boards.length + ' boards...');

                    for (const board of boards) {
                        if (!board.glb_uri) {
                            setStatus('Skipping ' + board.name + ' (no GLB)');
                            continue;
                        }
                        try {
                            setStatus('Loading ' + board.name + '...');
                            const gltf = await loader.loadAsync(board.glb_uri);
                            const boardGroup = new THREE.Group();
                            boardGroup.add(gltf.scene);

                            // Use original GLB materials — they render correctly out of the box
                            const bbox = new THREE.Box3().setFromObject(boardGroup);
                            const size = bbox.getSize(new THREE.Vector3());

                            if (size.x === 0 && size.y === 0 && size.z === 0) {
                                setStatus(board.name + ' has empty geometry');
                                continue;
                            }

                            // Position boards side by side with gap proportional to size
                            const gap = Math.max(size.x, size.y) * 1.5;
                            boardGroup.position.x = xOffset - bbox.min.x;
                            xOffset += size.x + gap;

                            loadedBoards.push({ name: board.name, group: boardGroup, size });
                            masterGroup.add(boardGroup);

                            // Board name label — centered on the board, floating above
                            const bboxCenter = bbox.getCenter(new THREE.Vector3());
                            const labelPos = new THREE.Vector3(
                                bboxCenter.x,
                                size.y,
                                bboxCenter.z
                            );
                            boardGroup.add(createTextSprite(board.name, labelPos));
                        } catch (err) {
                            setStatus('Failed: ' + board.name);
                            console.error('Failed to load GLB for ' + board.name, err);
                        }
                    }

                    // Create harness tubes between boards
                    for (const harness of harnesses) {
                        const fromBoard = loadedBoards.find(b => b.name === harness.fromBoard);
                        const toBoard = loadedBoards.find(b => b.name === harness.toBoard);
                        if (fromBoard && toBoard) {
                            const fromPos = getConnectorPosition(fromBoard, harness.fromPosition);
                            const toPos = getConnectorPosition(toBoard, harness.toPosition);
                            const avgSize = (fromBoard.size.x + toBoard.size.x) / 2;
                            const radius = avgSize * 0.015;

                            const curve = createCableCurve(fromPos, toPos);
                            const tubeGeo = new THREE.TubeGeometry(curve, 32, radius, 8, false);
                            const tubeMat = new THREE.MeshStandardMaterial({
                                color: 0x6688bb,
                                transparent: true,
                                opacity: 0.7,
                                roughness: 0.6,
                                metalness: 0.1,
                            });
                            const mesh = new THREE.Mesh(tubeGeo, tubeMat);
                            masterGroup.add(mesh);

                            // Harness label at midpoint
                            const mid = new THREE.Vector3().addVectors(fromPos, toPos).multiplyScalar(0.5);
                            mid.y += radius * 4;
                            const label = createTextSprite(harness.name, mid);
                            masterGroup.add(label);

                            harnessObjects.push({
                                fromName: harness.fromBoard,
                                toName: harness.toBoard,
                                fromPosition: harness.fromPosition,
                                toPosition: harness.toPosition,
                                mesh,
                                label,
                                radius,
                            });
                        }
                    }

                    scene.add(masterGroup);

                    if (loadedBoards.length === 0) {
                        setStatus('No boards loaded');
                        const loadingEl = document.getElementById('loading');
                        if (loadingEl) loadingEl.style.display = 'none';
                        return;
                    }

                    // Center and fit camera to all boards
                    const totalBox = new THREE.Box3().setFromObject(masterGroup);
                    const totalCenter = totalBox.getCenter(new THREE.Vector3());
                    const totalSize = totalBox.getSize(new THREE.Vector3());
                    masterGroup.position.sub(totalCenter);

                    const maxDim = Math.max(totalSize.x, totalSize.y, totalSize.z);
                    const distance = maxDim * 3;
                    camera.position.set(distance * 0.3, distance * 0.5, distance * 0.4);
                    camera.near = maxDim * 0.01;
                    camera.far = maxDim * 100;
                    camera.updateProjectionMatrix();
                    camera.lookAt(0, 0, 0);
                    controls.target.set(0, 0, 0);
                    controls.update();

                    // Directional lights scaled to scene size
                    const lightDist = maxDim * 2;
                    const keyLight = new THREE.DirectionalLight(0xffffff, 1.5);
                    keyLight.position.set(lightDist, lightDist * 2, lightDist);
                    scene.add(keyLight);
                    const fillLight = new THREE.DirectionalLight(0xffffff, 0.5);
                    fillLight.position.set(-lightDist, lightDist, -lightDist);
                    scene.add(fillLight);
                    const rimLight = new THREE.DirectionalLight(0xffffff, 0.6);
                    rimLight.position.set(0, lightDist, -lightDist * 2);
                    scene.add(rimLight);

                    // Update UI
                    const badge = document.getElementById('board-count');
                    if (badge) badge.textContent = loadedBoards.length + ' boards';
                    const loadingEl = document.getElementById('loading');
                    if (loadingEl) loadingEl.style.display = 'none';
                    const controlsEl = document.getElementById('viewer-controls');
                    if (controlsEl) controlsEl.style.display = 'flex';
                    setStatus('');
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
                });
                themeObserver.observe(document.body, {
                    attributes: true,
                    attributeFilter: ['class', 'style']
                });

                // Initialize
                loadBoards();
                animate();
            </script>
        `;

        return buildHtml({
            title: 'Multiboard 3D',
            styles: `
                html, body, #container { height: 100%; width: 100%; margin: 0; padding: 0; overflow: hidden; }
                #container { position: relative; background: var(--vscode-editor-background); }
                canvas { display: block; }
                #loading {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 12px;
                    font-family: var(--vscode-font-family);
                    color: var(--vscode-foreground);
                }
                .spinner {
                    width: 36px;
                    height: 36px;
                    border: 3px solid var(--vscode-editorWidget-border);
                    border-top-color: var(--vscode-progressBar-background);
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }
                @keyframes spin { to { transform: rotate(360deg); } }
                #viewer-controls {
                    position: absolute;
                    bottom: 8px;
                    left: 10px;
                    display: none;
                    align-items: center;
                    gap: 8px;
                    font-size: 11px;
                    color: var(--vscode-descriptionForeground);
                    z-index: 10;
                    font-family: var(--vscode-font-family);
                    background: var(--vscode-editor-background);
                    padding: 4px 8px;
                    border-radius: 4px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                }
                #status-info { font-size: 11px; opacity: 0.7; }
            `,
            body: `
                <div id="container">
                    <div id="loading">
                        <div class="spinner" aria-label="Loading"></div>
                        <div>Loading multiboard view...</div>
                        <div id="status-info" style="font-size: 11px; opacity: 0.7;"></div>
                    </div>
                    <div id="viewer-controls">
                        <span id="board-count">0 boards</span>
                    </div>
                </div>
                ${viewerScript}
            `,
        });
    }

    protected getLocalResourceRoots(): vscode.Uri[] {
        const roots = super.getLocalResourceRoots();

        if (this.manifestPath) {
            // Add the manifest's parent directory and the build/builds directory
            // so all sub-board GLB dirs are accessible
            const manifestDir = path.dirname(this.manifestPath);
            if (fs.existsSync(manifestDir) && !roots.some((r) => r.fsPath === manifestDir)) {
                roots.push(vscode.Uri.file(manifestDir));
            }

            // Also add the build/builds parent directory for cross-board GLB access
            const buildsDir = path.resolve(manifestDir, '..');
            if (fs.existsSync(buildsDir) && !roots.some((r) => r.fsPath === buildsDir)) {
                roots.push(vscode.Uri.file(buildsDir));
            }
        }

        return roots;
    }

    protected setupPanel(): void {}
}

let viewer: MultiboardViewerWebview | undefined;

export async function openMultiboardViewerPreview(manifestPath: string): Promise<void> {
    if (!viewer) {
        viewer = new MultiboardViewerWebview();
    }
    viewer.setManifestPath(manifestPath);
    await viewer.open();
}

export function closeMultiboardViewerPreview(): void {
    viewer?.dispose();
    viewer = undefined;
}

export function isMultiboardViewerOpen(): boolean {
    return viewer?.isOpen() ?? false;
}
