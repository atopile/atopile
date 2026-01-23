import { useState } from 'react'
import {
  ChevronDown, ChevronRight, Search, Box, Zap, Cpu,
  Cable, Copy, Hash
} from 'lucide-react'

// Standard library item types
type StdLibType = 'interface' | 'module' | 'component' | 'trait' | 'parameter'

// Child/field in an interface or module
// Backend uses to_frontend_dict() which converts snake_case to camelCase
interface StdLibChild {
  name: string
  type: string  // The type name (e.g., "Electrical", "ElectricLogic")
  itemType?: StdLibType  // Whether it's interface, parameter, etc.
  children?: StdLibChild[]
  enumValues?: string[] // For EnumParameter types, the possible values
}

// Helper to get item type from child
function getChildItemType(child: StdLibChild): StdLibType {
  // Backend sends camelCase via to_frontend_dict()
  return child.itemType || 'interface'
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

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
    } catch (error) {
      console.warn('Failed to copy usage text', error)
    }
  }

  const renderChild = (child: StdLibChild, path: string) => {
    const hasChildren = (child.children?.length ?? 0) > 0
    const isExpanded = expandedPaths.has(path)
    const childType = getChildItemType(child)
    const childConfig = typeConfig[childType]
    const ChildIcon = childConfig.icon

    return (
      <div key={path} className="stdlib-child-node">
        <div
          className={`stdlib-child-row${hasChildren ? ' expandable' : ''}`}
          onClick={() => (hasChildren ? onToggleChild(path) : undefined)}
        >
          {hasChildren ? (
            <button className="expand-btn" onClick={() => onToggleChild(path)}>
              {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            </button>
          ) : (
            <span className="expand-spacer" />
          )}
          <span className="stdlib-child-icon" style={{ color: childConfig.color }}>
            <ChildIcon size={12} />
          </span>
          <span className="stdlib-child-name">{child.name}</span>
          <span className="stdlib-child-type">{child.type}</span>
        </div>
        {hasChildren && isExpanded && (
          <div className="stdlib-child-children">
            {child.children!.map((subChild) =>
              renderChild(subChild, `${path}.${subChild.name}`)
            )}
          </div>
        )}
      </div>
    )
  }

  const hasChildren = (item.children?.length ?? 0) > 0

  return (
    <div className={`stdlib-card${isSelected ? ' selected' : ''}`} onClick={onSelect}>
      <div className="stdlib-card-header">
        {hasChildren && (
          <span className="stdlib-expand-icon">
            {isSelected ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </span>
        )}
        <span className="stdlib-type-icon" style={{ color: config.color }}>
          <Icon size={14} />
        </span>
        <span className="stdlib-card-name">{item.name}</span>
        <span className="stdlib-type-badge" style={{ background: config.color, color: 'var(--ctp-base)' }}>
          {config.label}
        </span>
      </div>

      {/* Only show details when card is selected (expanded) */}
      {isSelected && (
        <>
          <div className="stdlib-card-description">{item.description}</div>

          {hasChildren && (
            <div className="stdlib-card-children">
              {item.children!.map((child) => renderChild(child, child.name))}
            </div>
          )}

          {item.usage && (
            <div className="stdlib-card-usage">
              <div className="usage-header">
                <span>Usage</span>
                <button className="copy-btn" onClick={(e) => {
                  e.stopPropagation()
                  handleCopy(item.usage || '')
                }} title="Copy to clipboard">
                  <Copy size={12} />
                </button>
              </div>
              <pre className="usage-code">{item.usage}</pre>
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
}: StandardLibraryPanelProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [expandedChildren, setExpandedChildren] = useState<Map<string, Set<string>>>(new Map())
  // Start with all groups collapsed by default
  const [collapsedGroups, setCollapsedGroups] = useState<Set<StdLibType>>(
    new Set(['interface', 'module', 'trait', 'component'])
  )
  
  const stdlibItems = items || []
  // Check if we're in search mode (has search query)
  const isSearching = searchQuery.trim().length > 0
  
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
  
  // Filter items
  const filteredItems = stdlibItems.filter(item => {
    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const searchInChildren = (children?: StdLibChild[]): boolean => {
        if (!children) return false
        return children.some(c => 
          c.name.toLowerCase().includes(query) ||
          c.type.toLowerCase().includes(query) ||
          searchInChildren(c.children)
        )
      }
      
      return (
        item.name.toLowerCase().includes(query) ||
        item.description.toLowerCase().includes(query) ||
        searchInChildren(item.children)
      )
    }
    
    return true
  })
  
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
        <div className="stdlib-toolbar">
          <div className="search-box">
            <Search size={12} />
            <input 
              type="text"
              placeholder="Search standard library..."
              disabled
            />
          </div>
        </div>
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
      {/* Search and filters */}
      <div className="stdlib-toolbar">
        <div className="search-box">
          <Search size={12} />
          <input 
            type="text"
            placeholder="Search standard library..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>
      
      {/* Items list */}
      <div className="stdlib-list">
        {isSearching ? (
          // Flat list when searching - no groups, just show all matching results
          <div className="stdlib-search-results">
            {filteredItems.length === 0 ? (
              <div className="stdlib-empty">
                <Search size={24} />
                <span>No results for "{searchQuery}"</span>
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
                <button 
                  className="stdlib-group-header"
                  onClick={() => toggleGroup(type)}
                  style={{ '--group-color': config.color } as React.CSSProperties}
                >
                  <span className="group-chevron">
                    {isCollapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
                  </span>
                  <span className="group-icon" style={{ color: config.color }}>
                    <Icon size={12} />
                  </span>
                  <span className="group-label">{config.label}s</span>
                  <span className="group-count">({items.length})</span>
                </button>
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
            {searchQuery && (
              <span className="empty-hint">Try "I2C", "Resistor", or "power"</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
