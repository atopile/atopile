import { useEffect, useState, useMemo, useCallback } from 'react';
import { Plus, Trash2, ChevronRight, Play, CheckSquare, Square as SquareIcon, History, ArrowLeft } from 'lucide-react';
import { usePipelines, useUIState, useDispatch, useMobile } from '@/hooks';
import { PipelineEditor, PipelineToolbar } from '@/pipeline';
import { PipelineSessionsPanel } from '@/components';

type MobileView = 'list' | 'editor' | 'sessions';

export function Pipelines() {
  const dispatch = useDispatch();
  const pipelines = usePipelines();
  const state = useUIState();
  const selectedPipelineId = state.selectedPipelineId;
  const isMobile = useMobile();

  const [showList, setShowList] = useState(true);
  const [showSessions, setShowSessions] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isProcessing, setIsProcessing] = useState(false);
  const [mobileView, setMobileView] = useState<MobileView>('list');

  // Load pipelines and sessions on mount
  useEffect(() => {
    dispatch({ type: 'pipelines.refresh' });
  }, [dispatch]);

  // Fetch sessions for all pipelines to compute display status
  useEffect(() => {
    pipelines.forEach((pipeline) => {
      dispatch({ type: 'sessions.fetch', payload: { pipelineId: pipeline.id } });
    });
  }, [pipelines, dispatch]);

  const getRunningSessionCount = useCallback((pipelineId: string) => {
    const sessions = state.pipelineSessions.get(pipelineId) || [];
    return sessions.filter(s => s.status === 'running').length;
  }, [state.pipelineSessions]);

  const sortedPipelines = useMemo(() => {
    return [...pipelines].sort((a, b) => {
      // Running pipelines first (based on running session count)
      const aRunning = getRunningSessionCount(a.id);
      const bRunning = getRunningSessionCount(b.id);
      if (aRunning > 0 && bRunning === 0) return -1;
      if (aRunning === 0 && bRunning > 0) return 1;
      // Then by updated_at descending
      return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
    });
  }, [pipelines, getRunningSessionCount]);

  const handleSelectPipeline = useCallback((id: string) => {
    dispatch({ type: 'pipelines.select', payload: { pipelineId: id } });
    setShowList(false);
    if (isMobile) {
      setMobileView('editor');
    }
  }, [dispatch, isMobile]);

  const handleNewPipeline = useCallback(() => {
    dispatch({ type: 'editor.reset' });
    setShowList(false);
    if (isMobile) {
      setMobileView('editor');
    }
  }, [dispatch, isMobile]);

  const handleMobileBack = useCallback(() => {
    if (mobileView === 'sessions') {
      setMobileView('editor');
    } else {
      setMobileView('list');
    }
  }, [mobileView]);

  const handleMobileShowSessions = useCallback(() => {
    setMobileView('sessions');
  }, []);

  const handleDeletePipeline = useCallback(async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this pipeline?')) {
      await dispatch({ type: 'pipelines.delete', payload: { pipelineId: id } });
      selectedIds.delete(id);
      setSelectedIds(new Set(selectedIds));
    }
  }, [dispatch, selectedIds]);

  const toggleSelection = useCallback((id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  }, [selectedIds]);

  const toggleSelectAll = useCallback(() => {
    if (selectedIds.size === sortedPipelines.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(sortedPipelines.map(p => p.id)));
    }
  }, [selectedIds.size, sortedPipelines]);

  const handleBulkDelete = useCallback(async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Are you sure you want to delete ${selectedIds.size} pipeline(s)?`)) return;

    setIsProcessing(true);
    try {
      for (const id of selectedIds) {
        await dispatch({ type: 'pipelines.delete', payload: { pipelineId: id } });
      }
      setSelectedIds(new Set());
    } finally {
      setIsProcessing(false);
    }
  }, [dispatch, selectedIds]);

  const handleBulkRun = useCallback(async () => {
    if (selectedIds.size === 0) return;

    setIsProcessing(true);
    try {
      for (const id of selectedIds) {
        await dispatch({ type: 'pipelines.run', payload: { pipelineId: id } });
      }
    } finally {
      setIsProcessing(false);
    }
  }, [dispatch, selectedIds]);

  const hasSelection = selectedIds.size > 0;
  const allSelected = selectedIds.size === sortedPipelines.length && sortedPipelines.length > 0;

  // Mobile pipeline list component (reused in both layouts)
  const renderPipelineList = () => (
    <div className={`flex flex-col ${isMobile ? 'h-full' : 'w-80 border-r border-gray-700'}`}>
      <div className="flex items-center justify-between p-3 border-b border-gray-700">
        <h2 className="font-semibold">Pipelines</h2>
        <button
          className="btn btn-primary btn-sm"
          onClick={handleNewPipeline}
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* Bulk actions bar */}
      {sortedPipelines.length > 0 && (
        <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-700 bg-gray-800/50">
          <button
            className="p-1 hover:bg-gray-700 rounded touch-target"
            onClick={toggleSelectAll}
            title={allSelected ? 'Deselect all' : 'Select all'}
          >
            {allSelected ? (
              <CheckSquare className="w-4 h-4 text-blue-400" />
            ) : (
              <SquareIcon className="w-4 h-4 text-gray-500" />
            )}
          </button>
          {hasSelection && (
            <>
              <span className="text-xs text-gray-400">{selectedIds.size} selected</span>
              <div className="flex-1" />
              <button
                className="btn btn-sm btn-secondary flex items-center gap-1"
                onClick={handleBulkRun}
                disabled={isProcessing}
                title="Run selected"
              >
                <Play className="w-3 h-3" />
              </button>
              <button
                className="btn btn-sm btn-danger flex items-center gap-1"
                onClick={handleBulkDelete}
                disabled={isProcessing}
                title="Delete selected"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {sortedPipelines.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <p>No pipelines yet</p>
            <button
              className="btn btn-primary btn-sm mt-4"
              onClick={handleNewPipeline}
            >
              Create your first pipeline
            </button>
          </div>
        ) : (
          sortedPipelines.map((pipeline) => (
            <div
              key={pipeline.id}
              className={`card p-3 cursor-pointer transition-all touch-target ${
                selectedPipelineId === pipeline.id
                  ? 'ring-2 ring-blue-500'
                  : selectedIds.has(pipeline.id)
                  ? 'ring-1 ring-blue-400/50 bg-blue-900/10'
                  : 'hover:border-gray-600'
              }`}
              onClick={() => handleSelectPipeline(pipeline.id)}
            >
              <div className="flex items-center gap-2 mb-2">
                <button
                  className="p-0.5 hover:bg-gray-700 rounded flex-shrink-0 touch-target"
                  onClick={(e) => toggleSelection(pipeline.id, e)}
                >
                  {selectedIds.has(pipeline.id) ? (
                    <CheckSquare className="w-4 h-4 text-blue-400" />
                  ) : (
                    <SquareIcon className="w-4 h-4 text-gray-500" />
                  )}
                </button>
                <span className="font-medium text-sm truncate flex-1">
                  {pipeline.name}
                </span>
                {(() => {
                  const runningCount = getRunningSessionCount(pipeline.id);
                  return runningCount > 0 ? (
                    <span className="px-1.5 py-0.5 text-xs rounded bg-green-900/50 text-green-300 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                      {runningCount} running
                    </span>
                  ) : null;
                })()}
              </div>

              <div className="flex items-center justify-between text-xs text-gray-500 pl-6">
                <span>{pipeline.nodeCount} nodes</span>
                <div className="flex items-center gap-1">
                  <button
                    className="p-1 hover:bg-gray-700 rounded touch-target"
                    onClick={(e) => {
                      e.stopPropagation();
                      dispatch({ type: 'pipelines.select', payload: { pipelineId: pipeline.id } });
                      if (isMobile) {
                        setMobileView('sessions');
                      } else {
                        setShowSessions(true);
                      }
                    }}
                    title="View sessions"
                  >
                    <History className="w-3.5 h-3.5 hover:text-blue-400" />
                  </button>
                  <button
                    className="p-1 hover:bg-gray-700 rounded touch-target"
                    onClick={(e) => handleDeletePipeline(pipeline.id, e)}
                    title="Delete"
                  >
                    <Trash2 className="w-3.5 h-3.5 hover:text-red-400" />
                  </button>
                  <ChevronRight className="w-4 h-4" />
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );

  // Mobile layout
  if (isMobile) {
    return (
      <div className="flex flex-col h-full">
        {mobileView === 'list' ? (
          renderPipelineList()
        ) : mobileView === 'editor' ? (
          <>
            {/* Mobile back header for editor */}
            <div className="mobile-back-header">
              <button
                className="mobile-back-button"
                onClick={handleMobileBack}
              >
                <ArrowLeft className="w-5 h-5" />
                <span>Pipelines</span>
              </button>
              <div className="flex items-center gap-2">
                <button
                  className="btn btn-sm btn-secondary"
                  onClick={handleMobileShowSessions}
                >
                  <History className="w-4 h-4" />
                </button>
              </div>
            </div>
            {/* Mobile toolbar - simplified */}
            <PipelineToolbar
              onOpenPipelineList={() => setMobileView('list')}
              onToggleSessions={handleMobileShowSessions}
              showSessions={false}
              isMobile={true}
            />
            <div className="flex-1">
              <PipelineEditor />
            </div>
          </>
        ) : (
          <>
            {/* Mobile back header for sessions */}
            <div className="mobile-back-header">
              <button
                className="mobile-back-button"
                onClick={handleMobileBack}
              >
                <ArrowLeft className="w-5 h-5" />
                <span>Editor</span>
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              {selectedPipelineId ? (
                <PipelineSessionsPanel
                  pipelineId={selectedPipelineId}
                  onClose={() => setMobileView('editor')}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-gray-500 text-sm">
                  Select a pipeline to view sessions
                </div>
              )}
            </div>
          </>
        )}
      </div>
    );
  }

  // Desktop layout
  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <PipelineToolbar
        onOpenPipelineList={() => setShowList(true)}
        onToggleSessions={() => setShowSessions(!showSessions)}
        showSessions={showSessions}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Pipeline list sidebar */}
        {showList && renderPipelineList()}

        {/* Editor */}
        <div className="flex-1">
          <PipelineEditor />
        </div>

        {/* Sessions panel */}
        {showSessions && (
          <div className="w-80 border-l border-gray-700 bg-gray-900">
            {selectedPipelineId ? (
              <PipelineSessionsPanel
                pipelineId={selectedPipelineId}
                onClose={() => setShowSessions(false)}
              />
            ) : (
              <div className="h-full flex flex-col">
                <div className="flex items-center justify-between p-3 border-b border-gray-700">
                  <h3 className="font-semibold text-sm">Pipeline Sessions</h3>
                  <button
                    className="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-gray-200"
                    onClick={() => setShowSessions(false)}
                  >
                    ×
                  </button>
                </div>
                <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
                  Select a pipeline to view sessions
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Pipelines;
