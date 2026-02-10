/**
 * Shared visual policy for interface endpoints and stubs.
 *
 * Keeps module interface pins and sheet ports aligned so bus/single wiring
 * semantics are rendered consistently across the viewer.
 */

export const INTERFACE_BUS_STUB_OFFSET = 0.13;
export const INTERFACE_SINGLE_DOT_RADIUS = 0.17;
export const INTERFACE_BUS_DOT_RADIUS = 0.19;
export const INTERFACE_SINGLE_NAME_INSET = 0.82;
export const INTERFACE_BUS_NAME_INSET = 1.02;

export interface InterfaceStrokeStyle {
  primaryWidth: number;
  primaryOpacity: number;
  secondaryWidth?: number;
  secondaryOpacity?: number;
}

export function isBusInterface(signals?: readonly string[]): boolean {
  return (signals?.length ?? 0) > 1;
}

export function getInterfaceDotRadius(signals?: readonly string[]): number {
  return isBusInterface(signals)
    ? INTERFACE_BUS_DOT_RADIUS
    : INTERFACE_SINGLE_DOT_RADIUS;
}

export function getInterfaceNameInset(signals?: readonly string[]): number {
  return isBusInterface(signals)
    ? INTERFACE_BUS_NAME_INSET
    : INTERFACE_SINGLE_NAME_INSET;
}

export function getInterfaceParallelOffset(
  fromX: number,
  fromY: number,
  toX: number,
  toY: number,
  offset = INTERFACE_BUS_STUB_OFFSET,
): { x: number; y: number } {
  const dx = toX - fromX;
  const dy = toY - fromY;
  const length = Math.hypot(dx, dy);
  if (length <= 1e-6) return { x: 0, y: 0 };
  return {
    x: (-dy / length) * offset,
    y: (dx / length) * offset,
  };
}

export function getInterfaceStrokeStyle(
  signals: readonly string[] | undefined,
  highlighted: boolean,
): InterfaceStrokeStyle {
  if (isBusInterface(signals)) {
    return highlighted
      ? {
          primaryWidth: 2.9,
          primaryOpacity: 0.98,
          secondaryWidth: 2.5,
          secondaryOpacity: 0.92,
        }
      : {
          primaryWidth: 2.3,
          primaryOpacity: 0.82,
          secondaryWidth: 2.0,
          secondaryOpacity: 0.72,
        };
  }

  return highlighted
    ? { primaryWidth: 2.3, primaryOpacity: 0.98 }
    : { primaryWidth: 1.7, primaryOpacity: 0.8 };
}
