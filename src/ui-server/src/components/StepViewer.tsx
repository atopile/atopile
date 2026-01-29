import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

interface StepViewerProps {
  src: string
  className?: string
  style?: React.CSSProperties
}

export default function StepViewer({ src, className, style }: StepViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const sceneRef = useRef<{
    scene: THREE.Scene
    camera: THREE.PerspectiveCamera
    renderer: THREE.WebGLRenderer
    controls: OrbitControls
    animationId: number
  } | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let cancelled = false

    const init = async () => {
      setIsLoading(true)
      setError(null)

      try {
        // Dynamically import occt-import-js (large WASM) first
        // This way we only fetch the model if WASM loads successfully
        let occt
        try {
          const occtModule = await import('occt-import-js')
          // Pass locateFile to specify where to find the WASM
          // Check for VS Code extension provided URL, fall back to same origin
          const wasmUrl = (window as { __ATOPILE_WASM_URL__?: string }).__ATOPILE_WASM_URL__
            || new URL('/occt-import-js.wasm', window.location.href).href
          occt = await occtModule.default({
            locateFile: (file: string) => {
              if (file.endsWith('.wasm')) {
                return wasmUrl
              }
              return file
            }
          })
        } catch (wasmError) {
          console.error('WASM load error:', wasmError)
          throw new Error('3D viewer not available in this environment')
        }

        if (cancelled) return

        // Fetch the STEP file
        const response = await fetch(src)
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('No 3D model available for this part')
          }
          throw new Error(`Failed to load model: ${response.status}`)
        }
        const buffer = await response.arrayBuffer()
        const fileBuffer = new Uint8Array(buffer)

        if (cancelled) return

        // Parse STEP file
        const result = occt.ReadStepFile(fileBuffer, null)
        if (!result.success || result.meshes.length === 0) {
          throw new Error('Failed to parse 3D model')
        }

        if (cancelled) return

        // Setup Three.js scene
        const width = container.clientWidth || 300
        const height = container.clientHeight || 200

        const scene = new THREE.Scene()
        // Use VS Code theme background color
        const bgColor = getComputedStyle(container).getPropertyValue('--vscode-editor-background').trim() || '#1e1e2e'
        scene.background = new THREE.Color(bgColor)

        const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)

        const renderer = new THREE.WebGLRenderer({ antialias: true })
        renderer.setSize(width, height)
        renderer.setPixelRatio(window.devicePixelRatio)
        container.appendChild(renderer.domElement)

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
        scene.add(ambientLight)

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
        directionalLight.position.set(1, 1, 1)
        scene.add(directionalLight)

        const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.4)
        directionalLight2.position.set(-1, -1, -1)
        scene.add(directionalLight2)

        // Convert OCCT meshes to Three.js
        const group = new THREE.Group()

        for (const mesh of result.meshes) {
          const geometry = new THREE.BufferGeometry()

          geometry.setAttribute(
            'position',
            new THREE.Float32BufferAttribute(mesh.attributes.position.array, 3)
          )

          if (mesh.attributes.normal) {
            geometry.setAttribute(
              'normal',
              new THREE.Float32BufferAttribute(mesh.attributes.normal.array, 3)
            )
          } else {
            geometry.computeVertexNormals()
          }

          geometry.setIndex(mesh.index.array)

          // Build vertex colors from brep_faces, default to grey
          const vertexCount = mesh.attributes.position.array.length / 3
          const colors = new Float32Array(vertexCount * 3)
          colors.fill(0.7) // Default grey

          // Apply per-face colors from brep_faces
          const brepFaces = mesh.brep_faces as { first: number; last: number; color?: number[] }[] | undefined
          if (brepFaces) {
            const indices = mesh.index.array
            for (const face of brepFaces) {
              if (!face.color || face.color.length < 3) continue
              const [r, g, b] = face.color
              // first/last are triangle indices, multiply by 3 for index array positions
              const start = face.first * 3
              const end = (face.last + 1) * 3
              for (let i = start; i < end && i < indices.length; i++) {
                const vi = indices[i] * 3
                if (vi + 2 < colors.length) {
                  colors[vi] = r
                  colors[vi + 1] = g
                  colors[vi + 2] = b
                }
              }
            }
          }

          geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))

          const material = new THREE.MeshStandardMaterial({
            vertexColors: true,
            metalness: 0.1,
            roughness: 0.6,
            side: THREE.DoubleSide,
          })

          group.add(new THREE.Mesh(geometry, material))
        }

        scene.add(group)

        // Center and fit model
        const box = new THREE.Box3().setFromObject(group)
        const center = box.getCenter(new THREE.Vector3())
        const size = box.getSize(new THREE.Vector3())

        group.position.sub(center)

        const maxDim = Math.max(size.x, size.y, size.z)
        const distance = maxDim * 2
        camera.position.set(distance * 0.7, distance * 0.5, distance * 0.7)
        camera.lookAt(0, 0, 0)

        // Controls
        const controls = new OrbitControls(camera, renderer.domElement)
        controls.enableDamping = true
        controls.dampingFactor = 0.05
        controls.target.set(0, 0, 0)
        controls.update()

        // Animation loop
        const animate = () => {
          const animationId = requestAnimationFrame(animate)
          if (sceneRef.current) {
            sceneRef.current.animationId = animationId
          }
          controls.update()
          renderer.render(scene, camera)
        }

        sceneRef.current = {
          scene,
          camera,
          renderer,
          controls,
          animationId: 0,
        }

        animate()
        setIsLoading(false)

        // Handle resize
        const handleResize = () => {
          if (!container || !sceneRef.current) return
          const w = container.clientWidth
          const h = container.clientHeight
          sceneRef.current.camera.aspect = w / h
          sceneRef.current.camera.updateProjectionMatrix()
          sceneRef.current.renderer.setSize(w, h)
        }

        const resizeObserver = new ResizeObserver(handleResize)
        resizeObserver.observe(container)

        return () => {
          resizeObserver.disconnect()
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load 3D model')
          setIsLoading(false)
        }
      }
    }

    init()

    return () => {
      cancelled = true
      if (sceneRef.current) {
        cancelAnimationFrame(sceneRef.current.animationId)
        sceneRef.current.renderer.dispose()
        sceneRef.current.controls.dispose()
        const canvas = sceneRef.current.renderer.domElement
        canvas.parentNode?.removeChild(canvas)
        sceneRef.current = null
      }
    }
  }, [src])

  return (
    <div
      ref={containerRef}
      className={`detail-visual-frame detail-visual-stack ${className || ''}`}
      style={{ width: '100%', height: '100%', ...style }}
    >
      {isLoading && (
        <div className="detail-visual-spinner">
          <span className="spinner" />
          <span>Loading 3D model...</span>
        </div>
      )}
      {error && (
        <div className="detail-visual-empty">
          {error}
        </div>
      )}
    </div>
  )
}
