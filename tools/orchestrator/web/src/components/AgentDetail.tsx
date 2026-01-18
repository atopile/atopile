import { useEffect, useState, useCallback } from 'react';
import { Square, Send, X, Clock, Cpu, Hash, Code, RotateCcw, Pencil, Check, History } from 'lucide-react';
import type { AgentViewModel } from '@/logic/viewmodels';
import { useDispatch, useAgentOutput, useLoading } from '@/hooks';
import { StatusBadge } from './StatusBadge';
import { OutputStream } from './OutputStream';

interface AgentDetailProps {
  agent: AgentViewModel;
  onClose?: () => void;
}

export function AgentDetail({ agent, onClose }: AgentDetailProps) {
  const dispatch = useDispatch();
  const output = useAgentOutput(agent.id);
  const loadingResume = useLoading(`resume-${agent.id}`);

  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [verbose, setVerbose] = useState(false);
  const [resumePrompt, setResumePrompt] = useState('');
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState(agent.name || '');

  const hasMultipleRuns = agent.runCount > 0;

  // Initial data fetch - only runs when agent.id changes
  useEffect(() => {
    // Set the current run number so new WebSocket chunks get tagged correctly
    dispatch({
      type: 'output.setRunNumber',
      payload: { agentId: agent.id, runNumber: agent.runCount },
    });

    // For agents with multiple runs, load full history to see all runs
    if (hasMultipleRuns) {
      dispatch({ type: 'output.fetchHistory', payload: { agentId: agent.id } });
    } else {
      // Single-run agent - fetch current output
      dispatch({
        type: 'output.fetch',
        payload: { agentId: agent.id, runNumber: agent.runCount },
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agent.id]);

  // WebSocket connection - separate effect for running state
  useEffect(() => {
    if (agent.isRunning) {
      dispatch({ type: 'output.connect', payload: { agentId: agent.id } });
    }

    return () => {
      dispatch({ type: 'output.disconnect', payload: { agentId: agent.id } });
    };
  }, [agent.id, agent.isRunning, dispatch]);

  const handleLoadHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      await dispatch({ type: 'output.fetchHistory', payload: { agentId: agent.id } });
    } finally {
      setLoadingHistory(false);
    }
  }, [dispatch, agent.id]);

  const handleSendInput = useCallback(async () => {
    if (!inputValue.trim() || !agent.isRunning) return;

    setSending(true);
    try {
      await dispatch({
        type: 'agents.sendInput',
        payload: { agentId: agent.id, input: inputValue },
      });
      setInputValue('');
    } finally {
      setSending(false);
    }
  }, [dispatch, agent.id, agent.isRunning, inputValue]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSendInput();
    }
  };

  const handleResumeKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleResume();
    }
  };

  const handleResume = useCallback(async () => {
    if (!resumePrompt.trim() || !agent.canResume) return;

    const promptText = resumePrompt.trim();
    setResumePrompt('');

    try {
      await dispatch({
        type: 'agents.resume',
        payload: { agentId: agent.id, prompt: promptText },
      });
    } catch (e) {
      // Error is handled in logic layer
    }
  }, [dispatch, agent.id, agent.canResume, resumePrompt]);

  const handleSaveName = useCallback(async () => {
    if (editedName.trim() !== (agent.name || '')) {
      try {
        await dispatch({
          type: 'agents.rename',
          payload: { agentId: agent.id, name: editedName.trim() },
        });
      } catch (e) {
        // Error is handled in logic layer
      }
    }
    setIsEditingName(false);
  }, [dispatch, agent.id, agent.name, editedName]);

  const handleNameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSaveName();
    } else if (e.key === 'Escape') {
      setEditedName(agent.name || '');
      setIsEditingName(false);
    }
  };

  const handleTerminate = useCallback(() => {
    dispatch({ type: 'agents.terminate', payload: { agentId: agent.id } });
  }, [dispatch, agent.id]);

  const formatDuration = () => {
    if (!agent.startedAt) return '—';

    const start = new Date(agent.startedAt).getTime();
    if (isNaN(start)) return '—';

    let end: number;
    if (agent.finishedAt) {
      end = new Date(agent.finishedAt).getTime();
      if (isNaN(end)) return '—';
    } else if (agent.isRunning) {
      end = Date.now();
    } else {
      return '—';
    }

    const seconds = Math.floor((end - start) / 1000);

    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${mins}m ${secs}s`;
    }
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <div className="flex items-center gap-4">
          <div>
            {/* Editable name */}
            <div className="flex items-center gap-2 mb-1">
              {isEditingName ? (
                <>
                  <input
                    type="text"
                    className="input text-sm py-0.5 px-2 w-48"
                    value={editedName}
                    onChange={(e) => setEditedName(e.target.value)}
                    onKeyDown={handleNameKeyDown}
                    onBlur={handleSaveName}
                    autoFocus
                    placeholder="Enter name..."
                  />
                  <button
                    className="btn btn-icon btn-sm btn-primary"
                    onClick={handleSaveName}
                    title="Save"
                  >
                    <Check className="w-3 h-3" />
                  </button>
                </>
              ) : (
                <>
                  <span className="text-sm font-medium text-gray-200">
                    {agent.name || <span className="text-gray-500 italic">Unnamed</span>}
                  </span>
                  <button
                    className="btn btn-icon btn-sm btn-secondary opacity-50 hover:opacity-100"
                    onClick={() => {
                      setEditedName(agent.name || '');
                      setIsEditingName(true);
                    }}
                    title="Rename"
                  >
                    <Pencil className="w-3 h-3" />
                  </button>
                </>
              )}
            </div>
            <div className="flex items-center gap-2">
              <code className="text-xs font-mono text-gray-500">{agent.id.slice(0, 8)}</code>
              <StatusBadge status={agent.status} isAgent />
              {output.isConnected && (
                <span className="flex items-center gap-1 text-xs text-green-400">
                  <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                  Live
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {agent.canTerminate && (
            <button
              className="btn btn-danger btn-sm"
              onClick={handleTerminate}
            >
              <Square className="w-4 h-4 mr-1" />
              Terminate
            </button>
          )}
          {onClose && (
            <button
              className="btn btn-icon btn-secondary btn-sm"
              onClick={onClose}
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Stats bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800/50 border-b border-gray-700 text-sm">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-1.5 text-gray-400">
            <Cpu className="w-4 h-4" />
            <span>{agent.backend}</span>
          </div>
          <div className="flex items-center gap-1.5 text-gray-400">
            <Clock className="w-4 h-4" />
            <span>{formatDuration()}</span>
          </div>
          <div className="flex items-center gap-1.5 text-gray-400">
            <Hash className="w-4 h-4" />
            <span>{output.chunks.length} chunks</span>
          </div>
          {hasMultipleRuns && (
            <div className="flex items-center gap-1.5 text-blue-400">
              <RotateCcw className="w-4 h-4" />
              <span>Run {agent.runCount + 1}</span>
            </div>
          )}
          {agent.maxTurns && (
            <div className="text-gray-400">
              Max turns: {agent.maxTurns}
            </div>
          )}
          {agent.pid && (
            <div className="text-gray-400">
              PID: {agent.pid}
            </div>
          )}
        </div>
        <div className="flex items-center gap-4">
          {hasMultipleRuns && !output.hasHistory && (
            <button
              className="flex items-center gap-1.5 text-blue-400 hover:text-blue-300 text-xs"
              onClick={handleLoadHistory}
              disabled={loadingHistory}
            >
              {loadingHistory ? (
                <span className="w-3.5 h-3.5 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
              ) : (
                <History className="w-3.5 h-3.5" />
              )}
              <span>Load Full History</span>
            </button>
          )}
          {output.hasHistory && (
            <span className="flex items-center gap-1.5 text-green-400 text-xs">
              <History className="w-3.5 h-3.5" />
              <span>Full History</span>
            </span>
          )}
          <label className="flex items-center gap-2 text-gray-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={verbose}
              onChange={(e) => setVerbose(e.target.checked)}
              className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
            />
            <Code className="w-4 h-4" />
            <span>Verbose</span>
          </label>
        </div>
      </div>

      {/* Output stream */}
      <div className="flex-1 overflow-hidden">
        <OutputStream
          chunks={output.chunks}
          prompts={output.prompts}
          initialPrompt={agent.prompt}
          autoScroll={agent.isRunning}
          verbose={verbose}
        />
      </div>

      {/* Input bar (only for running agents that support input) */}
      {agent.isRunning && (
        <div className="p-4 border-t border-gray-700">
          <div className="flex items-center gap-2">
            <input
              type="text"
              className="input flex-1"
              placeholder="Send input to agent... (Cmd/Ctrl+Enter)"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sending}
            />
            <button
              className="btn btn-primary"
              onClick={handleSendInput}
              disabled={!inputValue.trim() || sending}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Note: Input support depends on the agent backend
          </p>
        </div>
      )}

      {/* Resume bar (for finished agents with session) */}
      {agent.canResume && (
        <div className="p-4 border-t border-gray-700 bg-gray-800/30">
          <div className="flex items-center gap-2 mb-2">
            <RotateCcw className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-gray-300">Resume this session</span>
            <span className="text-xs text-gray-500">(session: {agent.sessionId?.slice(0, 8)}...)</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              className="input flex-1 text-sm pl-4 placeholder:italic placeholder:text-xs placeholder:text-gray-500"
              placeholder="New prompt..."
              value={resumePrompt}
              onChange={(e) => setResumePrompt(e.target.value)}
              onKeyDown={handleResumeKeyDown}
              disabled={loadingResume}
            />
            <button
              className="btn btn-primary"
              onClick={handleResume}
              disabled={!resumePrompt.trim() || loadingResume}
              title="Send (Cmd/Ctrl+Enter)"
            >
              {loadingResume ? (
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              <span className="ml-1">Send</span>
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Creates a new agent that continues this conversation with full history
          </p>
        </div>
      )}

      {/* Error message */}
      {agent.errorMessage && (
        <div className="p-4 bg-red-900/20 border-t border-red-800">
          <div className="text-sm text-red-400">
            <strong>Error:</strong> {agent.errorMessage}
          </div>
        </div>
      )}
    </div>
  );
}

export default AgentDetail;
