import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Repeat } from 'lucide-react';
import type { LoopNodeData } from '@/api/types';
import { NodeStatusLabel } from './NodeStatusLabel';

interface LoopNodeProps {
  data: LoopNodeData & {
    _nodeStatus?: string;
    _loopIteration?: number;
  };
  selected?: boolean;
}

export const LoopNode = memo(({ data, selected }: LoopNodeProps) => {
  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h`;
  };

  return (
    <div className={`pipeline-node loop ${selected ? 'ring-2 ring-blue-500' : ''}`}>
      <Handle type="target" position={Position.Top} className="!bg-gray-500" />

      <div className="flex items-center gap-2 mb-2">
        <Repeat className="w-4 h-4 text-purple-400" />
        <span className="font-medium text-sm">Loop</span>
      </div>

      <div className="text-xs text-gray-400 space-y-1">
        <div>Duration: {formatDuration(data.duration_seconds)}</div>
        {data.max_iterations && (
          <div>Max iterations: {data.max_iterations}</div>
        )}
        <div className="flex items-center gap-2">
          {data.restart_on_complete && (
            <span className="px-1.5 py-0.5 bg-green-900/30 text-green-400 rounded">
              on complete
            </span>
          )}
          {data.restart_on_fail && (
            <span className="px-1.5 py-0.5 bg-red-900/30 text-red-400 rounded">
              on fail
            </span>
          )}
        </div>
      </div>

      {/* Loop iteration counter and status */}
      {(data._loopIteration !== undefined || data._nodeStatus) && (
        <div className="mt-2 pt-2 border-t border-gray-700 space-y-1">
          {data._loopIteration !== undefined && (
            <div className="text-xs font-medium text-purple-400">
              Iteration: {data._loopIteration}{data.max_iterations ? ` / ${data.max_iterations}` : ''}
            </div>
          )}
          {data._nodeStatus && <NodeStatusLabel status={data._nodeStatus} />}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-gray-500" />
    </div>
  );
});

LoopNode.displayName = 'LoopNode';

export default LoopNode;
