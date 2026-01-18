import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { GitBranch } from 'lucide-react';
import type { ConditionNodeData } from '@/api/types';
import { NodeStatusLabel } from './NodeStatusLabel';

interface ConditionNodeProps {
  data: ConditionNodeData & {
    _nodeStatus?: string;
  };
  selected?: boolean;
}

export const ConditionNode = memo(({ data, selected }: ConditionNodeProps) => {
  return (
    <div className={`pipeline-node condition ${selected ? 'ring-2 ring-blue-500' : ''}`}>
      <Handle type="target" position={Position.Top} className="!bg-gray-500" />

      <div className="flex items-center gap-2 mb-2">
        <GitBranch className="w-4 h-4 text-yellow-400" />
        <span className="font-medium text-sm">Condition</span>
      </div>

      <div className="text-xs text-gray-400">
        {data.expression ? (
          <code className="px-1.5 py-0.5 bg-gray-700 rounded">
            {data.expression.slice(0, 30)}{data.expression.length > 30 ? '...' : ''}
          </code>
        ) : (
          <span className="text-gray-500 italic">No expression</span>
        )}
      </div>

      {/* Status label at bottom */}
      {data._nodeStatus && (
        <div className="mt-2 pt-2 border-t border-gray-700">
          <NodeStatusLabel status={data._nodeStatus} />
        </div>
      )}

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
