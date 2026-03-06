import { useEffect, useRef } from 'react';
import { Editor } from '@layout-viewer/editor';
import { useInteractiveBomStore } from './useInteractiveBomStore';
import { API_URL } from '../../api/config';

// Derive layout server base URL from the standard API URL
// e.g. "http://127.0.0.1:12345/api" → "http://127.0.0.1:12345"
const LAYOUT_BASE_URL = API_URL.replace(/\/api$/, '');
const LAYOUT_API_PREFIX = '/api/layout';
const LAYOUT_WS_PATH = '/ws/layout';

export function LayoutViewerWrapper() {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const editorRef = useRef<Editor | null>(null);

  const setRenderModel = useInteractiveBomStore((s) => s.setRenderModel);
  const setSelectedGroups = useInteractiveBomStore((s) => s.setSelectedGroups);
  const selectedGroupIds = useInteractiveBomStore((s) => s.selectedGroupIds);
  const bomGroups = useInteractiveBomStore((s) => s.bomGroups);
  const fpIndexToGroupId = useInteractiveBomStore((s) => s.fpIndexToGroupId);

  // Initialize editor on mount
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const editor = new Editor(canvas, LAYOUT_BASE_URL, LAYOUT_API_PREFIX, LAYOUT_WS_PATH, container, {
      readOnly: true,
    });

    editor.setOnModelLoad((model) => {
      setRenderModel(model);
    });

    editor.setOnSelectionChange((indices) => {
      const state = useInteractiveBomStore.getState();
      if (indices.length === 0) {
        if (state.selectedGroupIds.size > 0) setSelectedGroups(new Set());
        return;
      }
      // Find all BomGroups that contain any of the selected indices
      const groupIds = new Set<string>();
      for (const idx of indices) {
        const groupId = state.fpIndexToGroupId.get(idx);
        if (groupId) groupIds.add(groupId);
      }
      // Skip update if the set of selected groups hasn't changed
      const prev = state.selectedGroupIds;
      if (groupIds.size === prev.size && [...groupIds].every((id) => prev.has(id))) return;
      setSelectedGroups(groupIds);
    });

    editor.init();
    editorRef.current = editor;

    return () => {
      editorRef.current?.dispose();
      editorRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync BOM selection → viewer
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;

    if (selectedGroupIds.size === 0) {
      editor.selectFootprintsByIndices([]);
      return;
    }

    const allIndices: number[] = [];
    for (const groupId of selectedGroupIds) {
      const group = bomGroups.find((g) => g.id === groupId);
      if (group) allIndices.push(...group.footprintIndices);
    }
    editor.selectFootprintsByIndices(allIndices);
  }, [selectedGroupIds, bomGroups, fpIndexToGroupId]);

  return (
    <div className="ibom-viewer" ref={containerRef}>
      <canvas ref={canvasRef} className="ibom-canvas" />
    </div>
  );
}
