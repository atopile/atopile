import { useState } from 'react';
import {
  Save,
  Play,
  Pause,
  Square,
  Plus,
  Bot,
  Clock,
  Repeat,
  GitBranch,
  FolderOpen,
} from 'lucide-react';
import { usePipelineStore } from '@/stores';
import type { PipelineNode, AgentNodeData, TriggerNodeData, LoopNodeData, ConditionNodeData } from '@/api/types';

interface PipelineToolbarProps {
  onOpenPipelineList?: () => void;
}

export function PipelineToolbar({ onOpenPipelineList }: PipelineToolbarProps) {
  const {
    selectedPipelineId,
    editorName,
    editorNodes,
    hasUnsavedChanges,
    setEditorName,
    setEditorNodes,
    saveEditorPipeline,
    runPipeline,
    pausePipeline,
    stopPipeline,
    resetEditor,
    getSelectedPipeline,
    loading,
  } = usePipelineStore();

  const [saving, setSaving] = useState(false);

  const selectedPipeline = getSelectedPipeline();
  const isRunning = selectedPipeline?.status === 'running';
  const isPaused = selectedPipeline?.status === 'paused';

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveEditorPipeline();
    } finally {
      setSaving(false);
    }
  };

  const handleRun = async () => {
    if (selectedPipelineId) {
      await runPipeline(selectedPipelineId);
    }
  };

  const handlePause = async () => {
    if (selectedPipelineId) {
      await pausePipeline(selectedPipelineId);
    }
  };

  const handleStop = async () => {
    if (selectedPipelineId) {
      await stopPipeline(selectedPipelineId);
    }
  };

  const addNode = (type: PipelineNode['type']) => {
    const basePosition = { x: 100 + editorNodes.length * 50, y: 100 + editorNodes.length * 50 };

    let data: PipelineNode['data'];
    switch (type) {
      case 'agent':
        data = {
          name: 'New Agent',
          backend: 'claude-code',
          prompt: '',
        } as AgentNodeData;
        break;
      case 'trigger':
        data = {
          trigger_type: 'manual',
        } as TriggerNodeData;
        break;
      case 'loop':
        data = {
          duration_seconds: 3600,
          restart_on_complete: true,
          restart_on_fail: false,
        } as LoopNodeData;
        break;
      case 'condition':
        data = {
          expression: '',
        } as ConditionNodeData;
        break;
      default:
        return;
    }

    const newNode: PipelineNode = {
      id: `${type}-${Date.now()}`,
      type,
      position: basePosition,
      data,
    };

    setEditorNodes([...editorNodes, newNode]);
  };

  return (
    <div className="flex items-center justify-between p-3 bg-gray-800 border-b border-gray-700">
      {/* Left: Pipeline info and save */}
      <div className="flex items-center gap-3">
        {onOpenPipelineList && (
          <button
            className="btn btn-secondary btn-sm"
            onClick={onOpenPipelineList}
            title="Open pipeline list"
          >
            <FolderOpen className="w-4 h-4" />
          </button>
        )}

        <input
          type="text"
          className="input input-sm w-48"
          value={editorName}
          onChange={(e) => setEditorName(e.target.value)}
          placeholder="Pipeline name"
        />

        <button
          className="btn btn-primary btn-sm"
          onClick={handleSave}
          disabled={saving || !editorName.trim()}
        >
          <Save className="w-4 h-4 mr-1" />
          {saving ? 'Saving...' : 'Save'}
        </button>

        {hasUnsavedChanges && (
          <span className="text-xs text-yellow-400">Unsaved changes</span>
        )}
      </div>

      {/* Center: Add nodes */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500 mr-2">Add:</span>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => addNode('trigger')}
          title="Add Trigger"
        >
          <Clock className="w-4 h-4 text-blue-400" />
        </button>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => addNode('agent')}
          title="Add Agent"
        >
          <Bot className="w-4 h-4 text-green-400" />
        </button>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => addNode('loop')}
          title="Add Loop"
        >
          <Repeat className="w-4 h-4 text-purple-400" />
        </button>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => addNode('condition')}
          title="Add Condition"
        >
          <GitBranch className="w-4 h-4 text-yellow-400" />
        </button>
      </div>

      {/* Right: Run controls */}
      <div className="flex items-center gap-2">
        {selectedPipelineId && (
          <>
            {!isRunning && !isPaused && (
              <button
                className="btn btn-success btn-sm"
                onClick={handleRun}
                disabled={loading || !selectedPipelineId}
              >
                <Play className="w-4 h-4 mr-1" />
                Run
              </button>
            )}

            {isRunning && (
              <>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={handlePause}
                  disabled={loading}
                >
                  <Pause className="w-4 h-4 mr-1" />
                  Pause
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={handleStop}
                  disabled={loading}
                >
                  <Square className="w-4 h-4 mr-1" />
                  Stop
                </button>
              </>
            )}

            {isPaused && (
              <>
                <button
                  className="btn btn-success btn-sm"
                  onClick={handleRun}
                  disabled={loading}
                >
                  <Play className="w-4 h-4 mr-1" />
                  Resume
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={handleStop}
                  disabled={loading}
                >
                  <Square className="w-4 h-4 mr-1" />
                  Stop
                </button>
              </>
            )}
          </>
        )}

        <button
          className="btn btn-secondary btn-sm"
          onClick={resetEditor}
          title="New pipeline"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export default PipelineToolbar;
