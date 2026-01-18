import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Bot, FileText } from 'lucide-react';
import type { AgentNodeData } from '@/logic/api/types';
import { NodeStatusLabel } from './NodeStatusLabel';

interface AgentNodeProps {
  data: AgentNodeData & {
    _nodeStatus?: string;
    _agentId?: string;
  };
  selected?: boolean;
}

export const AgentNode = memo(({ data, selected }: AgentNodeProps) => {
  return (
    <div className={`pipeline-node agent ${selected ? 'ring-2 ring-blue-500' : ''}`}>
      <Handle type="target" position={Position.Top} className="!bg-gray-500" />

      <div className="flex items-center gap-2 mb-2">
        <Bot className="w-4 h-4 text-green-400" />
        <span className="font-medium text-sm">{data.name || 'Agent'}</span>
      </div>

      <div className="text-xs text-gray-400 space-y-1">
        <div className="flex items-center gap-1">
          <span className="px-1.5 py-0.5 bg-gray-700 rounded">{data.backend}</span>
        </div>
        {data.max_turns && (
          <div>Max turns: {data.max_turns}</div>
        )}
        {data.planning_file && (
          <div className="flex items-center gap-1 text-blue-400">
            <FileText className="w-3 h-3" />
            <span>Has planning file</span>
          </div>
        )}
      </div>

      {data.prompt && (
        <div className="mt-2 pt-2 border-t border-gray-700">
          <p className="text-xs text-gray-500 truncate" title={data.prompt}>
            {data.prompt.slice(0, 50)}...
          </p>
        </div>
      )}

      {/* Status label at bottom */}
      <div className="mt-2 pt-2 border-t border-gray-700">
        <NodeStatusLabel status={data._nodeStatus} agentId={data._agentId} />
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-gray-500" />
    </div>
  );
});

AgentNode.displayName = 'AgentNode';

export default AgentNode;
