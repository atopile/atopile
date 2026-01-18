import { Loader2, CheckCircle, XCircle, Clock } from 'lucide-react';

interface NodeStatusLabelProps {
  status?: string;
  agentId?: string;
}

export function NodeStatusLabel({ status, agentId }: NodeStatusLabelProps) {
  if (!status && !agentId) return null;

  const getStatusConfig = () => {
    switch (status) {
      case 'running':
        return {
          icon: <Loader2 className="w-3 h-3 animate-spin" />,
          label: 'Running',
          className: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
        };
      case 'completed':
        return {
          icon: <CheckCircle className="w-3 h-3" />,
          label: 'Completed',
          className: 'bg-green-500/20 text-green-400 border-green-500/50',
        };
      case 'failed':
        return {
          icon: <XCircle className="w-3 h-3" />,
          label: 'Failed',
          className: 'bg-red-500/20 text-red-400 border-red-500/50',
        };
      case 'pending':
        return {
          icon: <Clock className="w-3 h-3" />,
          label: 'Pending',
          className: 'bg-gray-500/20 text-gray-400 border-gray-500/50',
        };
      default:
        if (agentId) {
          return {
            icon: <CheckCircle className="w-3 h-3" />,
            label: 'Has agent',
            className: 'bg-purple-500/20 text-purple-400 border-purple-500/50',
          };
        }
        return null;
    }
  };

  const config = getStatusConfig();
  if (!config) return null;

  return (
    <div className={`flex items-center gap-1 px-2 py-1 text-xs rounded border ${config.className}`}>
      {config.icon}
      <span>{config.label}</span>
    </div>
  );
}

export default NodeStatusLabel;
