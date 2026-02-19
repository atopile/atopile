import { useRef, useEffect, useMemo } from 'react'
import type { FootprintPadGeometry, FootprintDrawing, PinInfo } from '../types/build'
import { Editor } from '@layout-editor/editor'
import type { RenderModel, PadModel, DrawingModel, FootprintModel } from '@layout-editor/types'
import type { Color } from '@layout-editor/colors'

interface FootprintViewerCanvasProps {
  pads: FootprintPadGeometry[]
  drawings: FootprintDrawing[]
  pins: PinInfo[]
  selectedPinNumber: string | null
  onPadClick: (padNumber: string) => void
}

/** Pad colors matching the signal type badge hues in PinoutPanel */
const SIGNAL_PAD_COLORS: Record<string, Color> = {
  digital: [0.30, 0.55, 0.85, 0.9],   // blue  (matches #264f78)
  analog:  [0.30, 0.60, 0.30, 0.9],   // green (matches #2d4a2d)
  power:   [0.80, 0.30, 0.30, 0.9],   // red   (matches #5c2020)
  ground:  [0.45, 0.45, 0.45, 0.9],   // gray  (matches #3c3c3c)
  nc:      [0.35, 0.35, 0.35, 0.7],   // dim   (matches #444)
}

function buildRenderModel(pads: FootprintPadGeometry[], drawings: FootprintDrawing[]): RenderModel {
  const fpPads: PadModel[] = pads.map(p => ({
    name: p.pad_number,
    at: { x: p.x, y: p.y, r: p.rotation },
    size: { w: p.width, h: p.height },
    shape: p.shape,
    type: p.pad_type,
    layers: p.layers,
    net: 0,
    roundrect_rratio: p.roundrect_ratio ?? null,
    drill: null,
  }))

  const fpDrawings: DrawingModel[] = drawings.map(d => ({
    type: d.type as DrawingModel['type'],
    layer: d.layer,
    width: d.width,
    start: d.start_x != null ? { x: d.start_x, y: d.start_y! } : undefined,
    end: d.end_x != null ? { x: d.end_x, y: d.end_y! } : undefined,
    mid: d.mid_x != null ? { x: d.mid_x, y: d.mid_y! } : undefined,
    center: d.center_x != null ? { x: d.center_x, y: d.center_y! } : undefined,
  }))

  const fp: FootprintModel = {
    uuid: null,
    name: '',
    reference: null,
    value: null,
    at: { x: 0, y: 0, r: 0 },
    layer: 'F.Cu',
    pads: fpPads,
    drawings: fpDrawings,
  }

  return {
    board: { edges: [], width: 0, height: 0, origin: { x: 0, y: 0 } },
    footprints: [fp],
    tracks: [],
    arcs: [],
    vias: [],
    zones: [],
    nets: [],
  }
}

interface PadStyles {
  colorOverrides: Map<string, Color>
  outlinePads: Set<string>
}

/** Build color overrides (by signal type) and outline set (unconnected) */
function buildPadStyles(pins: PinInfo[]): PadStyles {
  const colorOverrides = new Map<string, Color>()
  const outlinePads = new Set<string>()

  for (const pin of pins) {
    if (!pin.pin_number) continue

    const color = SIGNAL_PAD_COLORS[pin.signal_type]
    if (color) {
      colorOverrides.set(pin.pin_number, color)
    }

    if (pin.connected_to.length === 0) {
      outlinePads.add(pin.pin_number)
    }
  }

  return { colorOverrides, outlinePads }
}

export function FootprintViewerCanvas({
  pads, drawings, pins, selectedPinNumber, onPadClick,
}: FootprintViewerCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const editorRef = useRef<Editor | null>(null)

  const model = useMemo(
    () => buildRenderModel(pads, drawings),
    [pads, drawings],
  )

  const padStyles = useMemo(
    () => buildPadStyles(pins),
    [pins],
  )

  // Initialize editor on mount
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const editor = new Editor(canvas, '', '', '')
    editor.setReadOnly(true)
    editor.setModel(model, true)
    editor.setPadColorOverrides(padStyles.colorOverrides)
    editor.setOutlinePads(padStyles.outlinePads)
    editor.setOnPadClick(onPadClick)
    editorRef.current = editor
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Update model when pads/drawings change
  useEffect(() => {
    editorRef.current?.setModel(model, true)
  }, [model])

  // Update pad styles when pins change
  useEffect(() => {
    editorRef.current?.setPadColorOverrides(padStyles.colorOverrides)
    editorRef.current?.setOutlinePads(padStyles.outlinePads)
  }, [padStyles])

  // Update highlighted pads when selection changes
  useEffect(() => {
    const highlighted = new Set(selectedPinNumber ? [selectedPinNumber] : [])
    editorRef.current?.setHighlightedPads(highlighted)
  }, [selectedPinNumber])

  // Update pad click callback
  useEffect(() => {
    editorRef.current?.setOnPadClick(onPadClick)
  }, [onPadClick])

  return (
    <canvas
      ref={canvasRef}
      style={{
        width: '100%',
        height: '100%',
        display: 'block',
        borderRadius: 4,
        border: '1px solid var(--vscode-panel-border, #444)',
        background: '#1e1e1e',
      }}
    />
  )
}
