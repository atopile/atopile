import { useState, useEffect } from 'react';
import { X, Play } from 'lucide-react';
import type { AgentBackendType, AgentConfig, BackendInfo } from '@/api/types';
import { api } from '@/api/client';
import { useAgentStore } from '@/stores';

interface SpawnAgentDialogProps {
  open: boolean;
  onClose: () => void;
}

export function SpawnAgentDialog({ open, onClose }: SpawnAgentDialogProps) {
  const { spawnAgent, loading } = useAgentStore();
  const [backends, setBackends] = useState<BackendInfo[]>([]);

  // Form state
  const [backend, setBackend] = useState<AgentBackendType>('claude-code');
  const [prompt, setPrompt] = useState('');
  const [maxTurns, setMaxTurns] = useState<string>('');
  const [maxBudget, setMaxBudget] = useState<string>('');
  const [workingDir, setWorkingDir] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [model, setModel] = useState('');
  const [disallowedTools, setDisallowedTools] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    api.backends().then((res) => setBackends(res.backends));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const config: AgentConfig = {
      backend,
      prompt,
      max_turns: maxTurns ? parseInt(maxTurns, 10) : undefined,
      max_budget_usd: maxBudget ? parseFloat(maxBudget) : undefined,
      working_directory: workingDir || undefined,
      system_prompt: systemPrompt || undefined,
      model: model || undefined,
      disallowed_tools: disallowedTools
        ? disallowedTools.split(',').map((t) => t.trim())
        : undefined,
    };

    try {
      await spawnAgent(config);
      resetForm();
      onClose();
    } catch (e) {
      // Error is handled in store
    }
  };

  const resetForm = () => {
    setPrompt('');
    setMaxTurns('');
    setMaxBudget('');
    setWorkingDir('');
    setSystemPrompt('');
    setModel('');
    setDisallowedTools('');
    setShowAdvanced(false);
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
          <h2 className="text-lg font-semibold">Spawn Agent</h2>
          <button
            className="btn btn-icon btn-secondary btn-sm"
            onClick={onClose}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
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
              disabled={!prompt.trim() || loading}
            >
              <Play className="w-4 h-4 mr-1" />
              {loading ? 'Spawning...' : 'Spawn Agent'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default SpawnAgentDialog;
