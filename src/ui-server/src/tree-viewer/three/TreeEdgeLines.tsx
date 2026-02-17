import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Line } from '@react-three/drei';
import * as THREE from 'three';
import type { TreeEdge } from '../types/tree';
import type { NodePosition } from '../utils/layoutEngine';
import type { ThemeColors } from '../utils/theme';

/** Build smooth cubic bezier points for an edge. */
function buildEdgeCurve(from: NodePosition, to: NodePosition, segments = 40): THREE.Vector3[] {
  const startX = (from.x + from.width / 2) / 100;
  const startY = from.y / 100;
  const endX = (to.x - to.width / 2) / 100;
  const endY = to.y / 100;
  const dx = endX - startX;

  const curve = new THREE.CubicBezierCurve3(
    new THREE.Vector3(startX, startY, -0.01),
    new THREE.Vector3(startX + dx * 0.4, startY, -0.01),
    new THREE.Vector3(startX + dx * 0.6, endY, -0.01),
    new THREE.Vector3(endX, endY, -0.01),
  );
  return curve.getPoints(segments);
}

/**
 * Map current (amps) to visual weight.
 * Returns a normalized 0..1 value for scaling visual properties.
 */
function currentWeight(amps: number | undefined): number {
  if (amps === undefined || amps <= 0) return 0.1;
  // log scale: 0.1mA=0, 3A=1
  const t = Math.max(0, Math.min(1, (Math.log10(Math.max(amps, 0.0001)) + 3.5) / 4));
  return t;
}

/** Interpolate two hex colors. */
function lerpColor(a: string, b: string, t: number): string {
  const p = (hex: string) => {
    hex = hex.replace('#', '');
    return [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16)];
  };
  const ca = p(a), cb = p(b);
  const r = Math.round(ca[0] + (cb[0] - ca[0]) * t);
  const g = Math.round(ca[1] + (cb[1] - ca[1]) * t);
  const bl = Math.round(ca[2] + (cb[2] - ca[2]) * t);
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${bl.toString(16).padStart(2, '0')}`;
}

interface EdgeRenderData {
  key: string;
  points: THREE.Vector3[];
  weight: number;
}

/** Single animated dot that pulses along the path. */
function FlowDot({ points, color, speed, radius, offset }: {
  points: THREE.Vector3[];
  color: string;
  speed: number;
  radius: number;
  offset: number;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const matRef = useRef<THREE.MeshBasicMaterial>(null);
  const progress = useRef(offset);

  useFrame((_, delta) => {
    if (!meshRef.current || !matRef.current) return;
    progress.current = (progress.current + delta * speed) % 1;
    const t = progress.current;
    const idx = Math.floor(t * (points.length - 1));
    const frac = t * (points.length - 1) - idx;
    const a = points[Math.min(idx, points.length - 1)];
    const b = points[Math.min(idx + 1, points.length - 1)];
    meshRef.current.position.lerpVectors(a, b, frac);
    // Fade in at start, fade out at end
    const fade = Math.sin(t * Math.PI);
    matRef.current.opacity = fade * 0.8;
  });

  return (
    <mesh ref={meshRef}>
      <circleGeometry args={[radius, 10]} />
      <meshBasicMaterial ref={matRef} color={color} transparent opacity={0} />
    </mesh>
  );
}

interface TreeEdgeLinesProps {
  edges: TreeEdge[];
  positions: Map<string, NodePosition>;
  theme: ThemeColors;
}

export function TreeEdgeLines({ edges, positions, theme }: TreeEdgeLinesProps) {
  const edgeData = useMemo<EdgeRenderData[]>(() => {
    return edges
      .map((edge) => {
        const from = positions.get(edge.source);
        const to = positions.get(edge.target);
        if (!from || !to) return null;
        return {
          key: edge.id,
          points: buildEdgeCurve(from, to),
          weight: currentWeight(edge.currentAmps),
        };
      })
      .filter(Boolean) as EdgeRenderData[];
  }, [edges, positions]);

  // Color ramp: low current = soft muted tone, high current = vivid accent
  const lowColor = lerpColor(theme.bgHover, theme.textMuted, 0.5);
  const highColor = theme.nodeSource;

  return (
    <group>
      {edgeData.map((edge) => {
        const w = edge.weight;
        const color = lerpColor(lowColor, highColor, w);
        const lineWidth = 1 + w * 3;        // 1..4
        const opacity = 0.2 + w * 0.4;      // 0.2..0.6
        const dotSpeed = 0.2 + w * 0.4;     // gentle
        const dotRadius = 0.01 + w * 0.015;

        return (
          <group key={edge.key}>
            <Line
              points={edge.points}
              color={color}
              lineWidth={lineWidth}
              transparent
              opacity={opacity}
            />
            {/* Just one dot per edge -- clean, not busy */}
            <FlowDot
              points={edge.points}
              color={color}
              speed={dotSpeed}
              radius={dotRadius}
              offset={Math.random()}
            />
          </group>
        );
      })}
    </group>
  );
}
