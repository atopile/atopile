import { useState, useEffect, useRef, useCallback, useImperativeHandle, forwardRef } from 'react';
import { Folder, FileText, ChevronRight } from 'lucide-react';
import { useLogic } from '@/hooks';
import type { PathSuggestion } from '@/logic/api/types';

export interface PathAutocompleteHandle {
  handleKeyDown: (e: KeyboardEvent) => boolean; // Returns true if the event was handled
}

interface PathAutocompleteProps {
  /** The current query after @ */
  query: string;
  /** Position where the dropdown should appear */
  position: { top: number; left: number };
  /** Called when a path is selected */
  onSelect: (path: string) => void;
  /** Called when the autocomplete should be dismissed */
  onDismiss: () => void;
  /** Base path for relative path resolution */
  basePath?: string;
  /** Only show directories */
  directoriesOnly?: boolean;
  /** Whether the dropdown is visible */
  visible: boolean;
}

export const PathAutocomplete = forwardRef<PathAutocompleteHandle, PathAutocompleteProps>(function PathAutocomplete({
  query,
  position,
  onSelect,
  onDismiss,
  basePath,
  directoriesOnly = false,
  visible,
}, ref) {
  const logic = useLogic();
  const [suggestions, setSuggestions] = useState<PathSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Fetch suggestions when query changes
  useEffect(() => {
    console.log('[PathAutocomplete] useEffect triggered, query:', JSON.stringify(query), 'visible:', visible);

    if (!visible) {
      setSuggestions([]);
      return;
    }

    // Create a new abort controller for this specific request
    const abortController = new AbortController();

    const fetchSuggestions = async () => {
      console.log('[PathAutocomplete] Fetching suggestions for query:', JSON.stringify(query));
      setLoading(true);
      setError(null);

      try {
        const response = await logic.api.filesystem.completePath({
          query,
          basePath,
          directoriesOnly,
          limit: 15,
        });
        console.log('[PathAutocomplete] Got response:', response.suggestions.length, 'suggestions');

        // Only update if not aborted
        if (!abortController.signal.aborted) {
          setSuggestions(response.suggestions);
          setSelectedIndex(0);
        }
      } catch (err) {
        // Only handle errors if not aborted
        if (!abortController.signal.aborted) {
          if (err instanceof Error && err.name !== 'AbortError') {
            console.error('Failed to fetch path suggestions:', err);
            const errorMsg = err instanceof Error ? err.message : 'Unknown error';
            setError(errorMsg.includes('404') ? 'API endpoint not found - restart server' : 'Failed to load suggestions');
            setSuggestions([]);
          }
        }
      } finally {
        if (!abortController.signal.aborted) {
          setLoading(false);
        }
      }
    };

    // Debounce the fetch - shorter delay for snappier feel
    const timer = setTimeout(fetchSuggestions, 50);

    return () => {
      clearTimeout(timer);
      abortController.abort();
    };
  }, [query, basePath, directoriesOnly, visible, logic.api]);

  // Handle keyboard navigation - returns true if the event was handled
  const handleKeyDown = useCallback(
    (e: KeyboardEvent): boolean => {
      if (!visible) return false;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          if (suggestions.length > 0) {
            setSelectedIndex((prev) => (prev + 1) % suggestions.length);
          }
          return true;
        case 'ArrowUp':
          e.preventDefault();
          if (suggestions.length > 0) {
            setSelectedIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length);
          }
          return true;
        case 'Enter':
        case 'Tab':
          e.preventDefault();
          if (suggestions.length > 0) {
            const selected = suggestions[selectedIndex];
            if (selected) {
              // If it's a directory, append / to continue navigation
              const path = selected.is_directory ? selected.path + '/' : selected.path;
              onSelect(path);
            }
          }
          return true;
        case 'Escape':
          e.preventDefault();
          onDismiss();
          return true;
        default:
          return false;
      }
    },
    [visible, suggestions, selectedIndex, onSelect, onDismiss]
  );

  // Expose the handleKeyDown method via ref
  useImperativeHandle(ref, () => ({
    handleKeyDown,
  }), [handleKeyDown]);

  // Add global keyboard listener when visible
  useEffect(() => {
    if (!visible) return;

    const listener = (e: KeyboardEvent) => {
      handleKeyDown(e);
    };

    // Use capture phase to intercept before other handlers
    document.addEventListener('keydown', listener, true);
    return () => {
      document.removeEventListener('keydown', listener, true);
    };
  }, [visible, handleKeyDown]);

  // Scroll selected item into view
  useEffect(() => {
    if (containerRef.current && suggestions.length > 0) {
      const selectedElement = containerRef.current.querySelector(`[data-index="${selectedIndex}"]`);
      selectedElement?.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex, suggestions.length]);

  if (!visible) return null;

  return (
    <div
      ref={containerRef}
      className="fixed z-50 bg-gray-800 border border-gray-600 rounded-lg shadow-xl max-h-64 overflow-y-auto min-w-[280px] max-w-[400px]"
      style={{
        top: position.top,
        left: position.left,
      }}
    >
      {/* Header showing current path */}
      {query && (
        <div className="px-3 py-1.5 text-xs text-gray-400 border-b border-gray-700 bg-gray-850 truncate">
          <span className="text-blue-400">@</span>
          {query}
        </div>
      )}

      {/* Loading state */}
      {loading && suggestions.length === 0 && (
        <div className="px-3 py-2 text-sm text-gray-400">
          Loading...
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="px-3 py-2 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && suggestions.length === 0 && (
        <div className="px-3 py-2 text-sm text-gray-500">
          No matches found
        </div>
      )}

      {/* Suggestions list */}
      {suggestions.length > 0 && (
        <ul className="py-1">
          {suggestions.map((suggestion, index) => (
            <li
              key={suggestion.path}
              data-index={index}
              className={`flex items-center gap-2 px-3 py-1.5 cursor-pointer ${
                index === selectedIndex
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-200 hover:bg-gray-700'
              }`}
              onClick={() => {
                const path = suggestion.is_directory ? suggestion.path + '/' : suggestion.path;
                onSelect(path);
              }}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              {/* Icon */}
              {suggestion.is_directory ? (
                <Folder className="w-4 h-4 flex-shrink-0 text-yellow-400" />
              ) : (
                <FileText className="w-4 h-4 flex-shrink-0 text-gray-400" />
              )}

              {/* Name */}
              <span className="truncate flex-1 text-sm font-mono">
                {suggestion.name}
              </span>

              {/* Directory indicator */}
              {suggestion.is_directory && (
                <ChevronRight className="w-3 h-3 flex-shrink-0 opacity-50" />
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Help text */}
      <div className="px-3 py-1.5 text-[10px] text-gray-500 border-t border-gray-700 bg-gray-850">
        <kbd className="px-1 py-0.5 bg-gray-700 rounded text-gray-400">↑↓</kbd> navigate
        {' · '}
        <kbd className="px-1 py-0.5 bg-gray-700 rounded text-gray-400">Tab</kbd> select
        {' · '}
        <kbd className="px-1 py-0.5 bg-gray-700 rounded text-gray-400">Esc</kbd> close
      </div>
    </div>
  );
});

export default PathAutocomplete;
