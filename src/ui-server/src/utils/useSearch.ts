/**
 * Custom hook for managing search state with regex support
 * Provides a unified interface for all panels to use search functionality
 */

import { useState, useMemo, useCallback } from 'react'
import { createSearchMatcher, type SearchOptions } from './searchUtils'

export interface UseSearchReturn {
  /** Current search query */
  query: string
  /** Set the search query */
  setQuery: (query: string) => void
  /** Whether regex mode is enabled */
  isRegex: boolean
  /** Toggle regex mode */
  setIsRegex: (isRegex: boolean) => void
  /** Toggle regex mode (convenience function) */
  toggleRegex: () => void
  /** Search options object for passing to filter functions */
  searchOptions: SearchOptions
  /** Check if a text matches the current search */
  matches: (text: string) => boolean
  /** Whether the current query has any search term */
  hasQuery: boolean
  /** Clear the search */
  clear: () => void
}

/**
 * Hook for managing search state with optional regex support
 *
 * @example
 * const search = useSearch()
 *
 * // In your filter function:
 * const filtered = items.filter(item => search.matches(item.name))
 *
 * // In your JSX:
 * <PanelSearchBox
 *   value={search.query}
 *   onChange={search.setQuery}
 *   enableRegex
 *   isRegex={search.isRegex}
 *   onRegexToggle={search.setIsRegex}
 * />
 */
export function useSearch(initialQuery = '', initialRegex = false): UseSearchReturn {
  const [query, setQuery] = useState(initialQuery)
  const [isRegex, setIsRegex] = useState(initialRegex)

  const searchOptions = useMemo<SearchOptions>(
    () => ({ isRegex, caseSensitive: false }),
    [isRegex]
  )

  const matcher = useMemo(
    () => createSearchMatcher(query, searchOptions),
    [query, searchOptions]
  )

  const matches = useCallback(
    (text: string) => matcher(text).matches,
    [matcher]
  )

  const toggleRegex = useCallback(() => {
    setIsRegex(prev => !prev)
  }, [])

  const clear = useCallback(() => {
    setQuery('')
  }, [])

  const hasQuery = query.trim().length > 0

  return {
    query,
    setQuery,
    isRegex,
    setIsRegex,
    toggleRegex,
    searchOptions,
    matches,
    hasQuery,
    clear,
  }
}
