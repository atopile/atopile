import { useMemo } from 'react';
import { Text, RoundedBox } from '@react-three/drei';
import type { NodePosition } from '../lib/layoutEngine';
import type { ThemeColors } from '../lib/theme';

interface GroupBoxProps {
  groupId: string;
  label: string;
  accent: string;
  memberIds: string[];
  positions: Map<string, NodePosition>;
  theme: ThemeColors;
}

export function GroupBox({ label, accent, memberIds, positions, theme }: GroupBoxProps) {
  const bounds = useMemo(() => {
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const id of memberIds) {
      const pos = positions.get(id);
      if (!pos) continue;
      const x = pos.x / 100;
      const y = pos.y / 100;
      const hw = pos.width / 200;
      const hh = pos.height / 200;
      minX = Math.min(minX, x - hw);
      maxX = Math.max(maxX, x + hw);
      minY = Math.min(minY, y - hh);
      maxY = Math.max(maxY, y + hh);
    }
    if (!isFinite(minX)) return null;

    const padX = 0.12;
    const padBottom = 0.06;
    const padTop = 0.24; // space above nodes for header text
    const contentH = maxY - minY;
    const contentW = maxX - minX;
    const w = contentW + padX * 2;
    const h = contentH + padTop + padBottom;
    // Center: shift down slightly since padTop > padBottom
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2 + (padTop - padBottom) / 2;
    return { cx, cy, w, h };
  }, [memberIds, positions]);

  if (!bounds) return null;

  const BAR = 0.025;

  return (
    <group position={[bounds.cx, bounds.cy, -0.009]}>
      {/* Border ring (same style as node cards) */}
      <RoundedBox
        args={[bounds.w + 0.012, bounds.h + 0.012, 0.001]}
        radius={0.048}
        smoothness={4}
        position={[0, 0, -0.002]}
      >
        <meshBasicMaterial color={accent} transparent opacity={0.2} />
      </RoundedBox>

      {/* Card background */}
      <RoundedBox args={[bounds.w, bounds.h, 0.002]} radius={0.042} smoothness={4}>
        <meshBasicMaterial color={theme.bgSecondary} />
      </RoundedBox>

      {/* Accent side bar */}
      <mesh position={[-bounds.w / 2 + BAR / 2 + 0.006, 0, 0.004]}>
        <planeGeometry args={[BAR, bounds.h * 0.6]} />
        <meshBasicMaterial color={accent} transparent opacity={0.8} />
      </mesh>

      {/* Header: tag + label at top of box */}
      <Text
        position={[-bounds.w / 2 + BAR + 0.06, bounds.h / 2 - 0.12, 0.005]}
        fontSize={0.055}
        color={accent}
        anchorX="left"
        anchorY="middle"
        letterSpacing={0.06}
        font={undefined}
      >
        DEVICE
      </Text>
      <Text
        position={[-bounds.w / 2 + BAR + 0.06 + 0.28, bounds.h / 2 - 0.12, 0.005]}
        fontSize={0.1}
        color={theme.textPrimary}
        anchorX="left"
        anchorY="middle"
        font={undefined}
      >
        {label}
      </Text>
    </group>
  );
}
