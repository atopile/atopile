import { useRef, useEffect, useMemo } from 'react'
import type { FootprintPadGeometry, PinInfo } from '../types/build'
import { Editor } from '@layout-editor/editor'
import { getSignalColors } from '@layout-editor/colors'
import { API_URL } from '../api/config'
import { sendActionWithResponse } from '../api/websocket'

interface FootprintViewerCanvasProps {
  projectRoot: string
  targetName: string
  pads: FootprintPadGeometry[]
  pins: PinInfo[]
  selectedPinNumber: string | null
  onPadClick: (padNumber: string) => void
}

interface PadStyles {
  colorOverrides: Map<string, ReturnType<typeof getSignalColors>['pad']>
  outlinePads: Set<string>
}

/** Build color overrides (by signal type) and outline set (unconnected) */
function buildPadStyles(pins: PinInfo[]): PadStyles {
  const colorOverrides = new Map<string, ReturnType<typeof getSignalColors>['pad']>()
  const outlinePads = new Set<string>()

  for (const pin of pins) {
    if (!pin.pin_number) continue

    colorOverrides.set(pin.pin_number, getSignalColors(pin.signal_type).pad)

    if (!pin.is_connected) {
      outlinePads.add(pin.pin_number)
    }
  }

  return { colorOverrides, outlinePads }
}

export function FootprintViewerCanvas({
  projectRoot, targetName, pads, pins, selectedPinNumber, onPadClick,
}: FootprintViewerCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const editorRef = useRef<Editor | null>(null)

  const padStyles = useMemo(
    () => buildPadStyles(pins),
    [pins],
  )

  // Initialize editor on mount
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const editor = new Editor(canvas, API_URL, '/api/layout', '/ws/layout')
    const initialPadNumbers = new Set(pads.map(p => p.pad_number).filter(Boolean))
    editor.setReadOnly(true)
    editor.setFilteredFootprintPadNames(initialPadNumbers, true)
    editor.setPadColorOverrides(padStyles.colorOverrides)
    editor.setOutlinePads(padStyles.outlinePads)
    editor.setOnPadClick(onPadClick)
    void editor.init()
    editorRef.current = editor
    return () => editor.dispose()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Update footprint filter when component pad set changes
  useEffect(() => {
    const padNumbers = new Set(pads.map(p => p.pad_number).filter(Boolean))
    editorRef.current?.setFilteredFootprintPadNames(padNumbers, true)
  }, [pads])

  // Ensure the selected target's layout is loaded in backend layout_service
  useEffect(() => {
    if (!projectRoot || !targetName) return
    let cancelled = false
    const loadViaAction = async () => {
      for (let attempt = 0; attempt < 6; attempt++) {
        if (cancelled) return
        try {
          await sendActionWithResponse(
            'loadLayout',
            { projectId: projectRoot, targetName },
            { timeoutMs: 10000 }
          )
          return
        } catch (err) {
          if (cancelled) return
          if (attempt === 5) {
            console.warn('[Pinout] Failed to load layout target for 2D viewer:', err)
            return
          }
          await new Promise(resolve => setTimeout(resolve, 300))
        }
      }
    }
    void loadViaAction()
    return () => { cancelled = true }
  }, [projectRoot, targetName])

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
