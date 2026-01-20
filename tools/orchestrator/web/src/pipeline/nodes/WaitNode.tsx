import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Clock, Timer } from 'lucide-react';
import type { WaitNodeData } from '@/logic/api/types';

interface WaitNodeProps {
  data: WaitNodeData & {
    _nodeStatus?: string;
    _waitUntil?: string;  // ISO datetime when wait will end
  };
  selected?: boolean;
}

export const WaitNode = memo(({ data, selected }: WaitNodeProps) => {
  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
  };

  const formatWaitUntil = (isoDate: string) => {
    const date = new Date(isoDate);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const isWaiting = data._nodeStatus === 'waiting';

  return (
    <div className={`pipeline-node wait ${selected ? 'ring-2 ring-blue-500' : ''}`}>
      <Handle type="target" position={Position.Top} className="!bg-gray-500" />

      <div className="flex items-center gap-2 mb-2">
        <Timer className={`w-4 h-4 text-yellow-400 ${isWaiting ? 'animate-pulse' : ''}`} />
        <span className="font-medium text-sm">Wait</span>
      </div>

      <div className="text-xs text-gray-400">
        <div>Duration: {formatDuration(data.duration_seconds)}</div>
      </div>

      {/* Wait until indicator */}
      {data._waitUntil && (
        <div className="mt-2 pt-2 border-t border-gray-700">
          <div className="flex items-center gap-1.5 text-xs text-yellow-400">
            <Clock className="w-3 h-3 animate-pulse" />
            <span>Until {formatWaitUntil(data._waitUntil)}</span>
          </div>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-gray-500" />
    </div>
  );
});

WaitNode.displayName = 'WaitNode';

export default WaitNode;
