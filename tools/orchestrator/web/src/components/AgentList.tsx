import { useEffect, useMemo, memo, useCallback, useState, useRef } from 'react';
import { RefreshCw, Plus, Search, X, Filter } from 'lucide-react';
import { useAgents, useUIState, useDispatch, useLoading } from '@/hooks';
import { AgentCard } from './AgentCard';
import { AgentListSkeleton } from './Skeleton';
import type { AgentStatus } from '@/logic/api/types';

type StatusFilter = 'all' | AgentStatus;

interface AgentListProps {
  onSpawnClick?: () => void;
}

export const AgentList = memo(function AgentList({ onSpawnClick }: AgentListProps) {
  const dispatch = useDispatch();
  const agents = useAgents();
  const state = useUIState();
  const loading = useLoading('agents');

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [showFilters, setShowFilters] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Initial fetch - updates will come via WebSocket
    dispatch({ type: 'agents.refresh' });
  }, [dispatch]);

  // Keyboard shortcut: Cmd+K or Ctrl+K to focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
      // Escape to clear search when focused
      if (e.key === 'Escape' && document.activeElement === searchInputRef.current) {
        setSearchQuery('');
        searchInputRef.current?.blur();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const filteredAndSortedAgents = useMemo(() => {
    let filtered = [...agents];

    // Filter by status
    if (statusFilter !== 'all') {
      filtered = filtered.filter(a => a.status === statusFilter);
    }

    // Filter by search query (search in name, prompt, id, backend)
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(a =>
        (a.name && a.name.toLowerCase().includes(query)) ||
        a.prompt.toLowerCase().includes(query) ||
        a.id.toLowerCase().includes(query) ||
        a.backend.toLowerCase().includes(query)
      );
    }

    // Sort: running first, then by created_at descending
    return filtered.sort((a, b) => {
      if (a.isRunning && !b.isRunning) return -1;
      if (!a.isRunning && b.isRunning) return 1;
      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    });
  }, [agents, searchQuery, statusFilter]);

  const handleRefresh = useCallback(() => {
    dispatch({ type: 'agents.refresh' });
  }, [dispatch]);

  const handleSelect = useCallback((agentId: string) => {
    dispatch({ type: 'agents.select', payload: { agentId } });
  }, [dispatch]);

  const handleTerminate = useCallback((agentId: string) => {
    dispatch({ type: 'agents.terminate', payload: { agentId } });
  }, [dispatch]);

  const handleDelete = useCallback((agentId: string) => {
    dispatch({ type: 'agents.delete', payload: { agentId } });
  }, [dispatch]);

  const handleRename = useCallback((agentId: string, currentName?: string | null) => {
    const newName = window.prompt('Enter new name:', currentName || '');
    if (newName !== null && newName.trim() !== (currentName || '')) {
      dispatch({ type: 'agents.rename', payload: { agentId, name: newName.trim() } });
    }
  }, [dispatch]);

  const hasActiveFilters = searchQuery.trim() || statusFilter !== 'all';
  const statusOptions: { value: StatusFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'running', label: 'Running' },
    { value: 'completed', label: 'Completed' },
    { value: 'failed', label: 'Failed' },
    { value: 'terminated', label: 'Terminated' },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold">Agents</h2>
        <div className="flex items-center gap-2">
          <button
            className="btn btn-icon btn-secondary btn-sm"
            onClick={handleRefresh}
            disabled={loading}
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {onSpawnClick && (
            <button
              className="btn btn-primary btn-sm"
              onClick={onSpawnClick}
            >
              <Plus className="w-4 h-4 mr-1" />
              Spawn
            </button>
          )}
        </div>
      </div>

      {/* Search and Filter */}
      <div className="p-3 border-b border-gray-700 space-y-2">
        {/* Search input */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            ref={searchInputRef}
            type="text"
            placeholder="Search agents... (⌘K)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-8 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          {searchQuery && (
            <button
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-700 rounded"
              onClick={() => setSearchQuery('')}
            >
              <X className="w-3 h-3 text-gray-500" />
            </button>
          )}
        </div>

        {/* Filter toggle and options */}
        <div className="flex items-center gap-2">
          <button
            className={`flex items-center gap-1 px-2 py-1 text-xs rounded ${showFilters || hasActiveFilters ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter className="w-3 h-3" />
            Filters
            {hasActiveFilters && !showFilters && (
              <span className="ml-1 px-1 bg-blue-500 rounded text-[10px]">!</span>
            )}
          </button>

          {showFilters && (
            <div className="flex items-center gap-1">
              {statusOptions.map(opt => (
                <button
                  key={opt.value}
                  className={`px-2 py-1 text-xs rounded ${statusFilter === opt.value ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
                  onClick={() => setStatusFilter(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}

          {hasActiveFilters && (
            <button
              className="text-xs text-gray-500 hover:text-gray-300"
              onClick={() => {
                setSearchQuery('');
                setStatusFilter('all');
              }}
            >
              Clear all
            </button>
          )}
        </div>

        {/* Results count */}
        {hasActiveFilters && (
          <div className="text-xs text-gray-500">
            {filteredAndSortedAgents.length} of {agents.length} agents
          </div>
        )}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {loading && agents.length === 0 ? (
          <AgentListSkeleton count={3} />
        ) : filteredAndSortedAgents.length === 0 && hasActiveFilters ? (
          <div className="text-center text-gray-500 py-8">
            <p>No agents match your filters</p>
            <button
              className="text-blue-400 hover:text-blue-300 text-sm mt-2"
              onClick={() => {
                setSearchQuery('');
                setStatusFilter('all');
              }}
            >
              Clear filters
            </button>
          </div>
        ) : filteredAndSortedAgents.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <p>No agents yet</p>
            {onSpawnClick && (
              <button
                className="btn btn-primary btn-sm mt-4"
                onClick={onSpawnClick}
              >
                <Plus className="w-4 h-4 mr-1" />
                Spawn your first agent
              </button>
            )}
          </div>
        ) : (
          filteredAndSortedAgents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              selected={state.selectedAgentId === agent.id}
              onClick={() => handleSelect(agent.id)}
              onTerminate={() => handleTerminate(agent.id)}
              onDelete={() => handleDelete(agent.id)}
              onRename={() => handleRename(agent.id, agent.name)}
            />
          ))
        )}
      </div>
    </div>
  );
});

export default AgentList;
