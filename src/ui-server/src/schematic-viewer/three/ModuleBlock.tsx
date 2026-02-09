import { useMemo, memo } from 'react';
import { Text, RoundedBox, Line } from '@react-three/drei';
import type { SchematicModule, SchematicInterfacePin } from '../types/schematic';
import { getModuleGridAlignmentOffset } from '../types/schematic';
import type { ThemeColors } from '../lib/theme';
import { getPinColor } from '../lib/theme';
import {
  getUprightTextTransform,
  anchorFromVisualSide,
} from '../lib/itemTransform';
import {
  isBusInterface,
  getInterfaceDotRadius,
  getInterfaceNameInset,
  getInterfaceParallelOffset,
  getInterfaceStrokeStyle,
} from './interfaceVisuals';

const NO_RAYCAST = () => {};
const MODULE_INSET = 0.72;

function moduleAccentColor(typeName: string): string {
  const t = typeName.toLowerCase();
  if (/power|ldo|buck|boost|regulator/i.test(t)) return '#f38ba8';
  if (/mcu|esp|stm|rp2|cortex|cpu/i.test(t)) return '#89b4fa';
  if (/sensor|bme|bmp|lis|mpu|accel/i.test(t)) return '#a6e3a1';
  if (/led|light|display/i.test(t)) return '#f9e2af';
  if (/usb|conn|jack/i.test(t)) return '#94e2d5';
  if (/i2c|spi|uart|bus/i.test(t)) return '#cba6f7';
  return '#89b4fa';
}

// ── Public component ───────────────────────────────────────────

interface Props {
  module: SchematicModule;
  theme: ThemeColors;
  isSelected: boolean;
  isHovered: boolean;
  isDragging: boolean;
  selectedNetId: string | null;
  netsForModule: Map<string, string>;
  rotation?: number;
  mirrorX?: boolean;
  mirrorY?: boolean;
}

export const ModuleBlock = memo(function ModuleBlock({
  module,
  theme,
  isSelected,
  isHovered,
  isDragging,
  selectedNetId,
  netsForModule,
  rotation = 0,
  mirrorX = false,
  mirrorY = false,
}: Props) {
  const W = module.bodyWidth;
  const H = module.bodyHeight;
  const accent = useMemo(
    () => moduleAccentColor(module.typeName),
    [module.typeName],
  );

  const RADIUS = Math.min(0.78, Math.max(0.34, Math.min(W, H) * 0.055));
  const maxDim = Math.min(W, H);
  const titleFontSize = Math.min(1.48, Math.max(0.88, maxDim * 0.085));
  const subtitleFontSize = Math.min(0.92, Math.max(0.62, titleFontSize * 0.56));
  const maxTextWidth = W * 0.74;
  const showType = module.typeName.trim() !== module.name.trim();
  const zOffset = isDragging ? 0.5 : 0;
  const gridOffset = useMemo(
    () => getModuleGridAlignmentOffset(module),
    [module],
  );

  const textTf = useMemo(
    () => getUprightTextTransform(rotation, mirrorX, mirrorY),
    [rotation, mirrorX, mirrorY],
  );

  return (
    <group position={[gridOffset.x, gridOffset.y, zOffset]} raycast={NO_RAYCAST}>
      {/* Interactive hit target for select/drag/double-click to enter. */}
      <mesh position={[0, 0, -0.07]}>
        <planeGeometry args={[W + 0.6, H + 0.6]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {isSelected && (
        <RoundedBox
          args={[W + 1.26, H + 1.26, 0.001]}
          radius={RADIUS + 0.22}
          smoothness={4}
          position={[0, 0, -0.06]}
          raycast={NO_RAYCAST}
        >
          <meshBasicMaterial color={accent} transparent opacity={0.2} depthWrite={false} />
        </RoundedBox>
      )}

      {isHovered && !isSelected && (
        <RoundedBox
          args={[W + 0.62, H + 0.62, 0.001]}
          radius={RADIUS + 0.1}
          smoothness={4}
          position={[0, 0, -0.06]}
          raycast={NO_RAYCAST}
        >
          <meshBasicMaterial color={accent} transparent opacity={0.09} depthWrite={false} />
        </RoundedBox>
      )}

      <RoundedBox
        args={[W + 0.14, H + 0.14, 0.001]}
        radius={RADIUS + 0.03}
        smoothness={4}
        position={[0, 0, -0.04]}
        raycast={NO_RAYCAST}
      >
        <meshBasicMaterial
          color={isSelected ? accent : theme.bodyBorder}
          transparent
          opacity={isSelected ? 0.96 : 0.86}
          depthWrite={false}
        />
      </RoundedBox>

      <RoundedBox
        args={[W, H, 0.001]}
        radius={RADIUS}
        smoothness={4}
        position={[0, 0, -0.03]}
        raycast={NO_RAYCAST}
      >
        <meshBasicMaterial color={theme.bodyFill} transparent opacity={0.97} depthWrite={false} />
      </RoundedBox>

      <RoundedBox
        args={[Math.max(2, W - MODULE_INSET), Math.max(2, H - MODULE_INSET), 0.001]}
        radius={Math.max(0.22, RADIUS * 0.76)}
        smoothness={4}
        position={[0, 0, -0.02]}
        raycast={NO_RAYCAST}
      >
        <meshBasicMaterial color={theme.bgPrimary} transparent opacity={0.2} depthWrite={false} />
      </RoundedBox>

      <RoundedBox
        args={[Math.max(2, W - MODULE_INSET), Math.max(2, H - MODULE_INSET), 0.001]}
        radius={Math.max(0.22, RADIUS * 0.76)}
        smoothness={4}
        position={[0, 0, -0.01]}
        raycast={NO_RAYCAST}
      >
        <meshBasicMaterial color={accent} transparent opacity={0.1} depthWrite={false} />
      </RoundedBox>

      <mesh position={[0, H / 2 - 0.52, -0.008]} raycast={NO_RAYCAST}>
        <planeGeometry args={[Math.max(1.6, W - 1.12), 0.3]} />
        <meshBasicMaterial color={accent} transparent opacity={0.48} depthWrite={false} />
      </mesh>

      <group position={[0, 0, 0.001]} rotation={[0, 0, textTf.rotationZ]} scale={[textTf.scaleX, textTf.scaleY, 1]}>
        <Text
          position={[0, showType ? 0.68 : 0.2, 0]}
          fontSize={titleFontSize}
          color={accent}
          anchorX="center"
          anchorY="middle"
          letterSpacing={0.028}
          maxWidth={maxTextWidth}
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {module.name}
        </Text>

        {showType && (
          <Text
            position={[0, -0.55, 0]}
            fontSize={subtitleFontSize}
            color={theme.textMuted}
            anchorX="center"
            anchorY="middle"
            maxWidth={W * 0.72}
            letterSpacing={0.014}
            font={undefined}
            raycast={NO_RAYCAST}
          >
            {module.typeName}
          </Text>
        )}
      </group>

      <group position={[W / 2 - 2.3, H / 2 - 1.2, 0.001]} rotation={[0, 0, textTf.rotationZ]} scale={[textTf.scaleX, textTf.scaleY, 1]}>
        <RoundedBox args={[3.8, 1.2, 0.001]} radius={0.28} smoothness={4} raycast={NO_RAYCAST}>
          <meshBasicMaterial color={accent} transparent opacity={0.17} depthWrite={false} />
        </RoundedBox>
        <Text
          position={[0, 0, 0.001]}
          fontSize={0.6}
          color={theme.textSecondary}
          anchorX="center"
          anchorY="middle"
          letterSpacing={0.02}
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {`${module.componentCount} parts`}
        </Text>
      </group>

      <group position={[-W / 2 + 1.6, H / 2 - 1.2, 0.001]} rotation={[0, 0, textTf.rotationZ]} scale={[textTf.scaleX, textTf.scaleY, 1]}>
        <Text
          fontSize={0.62}
          color={theme.textMuted}
          anchorX="left"
          anchorY="middle"
          letterSpacing={0.04}
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {'MODULE'}
        </Text>
      </group>

      {module.interfacePins.map((pin) => (
        <InterfacePinElement
          key={pin.id}
          pin={pin}
          theme={theme}
          netId={netsForModule.get(pin.id) ?? null}
          selectedNetId={selectedNetId}
          textRotationZ={textTf.rotationZ}
          textScaleX={textTf.scaleX}
          textScaleY={textTf.scaleY}
          rotationDeg={rotation}
          mirrorX={mirrorX}
          mirrorY={mirrorY}
        />
      ))}
    </group>
  );
});

// ── Interface pin element ──────────────────────────────────────

const InterfacePinElement = memo(function InterfacePinElement({
  pin,
  theme,
  netId,
  selectedNetId,
  textRotationZ = 0,
  textScaleX = 1,
  textScaleY = 1,
  rotationDeg = 0,
  mirrorX = false,
  mirrorY = false,
}: {
  pin: SchematicInterfacePin;
  theme: ThemeColors;
  netId: string | null;
  selectedNetId: string | null;
  textRotationZ?: number;
  textScaleX?: number;
  textScaleY?: number;
  rotationDeg?: number;
  mirrorX?: boolean;
  mirrorY?: boolean;
}) {
  const color = getPinColor(pin.category, theme);
  const isHighlighted = netId !== null && netId === selectedNetId;
  const isBus = isBusInterface(pin.signals);
  const dotRadius = getInterfaceDotRadius(pin.signals);
  const pinX = pin.x;
  const pinY = pin.y;
  const bodyX = pin.bodyX;
  const bodyY = pin.bodyY;

  const offset = getInterfaceParallelOffset(pinX, pinY, bodyX, bodyY);
  const perpX = offset.x;
  const perpY = offset.y;
  const lineColor = isHighlighted ? theme.accent : color;
  const stroke = getInterfaceStrokeStyle(pin.signals, isHighlighted);
  const edgeMarkerW = pin.side === 'left' || pin.side === 'right'
    ? 0.22
    : isBus
      ? 1.16
      : 0.86;
  const edgeMarkerH = pin.side === 'left' || pin.side === 'right'
    ? isBus
      ? 1.28
      : 0.9
    : 0.22;

  let nameX: number;
  let nameY: number;
  const NAME_INSET = getInterfaceNameInset(pin.signals);
  if (pin.side === 'left') {
    nameX = bodyX + NAME_INSET;
    nameY = pinY;
  } else if (pin.side === 'right') {
    nameX = bodyX - NAME_INSET;
    nameY = pinY;
  } else if (pin.side === 'top') {
    nameX = pinX;
    nameY = bodyY - NAME_INSET;
  } else {
    nameX = pinX;
    nameY = bodyY + NAME_INSET;
  }
  const effectiveNameAnchorX = anchorFromVisualSide(pin.side, {
    rotationDeg,
    mirrorX,
    mirrorY,
    left: 'left',
    right: 'right',
    vertical: 'center',
  });

  return (
    <group raycast={NO_RAYCAST}>
      <mesh position={[bodyX, bodyY, 0.001]} raycast={NO_RAYCAST}>
        <planeGeometry args={[edgeMarkerW, edgeMarkerH]} />
        <meshBasicMaterial color={lineColor} transparent opacity={isBus ? 0.52 : 0.32} depthWrite={false} />
      </mesh>

      {isBus ? (
        <>
          <Line
            points={[
              [pinX + perpX, pinY + perpY, 0.001],
              [bodyX + perpX, bodyY + perpY, 0.001],
            ]}
            color={lineColor}
            lineWidth={stroke.primaryWidth}
            transparent
            opacity={stroke.primaryOpacity}
            raycast={NO_RAYCAST}
          />
          <Line
            points={[
              [pinX - perpX, pinY - perpY, 0.001],
              [bodyX - perpX, bodyY - perpY, 0.001],
            ]}
            color={lineColor}
            lineWidth={stroke.secondaryWidth ?? stroke.primaryWidth}
            transparent
            opacity={stroke.secondaryOpacity ?? stroke.primaryOpacity}
            raycast={NO_RAYCAST}
          />
        </>
      ) : (
        <Line
          points={[
            [pinX, pinY, 0.001],
            [bodyX, bodyY, 0.001],
          ]}
          color={lineColor}
          lineWidth={stroke.primaryWidth}
          transparent
          opacity={stroke.primaryOpacity}
          raycast={NO_RAYCAST}
        />
      )}

      <mesh position={[pinX, pinY, 0.001]} raycast={NO_RAYCAST}>
        <circleGeometry args={[dotRadius * 1.86, 16]} />
        <meshBasicMaterial
          color={lineColor}
          transparent
          opacity={isHighlighted ? 0.27 : 0.16}
          depthWrite={false}
        />
      </mesh>

      {isBus ? (
        <>
          <mesh position={[pinX, pinY, 0.002]} raycast={NO_RAYCAST}>
            <circleGeometry args={[dotRadius, 16]} />
            <meshBasicMaterial color={lineColor} />
          </mesh>
          <mesh position={[pinX, pinY, 0.003]} raycast={NO_RAYCAST}>
            <circleGeometry args={[dotRadius * 0.56, 16]} />
            <meshBasicMaterial color={theme.bgPrimary} />
          </mesh>
          <mesh position={[pinX, pinY, 0.004]} raycast={NO_RAYCAST}>
            <circleGeometry args={[dotRadius * 0.2, 12]} />
            <meshBasicMaterial color={lineColor} />
          </mesh>
        </>
      ) : (
        <mesh position={[pinX, pinY, 0.002]} raycast={NO_RAYCAST}>
          <circleGeometry args={[dotRadius, 16]} />
          <meshBasicMaterial color={lineColor} />
        </mesh>
      )}

      <group position={[nameX, nameY, 0.002]} rotation={[0, 0, textRotationZ]} scale={[textScaleX, textScaleY, 1]}>
        <Text
          fontSize={isBus ? 0.93 : 0.88}
          color={isHighlighted ? theme.textPrimary : theme.textSecondary}
          anchorX={effectiveNameAnchorX}
          anchorY="middle"
          letterSpacing={isBus ? 0.02 : 0.015}
          maxWidth={10}
          font={undefined}
          raycast={NO_RAYCAST}
        >
          {pin.name}
        </Text>
      </group>
    </group>
  );
});
