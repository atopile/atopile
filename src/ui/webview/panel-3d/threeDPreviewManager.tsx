import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { DRACOLoader } from "three/examples/jsm/loaders/DRACOLoader.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { RGBELoader } from "three/examples/jsm/loaders/RGBELoader.js";
import { createWebviewLogger } from "../shared/logger";

interface ThreeDPreviewProps {
  modelUri: string;
}

type TexturedMaterial = THREE.MeshStandardMaterial & {
  map?: THREE.Texture & {
    image?: CanvasImageSource & { width: number; height: number };
    flipY?: boolean;
  };
  color?: THREE.Color;
};

const logger = createWebviewLogger("Panel3D");

export function ThreeDPreview({ modelUri }: ThreeDPreviewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    let disposed = false;
    let frameHandle = 0;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.01,
      1000,
    );

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: "high-performance",
    });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.replaceChildren(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 0.01;

    const getThemeBackground = () => {
      const style = getComputedStyle(document.body);
      const bgColor = style.getPropertyValue("--vscode-editor-background").trim();
      return new THREE.Color(bgColor || "#1e1e1e");
    };

    const resize = () => {
      const width = container.clientWidth || 1;
      const height = container.clientHeight || 1;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };

    const loadEnvironment = async () => {
      const bgColor = getThemeBackground();
      const rgbeLoader = new RGBELoader();
      try {
        const envMap = await rgbeLoader.loadAsync(
          "https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/1k/studio_small_08_1k.hdr",
        );
        if (disposed) {
          envMap.dispose();
          return;
        }
        envMap.mapping = THREE.EquirectangularReflectionMapping;
        scene.environment = envMap;
        scene.background = bgColor;
        renderer.setClearColor(bgColor);
      } catch (error) {
        logger.warn(
          `Failed to load HDR: ${error instanceof Error ? error.message : String(error)}`,
        );
        scene.background = bgColor;
        renderer.setClearColor(bgColor);
      }
    };

    const loadModel = async () => {
      const loader = new GLTFLoader();
      const dracoLoader = new DRACOLoader();
      dracoLoader.setDecoderPath(
        "https://www.gstatic.com/draco/versioned/decoders/1.5.6/",
      );
      loader.setDRACOLoader(dracoLoader);

      try {
        const gltf = await loader.loadAsync(modelUri);
        if (disposed) {
          dracoLoader.dispose();
          return;
        }

        const model = gltf.scene;

        model.traverse((child) => {
          const mesh = child as THREE.Mesh;
          const oldMat = mesh.material as
            | TexturedMaterial
            | TexturedMaterial[]
            | undefined;

          if (!mesh.isMesh || !oldMat || Array.isArray(oldMat)) {
            return;
          }

          if (oldMat.map?.image) {
            const img = oldMat.map.image;
            const canvas = document.createElement("canvas");
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext("2d");
            if (!ctx) {
              return;
            }

            ctx.drawImage(img, 0, 0);
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const { data } = imageData;

            for (let i = 0; i < data.length; i += 4) {
              const r = data[i];
              const g = data[i + 1];
              const b = data[i + 2];

              if (g > 80 && g > r * 1.3 && g > b * 1.3) {
                data[i] = 30;
                data[i + 1] = 32;
                data[i + 2] = 35;
              } else if (r > 150 && g > 120 && b > 60 && r > b * 1.5) {
                data[i] = Math.min(255, r * 0.85);
                data[i + 1] = Math.min(255, g * 0.8);
                data[i + 2] = Math.min(255, b * 0.6);
              }
            }

            ctx.putImageData(imageData, 0, 0);

            const newTexture = new THREE.CanvasTexture(canvas);
            newTexture.flipY = oldMat.map.flipY ?? false;
            newTexture.colorSpace = THREE.SRGBColorSpace;

            mesh.material = new THREE.MeshPhysicalMaterial({
              map: newTexture,
              roughness: 0.6,
              metalness: 0.0,
              clearcoat: 0.15,
              clearcoatRoughness: 0.4,
              envMapIntensity: 0.8,
            });
            oldMat.dispose();
            return;
          }

          mesh.material = new THREE.MeshPhysicalMaterial({
            color: oldMat.color,
            roughness: 0.5,
            metalness: 0.0,
            envMapIntensity: 1.0,
          });
          oldMat.dispose();
        });

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
        logger.error(
          `Failed to load model: ${error instanceof Error ? error.message : String(error)}`,
        );
      } finally {
        dracoLoader.dispose();
      }
    };

    const animate = () => {
      if (disposed) {
        return;
      }
      frameHandle = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);

    const themeObserver = new MutationObserver(() => {
      const bgColor = getThemeBackground();
      scene.background = bgColor;
      renderer.setClearColor(bgColor);
    });
    themeObserver.observe(document.body, {
      attributes: true,
      attributeFilter: ["class", "style"],
    });

    loadEnvironment();
    loadModel();
    resize();
    animate();

    return () => {
      disposed = true;
      cancelAnimationFrame(frameHandle);
      resizeObserver.disconnect();
      themeObserver.disconnect();
      controls.dispose();
      renderer.dispose();
      scene.environment?.dispose?.();
      scene.traverse((object) => {
        const mesh = object as THREE.Mesh;
        mesh.geometry?.dispose?.();
        if (!mesh.material) {
          return;
        }
        if (Array.isArray(mesh.material)) {
          for (const material of mesh.material) {
            material.dispose();
          }
          return;
        }
        mesh.material.dispose();
      });
    };
  }, [modelUri]);

  return <div className="panel-3d-canvas" ref={containerRef} />;
}
