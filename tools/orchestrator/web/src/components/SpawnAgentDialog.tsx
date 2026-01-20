import { useState, useEffect } from 'react';
import { X, Play, Download } from 'lucide-react';
import type { AgentBackendType, BackendInfo } from '@/logic/api/types';
import { useDispatch, useLoading, useLogic } from '@/hooks';

type DialogTab = 'spawn' | 'import';

interface SpawnAgentDialogProps {
  open: boolean;
  onClose: () => void;
}

export function SpawnAgentDialog({ open, onClose }: SpawnAgentDialogProps) {
  const dispatch = useDispatch();
  const logic = useLogic();
  const spawnLoading = useLoading('spawn');
  const importLoading = useLoading('importSession');
  const [backends, setBackends] = useState<BackendInfo[]>([]);
  const [activeTab, setActiveTab] = useState<DialogTab>('spawn');

  // Form state for spawn
  const [name, setName] = useState('');
  const [backend, setBackend] = useState<AgentBackendType>('claude-code');
  const [prompt, setPrompt] = useState('');
  const [maxTurns, setMaxTurns] = useState<string>('');
  const [maxBudget, setMaxBudget] = useState<string>('');
  const [workingDir, setWorkingDir] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [model, setModel] = useState('');
  const [disallowedTools, setDisallowedTools] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Form state for import
  const [importSessionId, setImportSessionId] = useState('');
  const [importPrompt, setImportPrompt] = useState('');
  const [importName, setImportName] = useState('');
  const [importBackend, setImportBackend] = useState<AgentBackendType>('claude-code');
  const [importWorkingDir, setImportWorkingDir] = useState('');
  const [importModel, setImportModel] = useState('');

  useEffect(() => {
    logic.api.backends().then((res) => setBackends(res.backends));
  }, [logic.api]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await dispatch({
        type: 'agents.spawn',
        payload: {
          backend,
          prompt,
          name: name || undefined,
          maxTurns: maxTurns ? parseInt(maxTurns, 10) : undefined,
          maxBudgetUsd: maxBudget ? parseFloat(maxBudget) : undefined,
          workingDirectory: workingDir || undefined,
          systemPrompt: systemPrompt || undefined,
          model: model || undefined,
        },
      });
      resetForm();
      onClose();
    } catch (e) {
      // Error is handled in logic layer
    }
  };

  const resetForm = () => {
    setName('');
    setPrompt('');
    setMaxTurns('');
    setMaxBudget('');
    setWorkingDir('');
    setSystemPrompt('');
    setModel('');
    setDisallowedTools('');
    setShowAdvanced(false);
    // Import form
    setImportSessionId('');
    setImportPrompt('');
    setImportName('');
    setImportWorkingDir('');
    setImportModel('');
  };

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await dispatch({
        type: 'agents.importSession',
        payload: {
          sessionId: importSessionId,
          prompt: importPrompt,
          name: importName || undefined,
          backend: importBackend,
          workingDirectory: importWorkingDir || undefined,
          model: importModel || undefined,
        },
      });
      resetForm();
      onClose();
    } catch (e) {
      // Error is handled in logic layer
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
      />

      {/* Dialog */}
      <div className="relative bg-gray-800 rounded-lg border border-gray-700 w-full max-w-lg mx-4 shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold">
            {activeTab === 'spawn' ? 'Spawn Agent' : 'Import Session'}
          </h2>
          <button
            className="btn btn-icon btn-secondary btn-sm"
            onClick={onClose}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-700">
          <button
            type="button"
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'spawn'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-gray-300'
            }`}
            onClick={() => setActiveTab('spawn')}
          >
            <Play className="w-4 h-4 inline-block mr-1" />
            New Agent
          </button>
          <button
            type="button"
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'import'
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-gray-300'
            }`}
            onClick={() => setActiveTab('import')}
          >
            <Download className="w-4 h-4 inline-block mr-1" />
            Import Session
          </button>
        </div>

        {/* Spawn Form */}
        {activeTab === 'spawn' && (
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Name
            </label>
            <input
              type="text"
              className="input"
              placeholder="e.g., my-agent (optional)"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          {/* Backend */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Backend
            </label>
            <select
              className="input"
              value={backend}
              onChange={(e) => setBackend(e.target.value as AgentBackendType)}
            >
              {backends.map((b) => (
                <option key={b.type} value={b.type}>
                  {b.type}
                </option>
              ))}
            </select>
          </div>

          {/* Prompt */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Prompt <span className="text-red-400">*</span>
            </label>
            <textarea
              className="input min-h-[100px]"
              placeholder="Enter your prompt for the agent..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              required
            />
          </div>

          {/* Basic options */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Max Turns
              </label>
              <input
                type="number"
                className="input"
                placeholder="e.g., 10"
                value={maxTurns}
                onChange={(e) => setMaxTurns(e.target.value)}
                min="1"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Max Budget (USD)
              </label>
              <input
                type="number"
                className="input"
                placeholder="e.g., 1.0"
                value={maxBudget}
                onChange={(e) => setMaxBudget(e.target.value)}
                min="0"
                step="0.01"
              />
            </div>
          </div>

          {/* Advanced toggle */}
          <button
            type="button"
            className="text-sm text-blue-400 hover:text-blue-300"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            {showAdvanced ? 'Hide' : 'Show'} advanced options
          </button>

          {/* Advanced options */}
          {showAdvanced && (
            <div className="space-y-4 pt-2 border-t border-gray-700">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Working Directory
                </label>
                <input
                  type="text"
                  className="input"
                  placeholder="/path/to/project"
                  value={workingDir}
                  onChange={(e) => setWorkingDir(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  System Prompt
                </label>
                <textarea
                  className="input min-h-[60px]"
                  placeholder="Custom system prompt..."
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Model
                  </label>
                  <select
                    className="input"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                  >
                    <option value="">Default</option>
                    <option value="sonnet">Sonnet</option>
                    <option value="opus">Opus</option>
                    <option value="haiku">Haiku</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Disallowed Tools
                  </label>
                  <input
                    type="text"
                    className="input"
                    placeholder="Bash, Write, ..."
                    value={disallowedTools}
                    onChange={(e) => setDisallowedTools(e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-4">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-success"
              disabled={!prompt.trim() || spawnLoading}
            >
              <Play className="w-4 h-4 mr-1" />
              {spawnLoading ? 'Spawning...' : 'Spawn Agent'}
            </button>
          </div>
        </form>
        )}

        {/* Import Form */}
        {activeTab === 'import' && (
        <form onSubmit={handleImport} className="p-4 space-y-4">
          {/* Session ID */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Session ID <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              className="input font-mono"
              placeholder="e.g., abc123-def456-..."
              value={importSessionId}
              onChange={(e) => setImportSessionId(e.target.value)}
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              The session ID from Claude Code CLI (shown when running with --verbose)
            </p>
          </div>

          {/* Prompt */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Prompt <span className="text-red-400">*</span>
            </label>
            <textarea
              className="input min-h-[80px]"
              placeholder="Continue with this prompt..."
              value={importPrompt}
              onChange={(e) => setImportPrompt(e.target.value)}
              required
            />
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Name
            </label>
            <input
              type="text"
              className="input"
              placeholder="Optional name for this agent"
              value={importName}
              onChange={(e) => setImportName(e.target.value)}
            />
          </div>

          {/* Backend and Model */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Backend
              </label>
              <select
                className="input"
                value={importBackend}
                onChange={(e) => setImportBackend(e.target.value as AgentBackendType)}
              >
                {backends.map((b) => (
                  <option key={b.type} value={b.type}>
                    {b.type}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Model
              </label>
              <select
                className="input"
                value={importModel}
                onChange={(e) => setImportModel(e.target.value)}
              >
                <option value="">Default</option>
                <option value="sonnet">Sonnet</option>
                <option value="opus">Opus</option>
                <option value="haiku">Haiku</option>
              </select>
            </div>
          </div>

          {/* Working Directory */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Working Directory
            </label>
            <input
              type="text"
              className="input"
              placeholder="/path/to/project (optional)"
              value={importWorkingDir}
              onChange={(e) => setImportWorkingDir(e.target.value)}
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-4">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-success"
              disabled={!importSessionId.trim() || !importPrompt.trim() || importLoading}
            >
              <Download className="w-4 h-4 mr-1" />
              {importLoading ? 'Importing...' : 'Import Session'}
            </button>
          </div>
        </form>
        )}
      </div>
    </div>
  );
}

export default SpawnAgentDialog;
