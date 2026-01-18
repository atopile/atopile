import { useEffect, useState } from 'react';
import { Square, Send, X, Clock, Cpu, Hash, Code, RotateCcw, Pencil, Check } from 'lucide-react';
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
  const { connectToAgent, disconnectFromAgent, fetchOutput, clearOutput, isConnected } = useOutputStore();
  // Subscribe directly to chunks for this agent - this ensures re-renders on updates
  const chunks = useOutputStore((state) => state.outputs.get(agent.id) || []);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [verbose, setVerbose] = useState(false);
  const [resumePrompt, setResumePrompt] = useState('');
  const [resuming, setResuming] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState(agent.name || '');
  const connected = isConnected(agent.id);
  const isRunning = agent.status === 'running' || agent.status === 'starting' || agent.status === 'pending';
  const isFinished = agent.status === 'completed' || agent.status === 'failed' || agent.status === 'terminated';
  const canResume = isFinished && !!agent.session_id;

  // Connect to WebSocket for running agents
  useEffect(() => {
    // Always fetch existing output first
    fetchOutput(agent.id);

    // Connect to WebSocket for real-time updates
    if (isRunning) {
      connectToAgent(agent.id);
    }

    return () => {
      disconnectFromAgent(agent.id);
    };
  }, [agent.id, isRunning, connectToAgent, disconnectFromAgent, fetchOutput]);

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

    setResuming(true);
    try {
      // Clear old output before resuming so we fetch fresh output
      clearOutput(agent.id);
      await resumeAgent(agent.id, resumePrompt);
      setResumePrompt('');
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
    if (!agent.started_at) return '-';

    const start = new Date(agent.started_at).getTime();
    const end = agent.finished_at
      ? new Date(agent.finished_at).getTime()
      : Date.now();
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

      {/* Prompt */}
      <div className="px-4 py-3 bg-gray-800/30 border-b border-gray-700">
        <div className="text-xs text-gray-500 mb-1">Prompt</div>
        <p className="text-sm text-gray-300">{agent.config.prompt}</p>
      </div>

      {/* Output stream */}
      <div className="flex-1 overflow-hidden">
        <OutputStream chunks={chunks} autoScroll={isRunning} verbose={verbose} />
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
              className="input flex-1"
              placeholder="Enter new prompt to continue conversation... (Cmd/Ctrl+Enter)"
              value={resumePrompt}
              onChange={(e) => setResumePrompt(e.target.value)}
              onKeyDown={handleResumeKeyDown}
              disabled={resuming}
            />
            <button
              className="btn btn-primary"
              onClick={handleResume}
              disabled={!resumePrompt.trim() || resuming}
            >
              {resuming ? (
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <RotateCcw className="w-4 h-4" />
              )}
              <span className="ml-1">Resume</span>
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
