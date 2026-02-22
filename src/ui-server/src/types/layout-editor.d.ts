/**
 * Type declarations for the layout editor modules.
 * Vite resolves these imports to the real layout editor source.
 */

declare module '@layout-editor/editor' {
  export class Editor {
    constructor(canvas: HTMLCanvasElement, baseUrl: string, apiPrefix?: string, wsPath?: string);
    loadRenderModel(footprintUuid?: string | null, fitToView?: boolean): Promise<void>;
    setReadOnly(readOnly: boolean): void;
    setPadColorOverrides(overrides: Map<string, import('@layout-editor/colors').Color>): void;
    setHighlightedPads(padNames: Set<string>): void;
    setOutlinePads(padNames: Set<string>): void;
    setOnPadClick(cb: ((padName: string) => void) | null): void;
  }
}

declare module '@layout-editor/colors' {
  export type Color = [number, number, number, number];
  export function getSignalColors(signalType: string | null | undefined): { pad: Color; badgeBg: string; badgeFg: string };
}
