import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getSignalColors } from '@layout-editor/colors'
import { api } from '../api/client'
import { onExtensionMessage, requestSelectionState } from '../api/vscodeApi'
import type { PinInfo, PinoutData } from '../types/build'
import { FootprintViewerCanvas } from './FootprintViewerCanvas'
import { EmptyState, PanelSearchBox } from './shared'
import './PinoutPanel.css'

type ConnectionFilter = 'all' | 'connected' | 'unconnected'
type SortKey = 'pin_number' | 'pin_name' | 'signal_type' | 'interfaces' | 'net_name'
type SortDir = 'asc' | 'desc'
type PinoutLoadState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'loaded'; report: PinoutData }

const PIN_ROW_ID_PREFIX = 'pin-row-'
const getPinRowId = (pinNumber: string) => `${PIN_ROW_ID_PREFIX}${pinNumber}`

const SORT_COLUMNS: ReadonlyArray<{ label: string; key: SortKey }> = [
  { label: 'Pin #', key: 'pin_number' },
  { label: 'Signal Name', key: 'pin_name' },
  { label: 'Signal Type', key: 'signal_type' },
  { label: 'Interfaces', key: 'interfaces' },
  { label: 'Net Name', key: 'net_name' },
]

const SORT_VALUE: Record<SortKey, (pin: PinInfo) => string> = {
  pin_number: (pin) => pin.pin_number ?? '',
  pin_name: (pin) => pin.pin_name,
  signal_type: (pin) => pin.signal_type,
  interfaces: (pin) => pin.interfaces.join(','),
  net_name: (pin) => pin.net_name ?? '',
}

function SignalBadge({ type }: { type: string }) {
  const colors = getSignalColors(type)
  return (
    <span
      className="pinout-signal-badge"
      style={{
        background: colors.badgeBg,
        color: colors.badgeFg,
      }}
    >
      {type}
    </span>
  )
}

function SortHeader({
  label,
  sortKey,
  currentSort,
  currentDir,
  onSort,
}: {
  label: string
  sortKey: SortKey
  currentSort: SortKey
  currentDir: SortDir
  onSort: (key: SortKey) => void
}) {
  const arrow = currentSort === sortKey ? (currentDir === 'asc' ? ' \u25b2' : ' \u25bc') : ''
  return (
    <th className="pinout-sort-header" onClick={() => onSort(sortKey)}>
      {label}
      {arrow}
    </th>
  )
}

function parseConnectionFilter(value: string): ConnectionFilter {
  if (value === 'all' || value === 'connected' || value === 'unconnected') return value
  throw new Error(`Unknown connection filter: ${value}`)
}

export function PinoutPanel() {
  const [selection, setSelection] = useState<{ projectRoot: string | null; targetNames: string[] }>({
    projectRoot: null,
    targetNames: [],
  })
  const [pinoutState, setPinoutState] = useState<PinoutLoadState>({ status: 'idle' })
  const [reloadToken, setReloadToken] = useState(0)
  const [selectedComponentIndex, setSelectedComponentIndex] = useState(0)
  const [search, setSearch] = useState('')
  const [filterSignalType, setFilterSignalType] = useState('all')
  const [filterConnection, setFilterConnection] = useState<ConnectionFilter>('all')
  const [sortKey, setSortKey] = useState<SortKey>('pin_number')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [hoveredPinNumber, setHoveredPinNumber] = useState<string | null>(null)
  const mousePos = useRef<{ x: number; y: number } | null>(null)

  const selectedProjectRoot = selection.projectRoot
  const selectedTargetName = selection.targetNames[0] ?? null

  useEffect(() => {
    const unsubscribe = onExtensionMessage((message) => {
      if (message.type !== 'selectionState') return
      setSelection({
        projectRoot: message.projectRoot ?? null,
        targetNames: message.targetNames ?? [],
      })
    })

    requestSelectionState()
    return unsubscribe
  }, [])

  useEffect(() => {
    setSelectedComponentIndex(0)
    setSearch('')
    setFilterSignalType('all')
    setFilterConnection('all')
    setSortKey('pin_number')
    setSortDir('asc')
    setHoveredPinNumber(null)
  }, [selectedProjectRoot, selectedTargetName])

  useEffect(() => {
    if (!selectedProjectRoot || !selectedTargetName) {
      setPinoutState({ status: 'idle' })
      return
    }

    let cancelled = false
    setPinoutState({ status: 'loading' })

    void api.pinout
      .get(selectedProjectRoot, selectedTargetName)
      .then((report) => {
        if (cancelled) return
        setPinoutState({ status: 'loaded', report })
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setPinoutState({
          status: 'error',
          message: error instanceof Error ? error.message : 'Failed to load pinout data',
        })
      })

    return () => {
      cancelled = true
    }
  }, [selectedProjectRoot, selectedTargetName, reloadToken])

  const report = pinoutState.status === 'loaded' ? pinoutState.report : null
  const component = report?.components[selectedComponentIndex] ?? null

  useEffect(() => {
    if (!report?.components.length) return
    setSelectedComponentIndex((index) => Math.min(index, report.components.length - 1))
  }, [report])

  const filteredPins = useMemo<PinInfo[]>(() => {
    if (!component) return []

    const query = search.trim().toLowerCase()
    const valueForSort = SORT_VALUE[sortKey]
    const pins = component.pins
      .filter((pin) => filterSignalType === 'all' || pin.signal_type === filterSignalType)
      .filter((pin) =>
        filterConnection === 'all' ||
        (filterConnection === 'connected' ? pin.is_connected : !pin.is_connected)
      )
      .filter((pin) =>
        !query ||
        pin.pin_name.toLowerCase().includes(query) ||
        pin.pin_number?.toLowerCase().includes(query) ||
        pin.signal_type.toLowerCase().includes(query) ||
        pin.interfaces.some((iface) => iface.toLowerCase().includes(query)) ||
        pin.net_name?.toLowerCase().includes(query) ||
        pin.notes.some((note) => note.toLowerCase().includes(query))
      )

    pins.sort((a, b) => {
      const cmp = valueForSort(a).localeCompare(valueForSort(b), undefined, { numeric: true })
      return sortDir === 'asc' ? cmp : -cmp
    })

    return pins
  }, [component, search, filterSignalType, filterConnection, sortKey, sortDir])

  const signalTypes = useMemo(() => {
    if (!component) return []
    return [...new Set(component.pins.map((pin) => pin.signal_type))].sort()
  }, [component])

  const hasFootprint = Boolean(component?.footprint_uuid)
  const totalPins = component?.pins.length ?? 0

  const emptyStateTitle = !selectedProjectRoot
    ? 'No project selected'
    : !selectedTargetName
      ? 'No target selected'
      : 'No pinout data available'
  const emptyStateDescription = !selectedProjectRoot
    ? 'Select a project in the sidebar to view pinout data.'
    : !selectedTargetName
      ? 'Select a target in the sidebar to view pinout data.'
      : 'Add the generate_pinout_details trait to a component and run ato build.'

  const handleSort = useCallback((key: SortKey) => {
    if (key === sortKey) {
      setSortDir((direction) => (direction === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(key)
    setSortDir('asc')
  }, [sortKey])

  const handleRefresh = useCallback(() => {
    setReloadToken((value) => value + 1)
  }, [])

  const handlePadClick = useCallback((padNumber: string) => {
    setHoveredPinNumber(padNumber)
    const row = document.getElementById(getPinRowId(padNumber))
    if (row) {
      row.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [])

  const updateHoverFromPoint = useCallback((x: number, y: number) => {
    const element = document.elementFromPoint(x, y)
    if (!element) {
      setHoveredPinNumber(null)
      return
    }

    const row = element.closest('tr[data-pin-number]')
    setHoveredPinNumber(row?.getAttribute('data-pin-number') ?? null)
  }, [])

  useEffect(() => {
    const onMouseMove = (event: MouseEvent) => {
      mousePos.current = { x: event.clientX, y: event.clientY }
    }

    const onWheel = () => {
      requestAnimationFrame(() => {
        if (!mousePos.current) return
        updateHoverFromPoint(mousePos.current.x, mousePos.current.y)
      })
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('wheel', onWheel, { passive: true })

    return () => {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('wheel', onWheel)
    }
  }, [updateHoverFromPoint])

  if (pinoutState.status === 'loading') {
    return (
      <div className="pinout-panel sidebar-panel">
        <EmptyState title="Loading pinout data..." />
      </div>
    )
  }

  if (pinoutState.status === 'error') {
    return (
      <div className="pinout-panel sidebar-panel">
        <EmptyState title="Error loading pinout" description={pinoutState.message} className="error" />
        <div className="pinout-error-actions">
          <button onClick={handleRefresh} className="action-btn secondary">Retry</button>
        </div>
      </div>
    )
  }

  return (
    <div className="pinout-panel sidebar-panel">
      <div className="panel-toolbar-row pinout-header">
        <h2 className="pinout-title">Pinout Table</h2>

        {report && report.components.length > 1 && (
          <div className="pinout-tabs">
            {report.components.map((entry, index) => (
              <button
                key={entry.name}
                onClick={() => setSelectedComponentIndex(index)}
                className={`action-btn secondary pinout-tab ${index === selectedComponentIndex ? 'is-active' : ''}`}
              >
                {entry.name.split('.').pop()}
              </button>
            ))}
          </div>
        )}

        {selectedProjectRoot && selectedTargetName && (
          <button onClick={handleRefresh} className="action-btn secondary" title="Refresh">Refresh</button>
        )}
      </div>

      {!report || report.components.length === 0 ? (
        <EmptyState title={emptyStateTitle} description={emptyStateDescription} />
      ) : (
        <>
          <div className="panel-toolbar-row pinout-filters">
            <div className="pinout-search-box">
              <PanelSearchBox
                value={search}
                onChange={setSearch}
                placeholder="Search pins, interfaces, notes..."
              />
            </div>

            <div className="bom-project-select">
              <select value={filterSignalType} onChange={(event) => setFilterSignalType(event.target.value)}>
                <option value="all">All types</option>
                {signalTypes.map((type) => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>

            <div className="bom-project-select">
              <select
                value={filterConnection}
                onChange={(event) => setFilterConnection(parseConnectionFilter(event.target.value))}
              >
                <option value="all">All pins</option>
                <option value="connected">Connected</option>
                <option value="unconnected">Unconnected</option>
              </select>
            </div>

            <span className="pinout-count">
              {filteredPins.length} of {totalPins} pins
            </span>
          </div>

          <div className="pinout-content">
            <div className={`pinout-table-wrap ${hasFootprint ? 'has-footprint' : 'full-width'}`}>
              <table className="pinout-table">
                <thead>
                  <tr className="pinout-head-row">
                    {SORT_COLUMNS.map((column) => (
                      <SortHeader
                        key={column.key}
                        label={column.label}
                        sortKey={column.key}
                        currentSort={sortKey}
                        currentDir={sortDir}
                        onSort={handleSort}
                      />
                    ))}
                    <th className="pinout-notes-header">Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPins.map((pin, index) => {
                    const pinNumber = pin.pin_number ?? null
                    const isHovered = pinNumber !== null && hoveredPinNumber === pinNumber
                    const rowKey = pinNumber ?? `${pin.pin_name}:${pin.net_name ?? ''}:${index}`

                    return (
                      <tr
                        key={rowKey}
                        id={pinNumber ? getPinRowId(pinNumber) : undefined}
                        data-pin-number={pinNumber ?? undefined}
                        className={`pinout-row ${isHovered ? 'is-hovered' : ''}`}
                        onMouseEnter={() => {
                          if (pinNumber) setHoveredPinNumber(pinNumber)
                        }}
                        onMouseLeave={() => {
                          setHoveredPinNumber((current) => (
                            pinNumber && current === pinNumber ? null : current
                          ))
                        }}
                      >
                        <td className="pinout-cell"><code className="pinout-dim-code">{pin.pin_number ?? '-'}</code></td>
                        <td className="pinout-cell"><code className="pinout-pin-name">{pin.pin_name}</code></td>
                        <td className="pinout-cell"><SignalBadge type={pin.signal_type} /></td>
                        <td className="pinout-cell">
                          {pin.interfaces.length > 0
                            ? pin.interfaces.map((iface, ifaceIndex) => (
                                <span key={ifaceIndex} className="pinout-interface-tag">{iface}</span>
                              ))
                            : <span className="pinout-placeholder">-</span>}
                        </td>
                        <td className="pinout-cell">
                          {pin.net_name ? <code>{pin.net_name}</code> : <span className="pinout-placeholder">-</span>}
                        </td>
                        <td className="pinout-cell">
                          {pin.notes.length > 0
                            ? pin.notes.map((note, noteIndex) => (
                                <span
                                  key={noteIndex}
                                  className={`pinout-note-tag ${note.includes('Unconnected') ? 'is-warning' : ''}`}
                                >
                                  {note}
                                </span>
                              ))
                            : <span className="pinout-placeholder">-</span>}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>

              {filteredPins.length === 0 && component && (
                <EmptyState
                  title="No pins match filters"
                  description="Adjust search or filter settings."
                  className="pinout-no-results"
                />
              )}
            </div>

            {hasFootprint && component && selectedProjectRoot && selectedTargetName && (
              <div className="pinout-footprint">
                <FootprintViewerCanvas
                  projectRoot={selectedProjectRoot}
                  targetName={selectedTargetName}
                  footprintUuid={component.footprint_uuid}
                  pins={component.pins}
                  selectedPinNumber={hoveredPinNumber}
                  onPadClick={handlePadClick}
                />
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
