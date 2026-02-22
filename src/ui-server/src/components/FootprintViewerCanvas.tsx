import { useRef, useEffect } from 'react'
import type { PinInfo } from '../types/build'
import { Editor } from '@layout-editor/editor'
import { getSignalColors } from '@layout-editor/colors'
import { API_URL } from '../api/config'
import { sendActionWithResponse } from '../api/websocket'

interface FootprintViewerCanvasProps {
  projectRoot: string
  targetName: string
  footprintUuid: string | null
  pins: PinInfo[]
  selectedPinNumber: string | null
  onPadClick: (padNumber: string) => void
}

export function FootprintViewerCanvas({
  projectRoot, targetName, footprintUuid, pins, selectedPinNumber, onPadClick,
}: FootprintViewerCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const editorRef = useRef<Editor | null>(null)
  const loadRequestSeq = useRef(0)

  // Initialize editor on mount
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const editor = new Editor(canvas, API_URL, '/api/layout', '/ws/layout')
    editor.setReadOnly(true)
    editorRef.current = editor
    return () => {
      editorRef.current = null
    }
  }, [])

  // Keep editor model in sync with selected project/target/footprint.
  useEffect(() => {
    const editor = editorRef.current
    if (!editor) return

    loadRequestSeq.current += 1
    const requestSeq = loadRequestSeq.current

    void (async () => {
      try {
        await sendActionWithResponse(
          'loadLayout',
          { projectId: projectRoot, targetName },
          { timeoutMs: 10000 }
        )
        if (requestSeq !== loadRequestSeq.current) return
        await editor.loadRenderModel(footprintUuid, true)
      } catch (error) {
        if (requestSeq !== loadRequestSeq.current) return
        console.warn('Failed to update footprint viewer model', error)
      }
    })()
  }, [projectRoot, targetName, footprintUuid])

  // Update pad styles when pins change
  useEffect(() => {
    const editor = editorRef.current
    if (!editor) return

    const colorOverrides = new Map<string, ReturnType<typeof getSignalColors>['pad']>()
    const outlinePads = new Set<string>()

    for (const pin of pins) {
      if (!pin.pin_number) continue
      colorOverrides.set(pin.pin_number, getSignalColors(pin.signal_type).pad)
      if (!pin.is_connected) outlinePads.add(pin.pin_number)
    }

    editor.setPadColorOverrides(colorOverrides)
    editor.setOutlinePads(outlinePads)
  }, [pins])

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
