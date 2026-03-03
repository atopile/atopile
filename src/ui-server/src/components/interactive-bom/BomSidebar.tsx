import { useCallback, useEffect, useRef, useMemo } from 'react';
import { RegexSearchBar } from '../shared/SearchBar';
import { BomRow } from './BomRow';
import { ComponentDetailPanel } from './ComponentDetailPanel';
import { useInteractiveBomStore } from './useInteractiveBomStore';
import { createSearchMatcher } from '../../utils/searchUtils';
import type { BomGroup } from './types';

export function BomSidebar() {
  const bomGroups = useInteractiveBomStore((s) => s.bomGroups);
  const selectedGroupId = useInteractiveBomStore((s) => s.selectedGroupId);
  const hoveredGroupId = useInteractiveBomStore((s) => s.hoveredGroupId);
  const searchQuery = useInteractiveBomStore((s) => s.searchQuery);
  const isRegex = useInteractiveBomStore((s) => s.isRegex);
  const caseSensitive = useInteractiveBomStore((s) => s.caseSensitive);
  const bomEnrichment = useInteractiveBomStore((s) => s.bomEnrichment);
  const setSelectedGroup = useInteractiveBomStore((s) => s.setSelectedGroup);
  const setHoveredGroup = useInteractiveBomStore((s) => s.setHoveredGroup);
  const setSearchQuery = useInteractiveBomStore((s) => s.setSearchQuery);
  const setIsRegex = useInteractiveBomStore((s) => s.setIsRegex);
  const setCaseSensitive = useInteractiveBomStore((s) => s.setCaseSensitive);

  const listRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const rowRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const selectedIndexRef = useRef<number>(-1);

  const filteredGroups = useMemo(() => {
    if (!searchQuery.trim()) return bomGroups;
    const matcher = createSearchMatcher(searchQuery, { isRegex, caseSensitive });
    return bomGroups.filter((group) => {
      const firstDes = group.designators[0];
      const enrichment = firstDes ? bomEnrichment.get(firstDes) : undefined;
      const searchText = [
        ...group.designators,
        enrichment?.mpn ?? '',
      ].join(' ');
      return matcher(searchText).matches;
    });
  }, [bomGroups, searchQuery, isRegex, caseSensitive, bomEnrichment]);

  const totalComponents = useMemo(
    () => bomGroups.reduce((sum, g) => sum + g.quantity, 0),
    [bomGroups]
  );

  // Auto-scroll to selected row when selection changes from viewer
  useEffect(() => {
    if (!selectedGroupId) return;
    const rowEl = rowRefs.current.get(selectedGroupId);
    if (rowEl) {
      rowEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [selectedGroupId]);

  // Update selectedIndexRef when selection changes
  useEffect(() => {
    if (!selectedGroupId) {
      selectedIndexRef.current = -1;
      return;
    }
    const idx = filteredGroups.findIndex((g) => g.id === selectedGroupId);
    selectedIndexRef.current = idx;
  }, [selectedGroupId, filteredGroups]);

  const handleSelect = useCallback(
    (groupId: string) => {
      setSelectedGroup(groupId === selectedGroupId ? null : groupId);
    },
    [setSelectedGroup, selectedGroupId]
  );

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInSearch =
        target.tagName === 'INPUT' || target.tagName === 'TEXTAREA';

      if (e.key === '/' && !isInSearch) {
        e.preventDefault();
        setIsRegex(true);
        setCaseSensitive(true);
        searchRef.current?.focus();
        return;
      }

      if (e.key === 'Escape' && isInSearch) {
        (target as HTMLInputElement).blur();
        return;
      }

      if (isInSearch) return;

      if (e.key === 'j' || e.key === 'k') {
        e.preventDefault();
        const len = filteredGroups.length;
        if (len === 0) return;
        let idx = selectedIndexRef.current;
        if (e.key === 'j') {
          idx = idx < len - 1 ? idx + 1 : 0;
        } else {
          idx = idx > 0 ? idx - 1 : len - 1;
        }
        const group = filteredGroups[idx];
        if (group) {
          setSelectedGroup(group.id);
        }
        return;
      }

      if (e.key === 'Escape') {
        setSelectedGroup(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [filteredGroups, setSelectedGroup]);

  const selectedGroup = selectedGroupId
    ? bomGroups.find((g) => g.id === selectedGroupId) ?? null
    : null;

  const selectedEnrichment = selectedGroup
    ? (() => {
        const firstDesignator = selectedGroup.designators[0];
        return firstDesignator ? bomEnrichment.get(firstDesignator) ?? null : null;
      })()
    : null;

  const setRowRef = useCallback(
    (groupId: string) => (el: HTMLDivElement | null) => {
      if (el) {
        rowRefs.current.set(groupId, el);
      } else {
        rowRefs.current.delete(groupId);
      }
    },
    []
  );

  return (
    <div className="ibom-sidebar">
      <div className="ibom-sidebar-header">
        <div className="ibom-summary">
          <span>{bomGroups.length} groups</span>
          <span className="ibom-summary-sep">&middot;</span>
          <span>{totalComponents} components</span>
        </div>
        <RegexSearchBar
          ref={searchRef}
          value={searchQuery}
          onChange={setSearchQuery}
          isRegex={isRegex}
          onRegexChange={setIsRegex}
          caseSensitive={caseSensitive}
          onCaseSensitiveChange={setCaseSensitive}
          placeholder="Filter components..."
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              if (filteredGroups.length > 0) {
                setSelectedGroup(filteredGroups[0]!.id);
              }
              (e.target as HTMLInputElement).blur();
            }
          }}
        />
      </div>

      <div className="ibom-list-header">
        <span className="ibom-row-qty">Qty</span>
        <span className="ibom-row-designators">Designators</span>
        <span className="ibom-row-value">Value</span>
      </div>

      <div className="ibom-list" ref={listRef}>
        {filteredGroups.length === 0 ? (
          <div className="ibom-empty">
            {bomGroups.length === 0 ? 'No components loaded' : 'No matches'}
          </div>
        ) : (
          filteredGroups.map((group: BomGroup) => {
            const firstDes = group.designators[0];
            const rowEnrichment = firstDes ? bomEnrichment.get(firstDes) ?? null : null;
            return (
              <div key={group.id} ref={setRowRef(group.id)}>
                <BomRow
                  group={group}
                  enrichment={rowEnrichment}
                  isSelected={selectedGroupId === group.id}
                  isHovered={hoveredGroupId === group.id}
                  onSelect={handleSelect}
                  onHover={setHoveredGroup}
                />
              </div>
            );
          })
        )}
      </div>

      {selectedGroup && (
        <ComponentDetailPanel
          group={selectedGroup}
          enrichment={selectedEnrichment}
        />
      )}
    </div>
  );
}
