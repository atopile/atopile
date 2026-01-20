import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { GitBranch, Hash, Clock } from 'lucide-react';
import type { ConditionNodeData } from '@/logic/api/types';

interface ConditionNodeProps {
  data: ConditionNodeData & {
    _nodeStatus?: string;
    _conditionCount?: number;
  };
  selected?: boolean;
}

export const ConditionNode = memo(({ data, selected }: ConditionNodeProps) => {
  const hasConditions = data.count_limit !== undefined || data.time_limit_seconds !== undefined;

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h`;
  };

  return (
    <div className={`pipeline-node condition ${selected ? 'ring-2 ring-blue-500' : ''}`}>
      <Handle type="target" position={Position.Top} className="!bg-gray-500" />

      <div className="flex items-center gap-2 mb-2">
        <GitBranch className="w-4 h-4 text-cyan-400" />
        <span className="font-medium text-sm">Condition</span>
      </div>

      <div className="text-xs text-gray-400 space-y-1">
        {!hasConditions && (
          <span className="text-gray-500 italic">Always true</span>
        )}
        {data.count_limit !== undefined && (
          <div className="flex items-center gap-1.5">
            <Hash className="w-3 h-3" />
            <span>Count &lt; {data.count_limit}</span>
          </div>
        )}
        {data.time_limit_seconds !== undefined && (
          <div className="flex items-center gap-1.5">
            <Clock className="w-3 h-3" />
            <span>Time &lt; {formatDuration(data.time_limit_seconds)}</span>
          </div>
        )}
      </div>

      {/* Current count display */}
      {data._conditionCount !== undefined && (
        <div className="mt-2 pt-2 border-t border-gray-700">
          <div className="text-xs text-cyan-400">
            Count: {data._conditionCount}{data.count_limit ? ` / ${data.count_limit}` : ''}
          </div>
        </div>
      )}

      {/* Branch labels */}
      <div className="flex justify-between text-[10px] text-gray-500 mt-2 px-1">
        <span className="text-green-400">✓</span>
        <span className="text-red-400">✗</span>
      </div>

      {/* Multiple output handles for branches */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="true"
        className="!bg-green-500 !left-1/3"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="false"
        className="!bg-red-500 !left-2/3"
      />
    </div>
  );
});

ConditionNode.displayName = 'ConditionNode';

export default ConditionNode;
