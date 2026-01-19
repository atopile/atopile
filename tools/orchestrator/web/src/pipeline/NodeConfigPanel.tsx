import { useState, useEffect } from 'react';
import { X, Bot, Clock, GitBranch, Timer } from 'lucide-react';
import type { Node } from '@xyflow/react';

interface NodeConfigPanelProps {
  node: Node;
  onUpdate: (nodeId: string, data: Record<string, unknown>) => void;
  onClose: () => void;
}

export function NodeConfigPanel({ node, onUpdate, onClose }: NodeConfigPanelProps) {
  const [formData, setFormData] = useState<Record<string, unknown>>(node.data);

  // Update form data when node changes
  useEffect(() => {
    setFormData(node.data);
  }, [node.id, node.data]);

  const handleChange = (field: string, value: unknown) => {
    const updated = { ...formData, [field]: value };
    setFormData(updated);
    onUpdate(node.id, updated);
  };

  const getIcon = () => {
    switch (node.type) {
      case 'agent':
        return <Bot className="w-5 h-5 text-green-400" />;
      case 'trigger':
        return <Clock className="w-5 h-5 text-blue-400" />;
      case 'wait':
        return <Timer className="w-5 h-5 text-yellow-400" />;
      case 'condition':
        return <GitBranch className="w-5 h-5 text-cyan-400" />;
      default:
        return null;
    }
  };

  const getTitle = () => {
    switch (node.type) {
      case 'agent':
        return 'Agent Node';
      case 'trigger':
        return 'Trigger Node';
      case 'wait':
        return 'Wait Node';
      case 'condition':
        return 'Condition Node';
      default:
        return 'Node Config';
    }
  };

  return (
    <div className="w-80 bg-gray-800 border-l border-gray-700 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <div className="flex items-center gap-2">
          {getIcon()}
          <span className="font-medium">{getTitle()}</span>
        </div>
        <button
          className="p-1 hover:bg-gray-700 rounded"
          onClick={onClose}
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Form */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {node.type === 'agent' && (
          <AgentConfigForm data={formData} onChange={handleChange} />
        )}
        {node.type === 'trigger' && (
          <TriggerConfigForm data={formData} onChange={handleChange} />
        )}
        {node.type === 'wait' && (
          <WaitConfigForm data={formData} onChange={handleChange} />
        )}
        {node.type === 'condition' && (
          <ConditionConfigForm data={formData} onChange={handleChange} />
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700">
        <p className="text-xs text-gray-500">
          Node ID: {node.id}
        </p>
      </div>
    </div>
  );
}

interface ConfigFormProps {
  data: Record<string, unknown>;
  onChange: (field: string, value: unknown) => void;
}

function AgentConfigForm({ data, onChange }: ConfigFormProps) {
  return (
    <>
      <div>
        <label className="block text-sm text-gray-400 mb-1">Name</label>
        <input
          type="text"
          className="input input-sm w-full"
          value={(data.name as string) || ''}
          onChange={(e) => onChange('name', e.target.value)}
          placeholder="Agent name"
        />
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-1">Backend</label>
        <select
          className="input input-sm w-full"
          value={(data.backend as string) || 'claude-code'}
          onChange={(e) => onChange('backend', e.target.value)}
        >
          <option value="claude-code">Claude Code</option>
          <option value="codex">Codex</option>
          <option value="cursor">Cursor</option>
        </select>
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-1">Prompt</label>
        <textarea
          className="input input-sm w-full min-h-[100px] resize-y"
          value={(data.prompt as string) || ''}
          onChange={(e) => onChange('prompt', e.target.value)}
          placeholder="Enter the prompt for this agent..."
        />
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-1">System Prompt (optional)</label>
        <textarea
          className="input input-sm w-full min-h-[60px] resize-y"
          value={(data.system_prompt as string) || ''}
          onChange={(e) => onChange('system_prompt', e.target.value)}
          placeholder="Optional system prompt..."
        />
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-1">Max Turns</label>
        <input
          type="number"
          className="input input-sm w-full"
          value={(data.max_turns as number) || ''}
          onChange={(e) => onChange('max_turns', e.target.value ? parseInt(e.target.value) : undefined)}
          placeholder="No limit"
          min={1}
        />
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-1">Max Budget (USD)</label>
        <input
          type="number"
          className="input input-sm w-full"
          value={(data.max_budget_usd as number) || ''}
          onChange={(e) => onChange('max_budget_usd', e.target.value ? parseFloat(e.target.value) : undefined)}
          placeholder="No limit"
          min={0}
          step={0.01}
        />
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-1">Working Directory</label>
        <input
          type="text"
          className="input input-sm w-full"
          value={(data.working_directory as string) || ''}
          onChange={(e) => onChange('working_directory', e.target.value || undefined)}
          placeholder="Current directory"
        />
      </div>
    </>
  );
}

function TriggerConfigForm({ data, onChange }: ConfigFormProps) {
  return (
    <>
      <div>
        <label className="block text-sm text-gray-400 mb-1">Trigger Type</label>
        <select
          className="input input-sm w-full"
          value={(data.trigger_type as string) || 'manual'}
          onChange={(e) => onChange('trigger_type', e.target.value)}
        >
          <option value="manual">Manual</option>
          <option value="timer">Timer</option>
          <option value="webhook">Webhook</option>
        </select>
      </div>

      {data.trigger_type === 'timer' && (
        <>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Interval (seconds)</label>
            <input
              type="number"
              className="input input-sm w-full"
              value={(data.interval_seconds as number) || 3600}
              onChange={(e) => onChange('interval_seconds', parseInt(e.target.value))}
              min={1}
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Cron Expression (optional)</label>
            <input
              type="text"
              className="input input-sm w-full"
              value={(data.cron_expression as string) || ''}
              onChange={(e) => onChange('cron_expression', e.target.value || undefined)}
              placeholder="*/5 * * * *"
            />
          </div>
        </>
      )}
    </>
  );
}

function WaitConfigForm({ data, onChange }: ConfigFormProps) {
  return (
    <>
      <div>
        <label className="block text-sm text-gray-400 mb-1">Duration (seconds)</label>
        <input
          type="number"
          className="input input-sm w-full"
          value={(data.duration_seconds as number) || 60}
          onChange={(e) => onChange('duration_seconds', parseInt(e.target.value))}
          min={1}
        />
        <p className="text-xs text-gray-500 mt-1">
          How long to wait before continuing to the next node
        </p>
      </div>

      <div className="bg-gray-700/50 p-3 rounded-lg">
        <p className="text-xs text-gray-400">
          The wait node pauses execution for the specified duration.
          Use it with a condition node to create loops.
        </p>
      </div>
    </>
  );
}

function ConditionConfigForm({ data, onChange }: ConfigFormProps) {
  return (
    <>
      <div className="bg-gray-700/50 p-3 rounded-lg mb-4">
        <p className="text-xs text-gray-400">
          Condition evaluates to <span className="text-green-400">true</span> (left path) or{' '}
          <span className="text-red-400">false</span> (right path).
          All conditions must be met for true. If no conditions are set, always true.
        </p>
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-1">Count Limit</label>
        <input
          type="number"
          className="input input-sm w-full"
          value={(data.count_limit as number) ?? ''}
          onChange={(e) => onChange('count_limit', e.target.value ? parseInt(e.target.value) : undefined)}
          placeholder="No limit"
          min={1}
        />
        <p className="text-xs text-gray-500 mt-1">
          True while evaluation count &lt; limit (for loops)
        </p>
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-1">Time Limit (seconds)</label>
        <input
          type="number"
          className="input input-sm w-full"
          value={(data.time_limit_seconds as number) ?? ''}
          onChange={(e) => onChange('time_limit_seconds', e.target.value ? parseInt(e.target.value) : undefined)}
          placeholder="No limit"
          min={1}
        />
        <p className="text-xs text-gray-500 mt-1">
          True while time since session start &lt; limit
        </p>
      </div>
    </>
  );
}

export default NodeConfigPanel;
