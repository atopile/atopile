import { memo, useState } from 'react';
import { ChevronDown, ChevronRight, Circle, CheckCircle2, Loader2 } from 'lucide-react';
import type { TodoItem } from '@/logic/api/types';

interface TodoListProps {
  todos: TodoItem[];
  compact?: boolean;
}

const statusIcons = {
  pending: Circle,
  in_progress: Loader2,
  completed: CheckCircle2,
};

const statusColors = {
  pending: 'text-gray-500',
  in_progress: 'text-blue-400',
  completed: 'text-green-500',
};

export const TodoList = memo(function TodoList({ todos, compact = false }: TodoListProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!todos || todos.length === 0) {
    return null;
  }

  const completedCount = todos.filter(t => t.status === 'completed').length;
  const inProgressCount = todos.filter(t => t.status === 'in_progress').length;
  const pendingCount = todos.filter(t => t.status === 'pending').length;
  const progress = Math.round((completedCount / todos.length) * 100);

  // Find the active task (in_progress) for display
  const activeTask = todos.find(t => t.status === 'in_progress');

  return (
    <div className="border-b border-gray-700 bg-gray-800/30">
      {/* Header */}
      <button
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-700/30 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )}
          <span className="text-sm font-medium text-gray-300">Tasks</span>
          <span className="text-xs text-gray-500">
            {completedCount}/{todos.length}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {/* Progress bar */}
          <div className="w-20 h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          {/* Status counts */}
          {!compact && (
            <div className="flex items-center gap-1 text-xs">
              {inProgressCount > 0 && (
                <span className="text-blue-400">{inProgressCount} active</span>
              )}
              {pendingCount > 0 && (
                <span className="text-gray-500">{pendingCount} pending</span>
              )}
            </div>
          )}
        </div>
      </button>

      {/* Active task summary (shown when collapsed) */}
      {!isExpanded && activeTask && (
        <div className="px-3 pb-2 flex items-center gap-2 text-xs">
          <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />
          <span className="text-gray-400 truncate">
            {activeTask.active_form || activeTask.content}
          </span>
        </div>
      )}

      {/* Expanded list */}
      {isExpanded && (
        <div className={`px-3 pb-2 space-y-1 ${compact ? 'max-h-32' : 'max-h-48'} overflow-y-auto`}>
          {todos.map((todo, index) => {
            const Icon = statusIcons[todo.status];
            const colorClass = statusColors[todo.status];
            const isActive = todo.status === 'in_progress';

            return (
              <div
                key={index}
                className={`flex items-start gap-2 py-1 rounded ${
                  isActive ? 'bg-blue-900/20 px-2 -mx-2' : ''
                }`}
              >
                <Icon
                  className={`w-4 h-4 mt-0.5 flex-shrink-0 ${colorClass} ${
                    isActive ? 'animate-spin' : ''
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <span
                    className={`text-sm ${
                      todo.status === 'completed'
                        ? 'text-gray-500 line-through'
                        : isActive
                        ? 'text-gray-200'
                        : 'text-gray-400'
                    }`}
                  >
                    {isActive && todo.active_form ? todo.active_form : todo.content}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
});

export default TodoList;
