import { useState, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Text, RoundedBox } from '@react-three/drei';
import * as THREE from 'three';
import type { TreeNode, TreeNodeType } from '../types/tree';
import type { NodePosition } from '../lib/layoutEngine';
import { useTreeStore } from '../stores/treeStore';
import type { ThemeColors } from '../lib/theme';

// ── Warning color (Catppuccin yellow) ──
const WARN_COLOR = '#f9e2af';

interface TypeStyle { accent: string; icon: string; tag: string }

function getStyle(type: TreeNodeType, t: ThemeColors): TypeStyle {
  switch (type) {
    case 'source':     return { accent: t.nodeSource, icon: '\u26A1', tag: 'SOURCE' };
    case 'sink':       return { accent: t.nodeSink, icon: '\u25CF', tag: 'LOAD' };
    case 'converter':  return { accent: t.nodeBus, icon: '\u21C4', tag: 'REG' };
    case 'controller': return { accent: t.nodeController, icon: '\u25C6', tag: 'CTRL' };
    case 'target':     return { accent: t.nodeTarget, icon: '\u25CB', tag: 'TGT' };
  }
}

function getDetail(node: TreeNode): string | null {
  const m = node.meta;
  if (!m) return null;
  if (node.type === 'source')
    return [m.voltage, m.max_current].filter(v => v && v !== '?').join(' \u00b7 ') || null;
  if (node.type === 'converter') {
    const v = (m.voltage_in && m.voltage_out) ? `${m.voltage_in} \u2192 ${m.voltage_out}` : null;
    const c = (m.max_current && m.max_current !== '?') ? `${m.max_current} out` : null;
    return [v, c].filter(Boolean).join(' \u00b7 ') || null;
  }
  if (node.type === 'sink')
    return (m.max_current && m.max_current !== '?' && m.max_current !== '0A') ? m.max_current : null;
  if (node.type === 'target') return m.address ?? null;
  if (node.type === 'controller') return m.bus_frequency ?? null;
  return null;
}

/** Check if a node has a warning condition. */
function hasWarning(node: TreeNode): string | null {
  if (node.resolved === false) return 'Address unresolved';
  return null;
}

/** Pulsing warning ring that breathes gently. */
function WarningPulse({ w, h, active }: { w: number; h: number; active: boolean }) {
  const matRef = useRef<THREE.MeshBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (!matRef.current) return;
    // Gentle sine pulse: 0.08 to 0.22 opacity, ~1.5s period
    const t = Math.sin(clock.getElapsedTime() * 2.2) * 0.5 + 0.5;
    const base = active ? 0.15 : 0.08;
    const range = active ? 0.2 : 0.12;
    matRef.current.opacity = base + t * range;
  });

  return (
    <RoundedBox
      args={[w + 0.06, h + 0.06, 0.001]}
      radius={0.048}
      smoothness={4}
      position={[0, 0, -0.004]}
    >
      <meshBasicMaterial ref={matRef} color={WARN_COLOR} transparent opacity={0.1} />
    </RoundedBox>
  );
}

/** Small warning triangle icon. */
function WarningBadge({ x, y, theme }: { x: number; y: number; theme: ThemeColors }) {
  const matRef = useRef<THREE.MeshBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (!matRef.current) return;
    const t = Math.sin(clock.getElapsedTime() * 2.2) * 0.5 + 0.5;
    matRef.current.opacity = 0.6 + t * 0.4;
  });

  return (
    <group position={[x, y, 0.015]}>
      <Text fontSize={0.09} color={WARN_COLOR} anchorX="center" anchorY="middle" font={undefined}>
        {'\u26A0'}
      </Text>
    </group>
  );
}

export function TreeNodeMesh({ node, position, theme }: { node: TreeNode; position: NodePosition; theme: ThemeColors }) {
  const [hovered, setHovered] = useState(false);
  const { hoveredNode, selectedNode, setHoveredNode, setSelectedNode } = useTreeStore();
  const isHovered = hoveredNode === node.id || hovered;
  const isSelected = selectedNode === node.id;
  const s = getStyle(node.type, theme);
  const detail = useMemo(() => getDetail(node), [node]);
  const warning = useMemo(() => hasWarning(node), [node]);

  const accent = isSelected ? theme.accent : s.accent;

  const W = position.width / 100;
  const H = position.height / 100;
  const BAR = 0.025;
  const L = -W / 2 + BAR + 0.05;

  return (
    <group
      position={[position.x / 100, position.y / 100, position.z]}
      scale={isHovered ? [1.02, 1.02, 1] : [1, 1, 1]}
      onPointerEnter={(e) => { e.stopPropagation(); setHovered(true); setHoveredNode(node.id); document.body.style.cursor = 'pointer'; }}
      onPointerLeave={() => { setHovered(false); setHoveredNode(null); document.body.style.cursor = 'auto'; }}
      onClick={(e) => { e.stopPropagation(); setSelectedNode(node.id); }}
    >
      {/* ── Warning pulse ring (always visible if warning, brighter when selected) ── */}
      {warning && (
        <WarningPulse w={W} h={H} active={isSelected || isHovered} />
      )}

      {/* ── Hover/select glow (only if no warning, to not conflict) ── */}
      {!warning && (isHovered || isSelected) && (
        <RoundedBox args={[W + 0.08, H + 0.08, 0.001]} radius={0.05} smoothness={4} position={[0, 0, -0.005]}>
          <meshBasicMaterial color={accent} transparent opacity={isSelected ? 0.18 : 0.09} />
        </RoundedBox>
      )}

      {/* ── Border ring ── */}
      <RoundedBox args={[W + 0.012, H + 0.012, 0.002]} radius={0.038} smoothness={4} position={[0, 0, -0.001]}>
        <meshBasicMaterial color={warning ? WARN_COLOR : accent} transparent opacity={warning ? 0.25 : 0.3} />
      </RoundedBox>

      {/* ── Card body ── */}
      <RoundedBox args={[W, H, 0.006]} radius={0.032} smoothness={4}>
        <meshBasicMaterial color={theme.bgPrimary} />
      </RoundedBox>

      {/* ── Accent bar (yellow if warning) ── */}
      <mesh position={[-W / 2 + BAR / 2 + 0.004, 0, 0.007]}>
        <planeGeometry args={[BAR, H * 0.6]} />
        <meshBasicMaterial color={warning ? WARN_COLOR : accent} transparent opacity={warning ? 0.7 : 0.9} />
      </mesh>

      {/* ── Tag + Name ── */}
      <Text position={[L, detail ? 0.06 : 0, 0.01]} fontSize={0.065} color={warning ? WARN_COLOR : accent} anchorX="left" anchorY="middle" letterSpacing={0.06} font={undefined}>
        {s.tag}
      </Text>
      <Text position={[L + s.tag.length * 0.04 + 0.06, detail ? 0.06 : 0, 0.01]} fontSize={0.1} color={theme.textPrimary} anchorX="left" anchorY="middle" maxWidth={W - 0.5} font={undefined}>
        {node.label}
      </Text>

      {/* ── Detail line ── */}
      {detail && (
        <Text position={[L, -0.1, 0.01]} fontSize={0.075} color={warning ? WARN_COLOR : accent} anchorX="left" anchorY="middle" maxWidth={W - 0.2} font={undefined}>
          {detail}
        </Text>
      )}

      {/* ── Warning badge (top-right corner) ── */}
      {warning && (
        <WarningBadge x={W / 2 - 0.08} y={H / 2 - 0.06} theme={theme} />
      )}
    </group>
  );
}
