import { useState, useMemo } from 'react'
import { Box, Zap, Cpu, Cable, Hash, Search } from 'lucide-react'
import { CopyableCodeBlock, PanelSearchBox, TreeRowHeader } from './shared'
import { useSearch } from '../utils/useSearch'

// Standard library item types
type StdLibType = 'interface' | 'module' | 'component' | 'trait' | 'parameter'

// Child/field in an interface or module
// Backend uses to_frontend_dict() which converts snake_case to camelCase
interface StdLibChild {
  name: string
  type: string  // The type name (e.g., "Electrical", "ElectricLogic")
  itemType?: StdLibType  // Whether it's interface, parameter, etc.
  item_type?: StdLibType  // Backend may send snake_case.
  children?: StdLibChild[]
  enumValues?: string[] // For EnumParameter types, the possible values
}

// Helper to get item type from child
function getChildItemType(child: StdLibChild): StdLibType {
  // Backend sends camelCase via to_frontend_dict()
  return child.itemType || child.item_type || 'interface'
}

const typeConfig: Record<StdLibType, { icon: typeof Box; color: string; label: string }> = {
  interface: { icon: Cable, color: 'var(--ctp-blue)', label: 'Interface' },
  module: { icon: Box, color: 'var(--ctp-green)', label: 'Module' },
  component: { icon: Cpu, color: 'var(--ctp-mauve)', label: 'Component' },
  trait: { icon: Zap, color: 'var(--ctp-yellow)', label: 'Trait' },
  parameter: { icon: Hash, color: 'var(--ctp-peach)', label: 'Parameter' },
}

interface StdLibItem {
  id: string
  name: string
  type: StdLibType
  description: string
  usage?: string | null
  children?: StdLibChild[]  // Nested structure
  parameters?: { name: string; type: string }[]
}

interface StandardLibraryPanelProps {
  items?: StdLibItem[]
  isLoading?: boolean
  onOpenDetail?: (item: StdLibItem) => void
  onRefresh?: () => void
  isExpanded?: boolean
}

interface StdLibCardProps {
  item: StdLibItem
  isSelected: boolean
  onSelect: () => void
  expandedPaths: Set<string>
  onToggleChild: (path: string) => void
}

function StdLibCard({
  item,
  isSelected,
  onSelect,
  expandedPaths,
  onToggleChild,
}: StdLibCardProps) {
  const config = typeConfig[item.type]
  const Icon = config.icon

  const renderChild = (child: StdLibChild, path: string, depth: number = 1) => {
    const hasChildren = (child.children?.length ?? 0) > 0
    const isExpanded = expandedPaths.has(path)
    const childType = getChildItemType(child)
    const childConfig = typeConfig[childType]
    const ChildIcon = childConfig.icon

    return (
      <div key={path} className="tree-row-node">
        <TreeRowHeader
          isExpandable={hasChildren}
          isExpanded={isExpanded}
          onClick={() => (hasChildren ? onToggleChild(path) : undefined)}
          icon={<ChildIcon size={12} style={{ color: childConfig.color }} />}
          label={child.name}
          rightValue={child.type}
          depth={depth}
        />
        {hasChildren && isExpanded && (
          <div className="tree-row-children">
            {child.children!.map((subChild) =>
              renderChild(subChild, `${path}.${subChild.name}`, depth + 1)
            )}
          </div>
        )}
      </div>
    )
  }

  const hasChildren = (item.children?.length ?? 0) > 0
  const isExpandable = hasChildren || Boolean(item.description || item.usage)

  return (
    <div className={`stdlib-card${isSelected ? ' selected' : ''}`}>
      <TreeRowHeader
        className="stdlib-card-header"
        isExpandable={isExpandable}
        isExpanded={isSelected}
        onClick={onSelect}
        icon={<Icon size={12} style={{ color: config.color }} />}
        label={item.name}
        depth={1}
      />

      {/* Only show details when card is selected (expanded) */}
      {isSelected && (
        <>
          <div className="stdlib-card-description">{item.description}</div>

          {hasChildren && (
            <div className="stdlib-card-children">
              {item.children!.map((child) => renderChild(child, child.name, 2))}
            </div>
          )}

          {item.usage && (
            <div className="stdlib-card-usage">
              <CopyableCodeBlock
                label="usage.ato"
                code={item.usage}
                highlightAto
              />
            </div>
          )}
        </>
      )}
    </div>
  )
}

export function StandardLibraryPanel({
  items,
  isLoading = false,
  onOpenDetail: _onOpenDetail,
  onRefresh: _onRefresh,
  isExpanded = false,
}: StandardLibraryPanelProps) {
  const search = useSearch()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [expandedChildren, setExpandedChildren] = useState<Map<string, Set<string>>>(new Map())
  // Start with all groups collapsed by default
  const [collapsedGroups, setCollapsedGroups] = useState<Set<StdLibType>>(
    new Set(['interface', 'module', 'trait', 'component'])
  )

  const stdlibItems = items || []
  // Check if we're in search mode (has search query)
  const isSearching = search.hasQuery

  // Toggle group collapse
  const toggleGroup = (type: StdLibType) => {
    setCollapsedGroups(prev => {
      const newSet = new Set(prev)
      if (newSet.has(type)) {
        newSet.delete(type)
      } else {
        newSet.add(type)
      }
      return newSet
    })
  }

  // Toggle child expansion
  const handleToggleChild = (itemId: string, path: string) => {
    setExpandedChildren(prev => {
      const newMap = new Map(prev)
      const itemPaths = newMap.get(itemId) || new Set()
      const newPaths = new Set(itemPaths)

      if (newPaths.has(path)) {
        newPaths.delete(path)
      } else {
        newPaths.add(path)
      }

      newMap.set(itemId, newPaths)
      return newMap
    })
  }

  // Filter items using search matcher
  const filteredItems = useMemo(() => {
    if (!search.hasQuery) return stdlibItems

    const searchInChildren = (children?: StdLibChild[]): boolean => {
      if (!children) return false
      return children.some(c =>
        search.matches(c.name) ||
        search.matches(c.type) ||
        searchInChildren(c.children)
      )
    }

    return stdlibItems.filter(item =>
      search.matches(item.name) ||
      search.matches(item.description) ||
      searchInChildren(item.children)
    )
  }, [stdlibItems, search.hasQuery, search.matches])

  // Group by type for display
  const groupedItems = filteredItems.reduce((acc, item) => {
    if (!acc[item.type]) acc[item.type] = []
    acc[item.type].push(item)
    return acc
  }, {} as Record<StdLibType, StdLibItem[]>)

  const typeOrder: StdLibType[] = ['interface', 'module', 'trait', 'component']

  // Show loading state
  if (isLoading) {
    return (
      <div className="stdlib-panel">
        <PanelSearchBox
          value=""
          onChange={() => {}}
          placeholder="Search standard library..."
          enableRegex
        />
        <div className="stdlib-list">
          <div className="stdlib-loading">
            <div className="loading-spinner" />
            <span>Loading standard library...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="stdlib-panel">
      <PanelSearchBox
        value={search.query}
        onChange={search.setQuery}
        placeholder="Search standard library..."
        autoFocus={isExpanded}
        enableRegex
        isRegex={search.isRegex}
        onRegexToggle={search.setIsRegex}
      />

      {/* Items list */}
      <div className="stdlib-list">
        {isSearching ? (
          // Flat list when searching - no groups, just show all matching results
          <div className="stdlib-search-results">
            {filteredItems.length === 0 ? (
              <div className="stdlib-empty">
                <Search size={24} />
                <span>No results for "{search.query}"</span>
              </div>
            ) : (
              <>
                <div className="search-results-count">
                  {filteredItems.length} result{filteredItems.length !== 1 ? 's' : ''}
                </div>
                {filteredItems.map(item => (
                  <StdLibCard
                    key={item.id}
                    item={item}
                    isSelected={selectedId === item.id}
                    onSelect={() => setSelectedId(selectedId === item.id ? null : item.id)}
                    expandedPaths={expandedChildren.get(item.id) || new Set()}
                    onToggleChild={(path) => handleToggleChild(item.id, path)}
                  />
                ))}
              </>
            )}
          </div>
        ) : (
          // Grouped view when not searching
          typeOrder.map(type => {
            const items = groupedItems[type]
            if (!items || items.length === 0) return null

            const config = typeConfig[type]
            const Icon = config.icon
            const isCollapsed = collapsedGroups.has(type)

            return (
              <div key={type} className={`stdlib-group ${isCollapsed ? 'collapsed' : ''}`}>
                <TreeRowHeader
                  className="stdlib-group-header"
                  isExpandable={true}
                  isExpanded={!isCollapsed}
                  onClick={() => toggleGroup(type)}
                  icon={<Icon size={12} style={{ color: config.color }} />}
                  label={`${config.label}s`}
                  count={items.length}
                  depth={0}
                />
                {!isCollapsed && (
                  <div className="stdlib-group-items">
                    {items.map(item => (
                      <StdLibCard
                        key={item.id}
                        item={item}
                        isSelected={selectedId === item.id}
                        onSelect={() => setSelectedId(selectedId === item.id ? null : item.id)}
                        expandedPaths={expandedChildren.get(item.id) || new Set()}
                        onToggleChild={(path) => handleToggleChild(item.id, path)}
                      />
                    ))}
                  </div>
                )}
              </div>
            )
          })
        )}

        {filteredItems.length === 0 && (
          <div className="empty-state">
            <span>No items found</span>
            {search.hasQuery && (
              <span className="empty-hint">Try "I2C", "Resistor", or "power"</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
