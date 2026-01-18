import { useEffect, useState } from 'react';
import { Square, Send, X, Clock, Cpu, Hash, Code, RotateCcw, Pencil, Check, History } from 'lucide-react';
import type { AgentState } from '@/api/types';
import { useAgentStore, useOutputStore } from '@/stores';
import { StatusBadge } from './StatusBadge';
import { OutputStream } from './OutputStream';

interface AgentDetailProps {
  agent: AgentState;
  onClose?: () => void;
}

export function AgentDetail({ agent, onClose }: AgentDetailProps) {
  const { terminateAgent, sendInput, resumeAgent, renameAgent } = useAgentStore();
  const { connectToAgent, disconnectFromAgent, fetchOutput, fetchFullHistory, isConnected, setCurrentRunNumber, addPrompt } = useOutputStore();
  // Subscribe directly to chunks for this agent - this ensures re-renders on updates
  const chunks = useOutputStore((state) => state.outputs.get(agent.id) || []);
  const prompts = useOutputStore((state) => state.prompts.get(agent.id) || []);
  const historyLoaded = useOutputStore((state) => state.historyLoaded.has(agent.id));
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [verbose, setVerbose] = useState(false);
  const [resumePrompt, setResumePrompt] = useState('');
  const [resuming, setResuming] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState(agent.name || '');
  const connected = isConnected(agent.id);
  const isRunning = agent.status === 'running' || agent.status === 'starting' || agent.status === 'pending';
  const isFinished = agent.status === 'completed' || agent.status === 'failed' || agent.status === 'terminated';
  const canResume = isFinished && !!agent.session_id;
  const runCount = agent.run_count ?? 0;
  const hasMultipleRuns = runCount > 0;

  // Initial data fetch - only runs when agent.id changes
  useEffect(() => {
    // Set the current run number so new WebSocket chunks get tagged correctly
    setCurrentRunNumber(agent.id, runCount);

    // For agents with multiple runs, load full history to see all runs
    if (hasMultipleRuns) {
      fetchFullHistory(agent.id);
    } else {
      // Single-run agent - fetch current output
      fetchOutput(agent.id, runCount);
    }
    // Note: We intentionally only depend on agent.id to avoid re-fetching
    // when other properties change. The runCount and hasMultipleRuns are
    // captured at the time of the effect run.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agent.id]);

  // Add initial prompt for single-run agents (separate effect to avoid re-fetch)
  useEffect(() => {
    if (!hasMultipleRuns && agent.config.prompt && prompts.length === 0) {
      addPrompt(agent.id, 0, agent.config.prompt);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agent.id, hasMultipleRuns]);

  // WebSocket connection - separate effect for running state
  useEffect(() => {
    if (isRunning) {
      connectToAgent(agent.id);
    }

    return () => {
      disconnectFromAgent(agent.id);
    };
  }, [agent.id, isRunning, connectToAgent, disconnectFromAgent]);

  const handleLoadHistory = async () => {
    setLoadingHistory(true);
    try {
      await fetchFullHistory(agent.id);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleSendInput = async () => {
    if (!inputValue.trim() || !isRunning) return;

    setSending(true);
    try {
      const success = await sendInput(agent.id, inputValue);
      if (success) {
        setInputValue('');
      }
    } finally {
      setSending(false);
    }
  };

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

  const handleResume = async () => {
    if (!resumePrompt.trim() || !canResume) return;

    const promptText = resumePrompt.trim();
    const nextRunNumber = runCount + 1;

    // Immediately show the prompt in UI for instant feedback
    addPrompt(agent.id, nextRunNumber, promptText);
    setCurrentRunNumber(agent.id, nextRunNumber);
    setResumePrompt('');
    setResuming(true);

    try {
      await resumeAgent(agent.id, promptText);
      // The useEffect will reconnect to WebSocket and fetch new output
      // when agent.status changes to 'running'
    } finally {
      setResuming(false);
    }
  };

  const handleSaveName = async () => {
    if (editedName.trim() !== (agent.name || '')) {
      try {
        await renameAgent(agent.id, editedName.trim());
      } catch (e) {
        // Error is handled in store
      }
    }
    setIsEditingName(false);
  };

  const handleNameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSaveName();
    } else if (e.key === 'Escape') {
      setEditedName(agent.name || '');
      setIsEditingName(false);
    }
  };

  const formatDuration = () => {
    if (!agent.started_at) return '—';

    const start = new Date(agent.started_at).getTime();
    if (isNaN(start)) return '—';

    let end: number;
    if (agent.finished_at) {
      end = new Date(agent.finished_at).getTime();
      if (isNaN(end)) return '—';
    } else if (isRunning) {
      end = Date.now();
    } else {
      return '—'; // Finished but no end time
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
              <StatusBadge status={agent.status} />
              {connected && (
                <span className="flex items-center gap-1 text-xs text-green-400">
                  <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                  Live
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isRunning && (
            <button
              className="btn btn-danger btn-sm"
              onClick={() => terminateAgent(agent.id)}
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
            <span>{agent.config.backend}</span>
          </div>
          <div className="flex items-center gap-1.5 text-gray-400">
            <Clock className="w-4 h-4" />
            <span>{formatDuration()}</span>
          </div>
          <div className="flex items-center gap-1.5 text-gray-400">
            <Hash className="w-4 h-4" />
            <span>{chunks.length} chunks</span>
          </div>
          {hasMultipleRuns && (
            <div className="flex items-center gap-1.5 text-blue-400">
              <RotateCcw className="w-4 h-4" />
              <span>Run {runCount + 1}</span>
            </div>
          )}
          {agent.config.max_turns && (
            <div className="text-gray-400">
              Max turns: {agent.config.max_turns}
            </div>
          )}
          {agent.pid && (
            <div className="text-gray-400">
              PID: {agent.pid}
            </div>
          )}
        </div>
        <div className="flex items-center gap-4">
          {hasMultipleRuns && !historyLoaded && (
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
          {historyLoaded && (
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
          chunks={chunks}
          prompts={prompts}
          initialPrompt={agent.config.prompt}
          autoScroll={isRunning}
          verbose={verbose}
        />
      </div>

      {/* Input bar (only for running agents that support input) */}
      {isRunning && (
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
      {canResume && (
        <div className="p-4 border-t border-gray-700 bg-gray-800/30">
          <div className="flex items-center gap-2 mb-2">
            <RotateCcw className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-gray-300">Resume this session</span>
            <span className="text-xs text-gray-500">(session: {agent.session_id?.slice(0, 8)}...)</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              className="input flex-1 text-sm pl-4 placeholder:italic placeholder:text-xs placeholder:text-gray-500"
              placeholder="New prompt..."
              value={resumePrompt}
              onChange={(e) => setResumePrompt(e.target.value)}
              onKeyDown={handleResumeKeyDown}
              disabled={resuming}
            />
            <button
              className="btn btn-primary"
              onClick={handleResume}
              disabled={!resumePrompt.trim() || resuming}
              title="Send (Cmd/Ctrl+Enter)"
            >
              {resuming ? (
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
      {agent.error_message && (
        <div className="p-4 bg-red-900/20 border-t border-red-800">
          <div className="text-sm text-red-400">
            <strong>Error:</strong> {agent.error_message}
          </div>
        </div>
      )}
    </div>
  );
}

export default AgentDetail;
