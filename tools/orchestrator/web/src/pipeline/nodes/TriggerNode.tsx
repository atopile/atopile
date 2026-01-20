import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Play, Clock, Webhook } from 'lucide-react';
import type { TriggerNodeData } from '@/logic/api/types';

interface TriggerNodeProps {
  data: TriggerNodeData;
  selected?: boolean;
}

export const TriggerNode = memo(({ data, selected }: TriggerNodeProps) => {
  const getIcon = () => {
    switch (data.trigger_type) {
      case 'timer':
        return <Clock className="w-4 h-4 text-blue-400" />;
      case 'webhook':
        return <Webhook className="w-4 h-4 text-blue-400" />;
      default:
        return <Play className="w-4 h-4 text-blue-400" />;
    }
  };

  const getLabel = () => {
    switch (data.trigger_type) {
      case 'timer':
        return data.interval_seconds
          ? `Every ${data.interval_seconds}s`
          : data.cron_expression || 'Timer';
      case 'webhook':
        return 'Webhook';
      default:
        return 'Manual Start';
    }
  };

  return (
    <div className={`pipeline-node trigger ${selected ? 'ring-2 ring-blue-500' : ''}`}>
      <div className="flex items-center gap-2 mb-2">
        {getIcon()}
        <span className="font-medium text-sm">Trigger</span>
      </div>

      <div className="text-xs text-gray-400">
        <span className="px-1.5 py-0.5 bg-gray-700 rounded">{data.trigger_type}</span>
      </div>

      <div className="mt-2 text-xs text-gray-500">
        {getLabel()}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-gray-500" />
    </div>
  );
});

TriggerNode.displayName = 'TriggerNode';

export default TriggerNode;
