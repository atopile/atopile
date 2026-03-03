import { useEffect, useRef } from 'react';
import { Editor } from '@layout-viewer/editor';
import { useInteractiveBomStore } from './useInteractiveBomStore';

export function LayoutViewerWrapper() {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const editorRef = useRef<Editor | null>(null);

  const setRenderModel = useInteractiveBomStore((s) => s.setRenderModel);
  const setSelectedGroup = useInteractiveBomStore((s) => s.setSelectedGroup);
  const selectedGroupId = useInteractiveBomStore((s) => s.selectedGroupId);
  const bomGroups = useInteractiveBomStore((s) => s.bomGroups);
  const fpIndexToGroupId = useInteractiveBomStore((s) => s.fpIndexToGroupId);

  // Initialize editor on mount
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const baseUrl = (window as any).__LAYOUT_BASE_URL__ || window.location.origin;
    const apiPrefix = (window as any).__LAYOUT_API_PREFIX__ || '/api';
    const wsPath = (window as any).__LAYOUT_WS_PATH__ || '/ws';
    const editor = new Editor(canvas, baseUrl, apiPrefix, wsPath, {
      readOnly: true,
      container,
    });

    editor.onModelLoad = (model) => {
      setRenderModel(model);
    };

    editor.onSelectionChange = (indices) => {
      if (indices.length === 0) {
        setSelectedGroup(null);
        return;
      }
      // Find which BomGroup contains the first selected index
      const groupId = useInteractiveBomStore.getState().fpIndexToGroupId.get(indices[0]!);
      setSelectedGroup(groupId ?? null);
    };

    editor.init();
    editorRef.current = editor;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync BOM selection → viewer
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;

    if (!selectedGroupId) {
      editor.selectFootprintsByIndices([]);
      return;
    }

    const group = bomGroups.find((g) => g.id === selectedGroupId);
    if (group) {
      editor.selectFootprintsByIndices(group.footprintIndices);
    }
  }, [selectedGroupId, bomGroups, fpIndexToGroupId]);

  return (
    <div className="ibom-viewer" ref={containerRef}>
      <canvas ref={canvasRef} className="ibom-canvas" />
    </div>
  );
}
