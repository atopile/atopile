import { useState, useCallback } from 'react';
import {
  Save,
  Play,
  Plus,
  Bot,
  Clock,
  GitBranch,
  FolderOpen,
  History,
  Timer,
} from 'lucide-react';
import { useEditor, useDispatch, useUIState, useLoading } from '@/hooks';
import type { PipelineNode, AgentNodeData, TriggerNodeData, ConditionNodeData, WaitNodeData } from '@/logic/api/types';

interface PipelineToolbarProps {
  onOpenPipelineList?: () => void;
  onToggleSessions?: () => void;
  showSessions?: boolean;
  isMobile?: boolean;
}

export function PipelineToolbar({ onOpenPipelineList, onToggleSessions, showSessions, isMobile }: PipelineToolbarProps) {
  const dispatch = useDispatch();
  const editor = useEditor();
  const state = useUIState();
  const loading = useLoading('pipelines');

  const [saving, setSaving] = useState(false);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await dispatch({ type: 'editor.save' });
    } finally {
      setSaving(false);
    }
  }, [dispatch]);

  const handleRun = useCallback(async () => {
    if (state.selectedPipelineId) {
      await dispatch({ type: 'pipelines.run', payload: { pipelineId: state.selectedPipelineId } });
    }
  }, [dispatch, state.selectedPipelineId]);

  const handleReset = useCallback(() => {
    dispatch({ type: 'editor.reset' });
  }, [dispatch]);

  const addNode = useCallback((type: PipelineNode['type']) => {
    const basePosition = { x: 100 + editor.nodes.length * 50, y: 100 + editor.nodes.length * 50 };

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
      case 'wait':
        data = {
          duration_seconds: 60,
        } as WaitNodeData;
        break;
      case 'condition':
        data = {
          count_limit: undefined,
          time_limit_seconds: undefined,
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

    dispatch({
      type: 'editor.setNodes',
      payload: { nodes: [...editor.nodes, newNode] },
    });
  }, [dispatch, editor.nodes]);

  const handleSetName = useCallback((name: string) => {
    dispatch({ type: 'editor.setName', payload: { name } });
  }, [dispatch]);

  // Mobile layout - simplified toolbar
  if (isMobile) {
    return (
      <div className="flex items-center justify-between p-2 bg-gray-800 border-b border-gray-700 gap-2">
        {/* Left: Name and save */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <input
            type="text"
            className="input input-sm flex-1 min-w-0"
            value={editor.name}
            onChange={(e) => handleSetName(e.target.value)}
            placeholder="Pipeline name"
          />
          <button
            className="btn btn-primary btn-sm flex-shrink-0"
            onClick={handleSave}
            disabled={saving || !editor.name.trim()}
          >
            <Save className="w-4 h-4" />
          </button>
        </div>

        {/* Right: Add nodes dropdown + Run */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {/* Compact add buttons */}
          <button
            className="btn btn-secondary btn-sm touch-target"
            onClick={() => addNode('trigger')}
            title="Add Trigger"
          >
            <Clock className="w-4 h-4 text-blue-400" />
          </button>
          <button
            className="btn btn-secondary btn-sm touch-target"
            onClick={() => addNode('agent')}
            title="Add Agent"
          >
            <Bot className="w-4 h-4 text-green-400" />
          </button>
          <button
            className="btn btn-secondary btn-sm touch-target"
            onClick={() => addNode('wait')}
            title="Add Wait"
          >
            <Timer className="w-4 h-4 text-yellow-400" />
          </button>
          <button
            className="btn btn-secondary btn-sm touch-target"
            onClick={() => addNode('condition')}
            title="Add Condition"
          >
            <GitBranch className="w-4 h-4 text-cyan-400" />
          </button>
          {state.selectedPipelineId && (
            <button
              className="btn btn-success btn-sm touch-target"
              onClick={handleRun}
              disabled={loading || !state.selectedPipelineId}
              title="Run"
            >
              <Play className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    );
  }

  // Desktop layout
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
          value={editor.name}
          onChange={(e) => handleSetName(e.target.value)}
          placeholder="Pipeline name"
        />

        <button
          className="btn btn-primary btn-sm"
          onClick={handleSave}
          disabled={saving || !editor.name.trim()}
        >
          <Save className="w-4 h-4 mr-1" />
          {saving ? 'Saving...' : 'Save'}
        </button>

        {editor.hasUnsavedChanges && (
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
          onClick={() => addNode('wait')}
          title="Add Wait"
        >
          <Timer className="w-4 h-4 text-yellow-400" />
        </button>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => addNode('condition')}
          title="Add Condition"
        >
          <GitBranch className="w-4 h-4 text-cyan-400" />
        </button>
      </div>

      {/* Right: Run and sessions */}
      <div className="flex items-center gap-2">
        {state.selectedPipelineId && (
          <button
            className="btn btn-success btn-sm"
            onClick={handleRun}
            disabled={loading || !state.selectedPipelineId}
            title="Start a new session"
          >
            <Play className="w-4 h-4 mr-1" />
            Run
          </button>
        )}

        {state.selectedPipelineId && onToggleSessions && (
          <button
            className={`btn btn-sm ${showSessions ? 'btn-primary' : 'btn-secondary'}`}
            onClick={onToggleSessions}
            title="Toggle sessions panel"
          >
            <History className="w-4 h-4" />
          </button>
        )}

        <button
          className="btn btn-secondary btn-sm"
          onClick={handleReset}
          title="New pipeline"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export default PipelineToolbar;
