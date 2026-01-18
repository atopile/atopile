import { useEffect, useState } from 'react';
import { Plus, Trash2, ChevronRight, Play, Square, CheckSquare, Square as SquareIcon } from 'lucide-react';
import { usePipelineStore } from '@/stores';
import { PipelineEditor, PipelineToolbar } from '@/pipeline';
import { StatusBadge } from '@/components';

export function Pipelines() {
  const {
    pipelines,
    selectedPipelineId,
    fetchPipelines,
    selectPipeline,
    deletePipeline,
    runPipeline,
    stopPipeline,
    resetEditor,
  } = usePipelineStore();

  const [showList, setShowList] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    fetchPipelines();
  }, [fetchPipelines]);

  const sortedPipelines = Array.from(pipelines.values()).sort((a, b) => {
    // Running pipelines first
    if (a.status === 'running' && b.status !== 'running') return -1;
    if (a.status !== 'running' && b.status === 'running') return 1;
    // Then by updated_at descending
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });

  const handleSelectPipeline = (id: string) => {
    selectPipeline(id);
    setShowList(false);
  };

  const handleNewPipeline = () => {
    resetEditor();
    setShowList(false);
  };

  const handleDeletePipeline = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this pipeline?')) {
      await deletePipeline(id);
      selectedIds.delete(id);
      setSelectedIds(new Set(selectedIds));
    }
  };

  const toggleSelection = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === sortedPipelines.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(sortedPipelines.map(p => p.id)));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Are you sure you want to delete ${selectedIds.size} pipeline(s)?`)) return;

    setIsProcessing(true);
    try {
      for (const id of selectedIds) {
        await deletePipeline(id);
      }
      setSelectedIds(new Set());
    } finally {
      setIsProcessing(false);
    }
  };

  const handleBulkRun = async () => {
    if (selectedIds.size === 0) return;

    setIsProcessing(true);
    try {
      for (const id of selectedIds) {
        const pipeline = pipelines.get(id);
        if (pipeline && pipeline.status !== 'running') {
          await runPipeline(id);
        }
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleBulkStop = async () => {
    if (selectedIds.size === 0) return;

    setIsProcessing(true);
    try {
      for (const id of selectedIds) {
        const pipeline = pipelines.get(id);
        if (pipeline && (pipeline.status === 'running' || pipeline.status === 'paused')) {
          await stopPipeline(id);
        }
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const hasSelection = selectedIds.size > 0;
  const allSelected = selectedIds.size === sortedPipelines.length && sortedPipelines.length > 0;

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <PipelineToolbar onOpenPipelineList={() => setShowList(true)} />

      <div className="flex flex-1 overflow-hidden">
        {/* Pipeline list sidebar */}
        {showList && (
          <div className="w-80 border-r border-gray-700 flex flex-col">
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
                  className="p-1 hover:bg-gray-700 rounded"
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
                      className="btn btn-sm btn-secondary flex items-center gap-1"
                      onClick={handleBulkStop}
                      disabled={isProcessing}
                      title="Stop selected"
                    >
                      <Square className="w-3 h-3" />
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
                    className={`card p-3 cursor-pointer transition-all ${
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
                        className="p-0.5 hover:bg-gray-700 rounded flex-shrink-0"
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
                      <StatusBadge status={pipeline.status} size="sm" />
                    </div>

                    <div className="flex items-center justify-between text-xs text-gray-500 pl-6">
                      <span>{pipeline.nodes.length} nodes</span>
                      <div className="flex items-center gap-1">
                        <button
                          className="p-1 hover:bg-gray-700 rounded"
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
        )}

        {/* Editor */}
        <div className="flex-1">
          <PipelineEditor />
        </div>
      </div>
    </div>
  );
}

export default Pipelines;
