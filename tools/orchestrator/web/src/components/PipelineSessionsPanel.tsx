import { useEffect, useState, useCallback } from 'react';
import { Square, Trash2, RefreshCw, Clock, CheckCircle, XCircle, StopCircle } from 'lucide-react';
import { useDispatch, useUIState, usePipelineSessions } from '@/hooks';
import { StatusBadge } from './StatusBadge';

interface PipelineSessionsPanelProps {
  pipelineId: string;
  onClose?: () => void;
}

export function PipelineSessionsPanel({ pipelineId, onClose }: PipelineSessionsPanelProps) {
  const dispatch = useDispatch();
  const state = useUIState();
  const sessions = usePipelineSessions(pipelineId);
  const selectedSessionId = state.selectedSessionId;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      await dispatch({ type: 'sessions.fetch', payload: { pipelineId } });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  }, [dispatch, pipelineId]);

  useEffect(() => {
    // Initial fetch - updates will come via WebSocket
    fetchSessions();
  }, [fetchSessions]);

  const handleStop = useCallback(async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      setActionInProgress(sessionId);
      await dispatch({ type: 'sessions.stop', payload: { pipelineId, sessionId, force: true } });
      await fetchSessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop session');
    } finally {
      setActionInProgress(null);
    }
  }, [dispatch, pipelineId, fetchSessions]);

  const handleDelete = useCallback(async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      setActionInProgress(sessionId);
      await dispatch({ type: 'sessions.delete', payload: { pipelineId, sessionId, force: true } });
      if (selectedSessionId === sessionId) {
        dispatch({ type: 'sessions.select', payload: { sessionId: null } });
      }
      await fetchSessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete session');
    } finally {
      setActionInProgress(null);
    }
  }, [dispatch, pipelineId, selectedSessionId, fetchSessions]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Clock className="w-4 h-4 text-blue-400 animate-pulse" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'stopped':
        return <StopCircle className="w-4 h-4 text-yellow-400" />;
      default:
        return null;
    }
  };

  const formatTime = (dateStr: string | undefined | null) => {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return '—';
    return date.toLocaleTimeString();
  };

  const formatDuration = (startStr: string | undefined | null, endStr: string | undefined | null, isRunning: boolean) => {
    if (!startStr) return '—';
    const start = new Date(startStr).getTime();
    if (isNaN(start)) return '—';

    // Only use Date.now() for actively running sessions
    let end: number;
    if (endStr) {
      end = new Date(endStr).getTime();
      if (isNaN(end)) return '—';
    } else if (isRunning) {
      end = Date.now();
    } else {
      return '—'; // Finished but no end time - something is wrong
    }

    const durationMs = end - start;
    const seconds = Math.floor(durationMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-900 border-l border-gray-700">
      <div className="flex items-center justify-between p-3 border-b border-gray-700">
        <h3 className="font-semibold text-sm">Pipeline Sessions</h3>
        <div className="flex items-center gap-2">
          <button
            className="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-gray-200"
            onClick={fetchSessions}
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          {onClose && (
            <button
              className="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-gray-200"
              onClick={onClose}
            >
              ×
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="px-3 py-2 bg-red-900/20 border-b border-red-800 text-red-400 text-xs">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {loading && sessions.length === 0 ? (
          <div className="flex items-center justify-center p-8 text-gray-500">
            Loading sessions...
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex items-center justify-center p-8 text-gray-500">
            No sessions yet
          </div>
        ) : (
          <div className="p-2 space-y-2">
            {sessions.map((session) => {
              const isSelected = selectedSessionId === session.id;
              const isRunning = session.status === 'running';
              return (
                <div
                  key={session.id}
                  className={`card p-3 cursor-pointer transition-all ${
                    isSelected ? 'ring-2 ring-blue-500' : 'hover:border-gray-600'
                  } ${actionInProgress === session.id ? 'opacity-50' : ''}`}
                  onClick={() => dispatch({ type: 'sessions.select', payload: { sessionId: session.id } })}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(session.status)}
                      <span className="text-xs font-mono text-gray-400">
                        {session.id.slice(0, 8)}
                      </span>
                    </div>
                    <StatusBadge status={session.status} size="sm" />
                  </div>

                  <div className="text-xs text-gray-500 mb-2">
                    <div className="flex justify-between">
                      <span>Started:</span>
                      <span>{formatTime(session.startedAt)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Duration:</span>
                      <span>{formatDuration(session.startedAt, session.finishedAt, session.status === 'running')}</span>
                    </div>
                  </div>

                  {/* Node status */}
                  <div className="text-xs mb-2">
                    <div className="text-gray-500 mb-1">Nodes:</div>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(session.nodeStatus).map(([nodeId, status]) => (
                        <span
                          key={nodeId}
                          className={`px-1.5 py-0.5 rounded text-xs ${
                            status === 'completed'
                              ? 'bg-green-900/30 text-green-400'
                              : status === 'running'
                              ? 'bg-blue-900/30 text-blue-400'
                              : status === 'failed'
                              ? 'bg-red-900/30 text-red-400'
                              : 'bg-gray-700 text-gray-400'
                          }`}
                        >
                          {nodeId.split('-')[0]}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-1">
                    {isRunning && (
                      <button
                        className="p-1 hover:bg-gray-700 rounded transition-colors"
                        onClick={(e) => handleStop(session.id, e)}
                        disabled={actionInProgress === session.id}
                        title="Stop"
                      >
                        <Square className="w-3.5 h-3.5 text-red-400" />
                      </button>
                    )}
                    {!isRunning && (
                      <button
                        className="p-1 hover:bg-gray-700 rounded transition-colors"
                        onClick={(e) => handleDelete(session.id, e)}
                        disabled={actionInProgress === session.id}
                        title="Delete"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-gray-400 hover:text-red-400" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default PipelineSessionsPanel;
