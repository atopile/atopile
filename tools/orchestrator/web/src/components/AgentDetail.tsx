import { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { Square, Send, X, Clock, Cpu, Hash, Code, RotateCcw, Pencil, Check, History, Sparkles, Settings, ChevronDown, ChevronUp, ArrowLeft } from 'lucide-react';
import type { AgentViewModel } from '@/logic/viewmodels';
import { useDispatch, useAgentOutput, useLoading, useMobile } from '@/hooks';
import { StatusBadge } from './StatusBadge';
import { OutputStream } from './OutputStream';
import { VimTextarea } from './VimTextarea';
import { TodoList } from './TodoList';

// Completion settings stored in localStorage
type CompletionMode = 'code' | 'prompt';

interface CompletionSettings {
  enabled: boolean;
  endpoint: string;
  model: string;
  mode: CompletionMode;
}

const DEFAULT_COMPLETION_SETTINGS: CompletionSettings = {
  enabled: false,
  endpoint: 'http://localhost:11434/api/generate',
  model: 'qwen2.5:7b',
  mode: 'prompt',
};

function loadCompletionSettings(): CompletionSettings {
  try {
    const stored = localStorage.getItem('vim-completion-settings');
    if (stored) {
      return { ...DEFAULT_COMPLETION_SETTINGS, ...JSON.parse(stored) };
    }
  } catch (e) {
    console.error('Failed to load completion settings:', e);
  }
  return DEFAULT_COMPLETION_SETTINGS;
}

function saveCompletionSettings(settings: CompletionSettings) {
  try {
    localStorage.setItem('vim-completion-settings', JSON.stringify(settings));
  } catch (e) {
    console.error('Failed to save completion settings:', e);
  }
}

interface AgentDetailProps {
  agent: AgentViewModel;
  onClose?: () => void;
}

export function AgentDetail({ agent, onClose }: AgentDetailProps) {
  const dispatch = useDispatch();
  const isMobile = useMobile();
  const output = useAgentOutput(agent.id);
  const loadingResume = useLoading(`resume-${agent.id}`);

  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const [verbose, setVerbose] = useState(false);
  const [resumePrompt, setResumePrompt] = useState('');
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState(agent.name || '');
  const [vimMode, setVimMode] = useState(false);
  const [completionSettings, setCompletionSettings] = useState<CompletionSettings>(loadCompletionSettings);
  const [showCompletionSettings, setShowCompletionSettings] = useState(false);
  const [showStats, setShowStats] = useState(!isMobile); // Collapsed by default on mobile
  const settingsPopoverRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Refs for stable callbacks (prevents re-renders when input values change)
  const inputValueRef = useRef(inputValue);
  const resumePromptRef = useRef(resumePrompt);
  inputValueRef.current = inputValue;
  resumePromptRef.current = resumePrompt;

  // Close settings popover when clicking outside
  useEffect(() => {
    if (!showCompletionSettings) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (settingsPopoverRef.current && !settingsPopoverRef.current.contains(e.target as Node)) {
        setShowCompletionSettings(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showCompletionSettings]);

  // Memoize completion config for VimTextarea
  const completionConfig = useMemo(() => ({
    enabled: completionSettings.enabled,
    endpoint: completionSettings.endpoint,
    model: completionSettings.model,
    mode: completionSettings.mode,
    debounceMs: 400,
  }), [completionSettings]);

  // Save completion settings when they change
  const updateCompletionSettings = useCallback((updates: Partial<CompletionSettings>) => {
    setCompletionSettings(prev => {
      const newSettings = { ...prev, ...updates };
      saveCompletionSettings(newSettings);
      return newSettings;
    });
  }, []);

  const hasMultipleRuns = agent.runCount > 0;

  // Initial data fetch and run number tracking
  // This runs when agent.id OR agent.runCount changes (e.g., after resume)
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
  }, [agent.id, agent.runCount, hasMultipleRuns, dispatch]);

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

  // Stable callback - uses ref to avoid recreating on every keystroke
  const handleSendInput = useCallback(async () => {
    const value = inputValueRef.current;
    if (!value.trim() || !agent.isRunning) return;

    setSending(true);
    try {
      await dispatch({
        type: 'agents.sendInput',
        payload: { agentId: agent.id, input: value },
      });
      setInputValue('');
    } finally {
      setSending(false);
    }
  }, [dispatch, agent.id, agent.isRunning]);

  // Stable callback - uses ref to avoid recreating on every keystroke
  const handleResume = useCallback(async () => {
    const value = resumePromptRef.current;
    if (!value.trim() || !agent.canResume) return;

    const promptText = value.trim();
    setResumePrompt('');

    try {
      await dispatch({
        type: 'agents.resume',
        payload: { agentId: agent.id, prompt: promptText },
      });
    } catch (e) {
      // Error is handled in logic layer
    }
  }, [dispatch, agent.id, agent.canResume]);

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
    <div
      ref={containerRef}
      className="flex flex-col h-full relative"
    >
      {/* Header */}
      <div
        className={`flex items-center justify-between border-b border-gray-700 ${
          isMobile ? 'px-3 py-2' : 'p-4'
        }`}
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* Back button for narrow screens */}
          {isMobile && onClose && (
            <button
              className="btn btn-icon btn-secondary btn-sm mr-1"
              onClick={onClose}
              title="Back to list"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
          )}
          <div className="min-w-0 flex-1">
            {/* Editable name */}
            <div className="flex items-center gap-2">
              {isEditingName ? (
                <>
                  <input
                    type="text"
                    className={`input py-0.5 px-2 ${isMobile ? 'text-xs w-32' : 'text-sm w-48'}`}
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
                  <span className={`font-medium text-gray-200 truncate ${isMobile ? 'text-xs max-w-[120px]' : 'text-sm'}`}>
                    {agent.name || <span className="text-gray-500 italic">Unnamed</span>}
                  </span>
                  {!isMobile && (
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
                  )}
                </>
              )}
              <StatusBadge status={agent.status} isAgent />
              {output.isConnected && (
                <span className="flex items-center gap-1 text-xs text-green-400">
                  <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                  {!isMobile && 'Live'}
                </span>
              )}
            </div>
            {!isMobile && (
              <code className="text-xs font-mono text-gray-500">{agent.id.slice(0, 8)}</code>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1">
          {agent.canTerminate && (
            <button
              className={`btn btn-danger ${isMobile ? 'btn-icon' : 'btn-sm'}`}
              onClick={handleTerminate}
              title="Terminate"
            >
              <Square className="w-4 h-4" />
              {!isMobile && <span className="ml-1">Terminate</span>}
            </button>
          )}
          {onClose && !isMobile && (
            <button
              className="btn btn-icon btn-secondary btn-sm"
              onClick={onClose}
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Stats bar - collapsible on mobile */}
      <div className={`bg-gray-800/50 border-b border-gray-700 ${isMobile ? 'text-xs' : 'text-sm'}`}>
        {/* Mobile: show toggle + key stats */}
        {isMobile ? (
          <>
            <div
              className="flex items-center justify-between px-3 py-1.5 cursor-pointer"
              onClick={() => setShowStats(!showStats)}
            >
              <div className="flex items-center gap-3">
                <span className="text-gray-400">{agent.backend}</span>
                <span className="text-gray-400">{formatDuration()}</span>
                {hasMultipleRuns && (
                  <span className="text-blue-400">Run {agent.runCount + 1}</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-1 text-gray-400">
                  <input
                    type="checkbox"
                    checked={verbose}
                    onChange={(e) => { e.stopPropagation(); setVerbose(e.target.checked); }}
                    className="w-3 h-3 rounded border-gray-600 bg-gray-700 text-blue-500"
                  />
                  <Code className="w-3 h-3" />
                </label>
                {showStats ? <ChevronUp className="w-3 h-3 text-gray-500" /> : <ChevronDown className="w-3 h-3 text-gray-500" />}
              </div>
            </div>
            {showStats && (
              <div className="px-3 py-2 border-t border-gray-700/50 space-y-2">
                <div className="flex items-center gap-4 flex-wrap">
                  <span className="text-gray-400">{output.chunks.length} chunks</span>
                  {agent.maxTurns && <span className="text-gray-400">Max: {agent.maxTurns}</span>}
                  {agent.pid && <span className="text-gray-400">PID: {agent.pid}</span>}
                </div>
                <div className="flex items-center gap-3">
                  {hasMultipleRuns && !output.hasHistory && (
                    <button
                      className="flex items-center gap-1 text-blue-400 hover:text-blue-300"
                      onClick={handleLoadHistory}
                      disabled={loadingHistory}
                    >
                      <History className="w-3 h-3" />
                      <span>Load History</span>
                    </button>
                  )}
                  <button
                    className={`flex items-center gap-1 ${completionSettings.enabled ? 'text-purple-400' : 'text-gray-400'}`}
                    onClick={() => setShowCompletionSettings(!showCompletionSettings)}
                  >
                    <Sparkles className="w-3 h-3" />
                    <span>AI</span>
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          /* Desktop: full stats bar */
          <div className="flex items-center justify-between px-4 py-2">
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
              {/* Completion settings */}
              <div className="relative" ref={settingsPopoverRef}>
                <button
                  className={`flex items-center gap-1.5 text-xs cursor-pointer select-none ${
                    completionSettings.enabled ? 'text-purple-400' : 'text-gray-400'
                  } hover:text-purple-300`}
                  onClick={() => setShowCompletionSettings(!showCompletionSettings)}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>AI</span>
                  <Settings className="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>
        )}
        {/* Completion settings popover - shared between mobile and desktop */}
        {showCompletionSettings && (
          <div ref={settingsPopoverRef} className={`${isMobile ? 'px-3 py-2 border-t border-gray-700/50' : 'absolute right-4 top-full mt-1 w-72 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50 p-3'}`}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-gray-200">Tab Completion</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={completionSettings.enabled}
                  onChange={(e) => updateCompletionSettings({ enabled: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-purple-600"></div>
              </label>
            </div>
            <div className="space-y-2">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Mode</label>
                <div className="flex gap-1">
                  <button
                    onClick={() => updateCompletionSettings({ mode: 'prompt' })}
                    className={`flex-1 px-2 py-1 text-xs rounded transition-colors ${
                      completionSettings.mode === 'prompt'
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                    }`}
                  >
                    Prompt
                  </button>
                  <button
                    onClick={() => updateCompletionSettings({ mode: 'code' })}
                    className={`flex-1 px-2 py-1 text-xs rounded transition-colors ${
                      completionSettings.mode === 'code'
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                    }`}
                  >
                    Code
                  </button>
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Model</label>
                <input
                  type="text"
                  value={completionSettings.model}
                  onChange={(e) => updateCompletionSettings({ model: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-600 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-purple-500"
                  placeholder="qwen2.5:7b"
                />
              </div>
              {!isMobile && (
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Ollama Endpoint</label>
                  <input
                    type="text"
                    value={completionSettings.endpoint}
                    onChange={(e) => updateCompletionSettings({ endpoint: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-600 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-purple-500"
                    placeholder="http://localhost:11434/api/generate"
                  />
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Mobile: Always-visible agent name bar */}
      {isMobile && (
        <div className="flex items-center justify-between px-3 py-1.5 bg-gray-800/80 border-b border-gray-700/50 text-xs">
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-medium text-gray-300 truncate">
              {agent.name || 'Unnamed'}
            </span>
            <StatusBadge status={agent.status} isAgent />
          </div>
          <span className="text-gray-500">{formatDuration()}</span>
        </div>
      )}

      {/* Todo list (if agent has todos) */}
      {agent.todos && agent.todos.length > 0 && (
        <TodoList todos={agent.todos} compact={isMobile} />
      )}

      {/* Output stream */}
      <div className="flex-1 overflow-hidden">
        <OutputStream
          chunks={output.chunks}
          prompts={output.prompts}
          initialPrompt={agent.prompt}
          autoScroll={agent.isRunning}
          verbose={verbose}
          isAgentRunning={agent.isRunning}
          onSendInput={(input) => {
            dispatch({
              type: 'agents.sendInput',
              payload: { agentId: agent.id, input },
            });
          }}
        />
      </div>

      {/* Input bar (only for running agents that support input) */}
      {agent.isRunning && (
        <div className={`border-t border-gray-700 ${isMobile ? 'p-2' : 'p-4'}`}>
          <div className="flex gap-2 items-end">
            <VimTextarea
              value={inputValue}
              onChange={setInputValue}
              onSubmit={handleSendInput}
              placeholder="Send input..."
              disabled={sending}
              vimMode={vimMode}
              onVimModeToggle={setVimMode}
              className="flex-1"
              completion={completionConfig}
              compact={isMobile}
            />
            <button
              className="rounded-full w-9 h-9 mb-0.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center justify-center text-white shadow-lg flex-shrink-0"
              onClick={handleSendInput}
              disabled={!inputValue.trim() || sending}
              title="Send (⌘+Enter)"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Resume bar (for finished agents with session) */}
      {agent.canResume && (
        <div className={`border-t border-gray-700 bg-gray-800/30 ${isMobile ? 'p-2' : 'p-4'}`}>
          <div className="flex gap-2 items-end">
            <VimTextarea
              value={resumePrompt}
              onChange={setResumePrompt}
              onSubmit={handleResume}
              placeholder="Continue conversation..."
              disabled={loadingResume}
              vimMode={vimMode}
              onVimModeToggle={setVimMode}
              className="flex-1"
              completion={completionConfig}
              compact={isMobile}
            />
            <button
              className="rounded-full w-9 h-9 mb-0.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center justify-center text-white shadow-lg flex-shrink-0"
              onClick={handleResume}
              disabled={!resumePrompt.trim() || loadingResume}
              title="Send (⌘+Enter)"
            >
              {loadingResume ? (
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
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
