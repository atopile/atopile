import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { api } from '../api/client'
import type { PinoutData, PinInfo } from '../types/build'
import { FootprintViewerCanvas } from './FootprintViewerCanvas'
import { getSignalColors } from '@layout-editor/colors'
import { EmptyState, PanelSearchBox } from './shared'
import { onExtensionMessage, requestSelectionState } from '../api/vscodeApi'
import './PinoutPanel.css'

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

// ---------------------------------------------------------------------------
//  Sortable header
// ---------------------------------------------------------------------------

type SortKey = 'pin_number' | 'pin_name' | 'signal_type' | 'interfaces' | 'connected_to' | 'net_name'
type SortDir = 'asc' | 'desc'
type ConnectionFilter = 'all' | 'connected' | 'unconnected'
type PinoutState =
  | { status: 'idle' }
  | { status: 'loading'; selectionKey: string }
  | { status: 'error'; selectionKey: string; message: string }
  | { status: 'loaded'; selectionKey: string; report: PinoutData }

const PIN_ROW_ID_PREFIX = 'pin-row-'
const getPinRowId = (pinNumber: string) => `${PIN_ROW_ID_PREFIX}${pinNumber}`
const parseConnectionFilter = (value: string): ConnectionFilter => {
  if (value === 'all' || value === 'connected' || value === 'unconnected') return value
  throw new Error(`Unknown connection filter: ${value}`)
}

const SORT_COLUMNS: ReadonlyArray<{ label: string; key: SortKey }> = [
  { label: 'Pin #', key: 'pin_number' },
  { label: 'Signal Name', key: 'pin_name' },
  { label: 'Signal Type', key: 'signal_type' },
  { label: 'Interfaces', key: 'interfaces' },
  { label: 'Connected To', key: 'connected_to' },
  { label: 'Net Name', key: 'net_name' },
]
const SORT_VALUE: Record<SortKey, (pin: PinInfo) => string> = {
  pin_number: pin => pin.pin_number ?? '',
  pin_name: pin => pin.pin_name,
  signal_type: pin => pin.signal_type,
  interfaces: pin => pin.interfaces.join(','),
  connected_to: pin => pin.connected_to.join(','),
  net_name: pin => pin.net_name ?? '',
}

function SortHeader({ label, sortKey, currentSort, currentDir, onSort }: {
  label: string
  sortKey: SortKey
  currentSort: SortKey
  currentDir: SortDir
  onSort: (key: SortKey) => void
}) {
  const arrow = currentSort === sortKey ? (currentDir === 'asc' ? ' \u25b2' : ' \u25bc') : ''
  return (
    <th
      className="pinout-sort-header"
      onClick={() => onSort(sortKey)}
    >
      {label}{arrow}
    </th>
  )
}

// ---------------------------------------------------------------------------
//  Main component
// ---------------------------------------------------------------------------

export function PinoutPanel() {
  const [selection, setSelection] = useState<{ projectRoot: string | null; targetNames: string[] }>({
    projectRoot: null,
    targetNames: [],
  })
  const selectedProjectRoot = selection.projectRoot
  const selectedTargetName = selection.targetNames[0] ?? null
  const selectionKey = selectedProjectRoot && selectedTargetName
    ? `${selectedProjectRoot}::${selectedTargetName}`
    : null
  const [pinoutState, setPinoutState] = useState<PinoutState>({ status: 'idle' })
  const [selectedComp, setSelectedComp] = useState(0)
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('pin_number')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [hoveredPinNumber, setHoveredPinNumber] = useState<string | null>(null)
  const [filterSignalType, setFilterSignalType] = useState<string>('all')
  const [filterConnection, setFilterConnection] = useState<ConnectionFilter>('all')
  const pinoutRequestSeq = useRef(0)
  const mousePos = useRef<{ x: number; y: number } | null>(null)

  useEffect(() => {
    const unsub = onExtensionMessage((message) => {
      if (message.type !== 'selectionState') return
      setSelection({
        projectRoot: message.projectRoot ?? null,
        targetNames: message.targetNames ?? [],
      })
    })
    requestSelectionState()
    return unsub
  }, [])

  const resetPinoutView = useCallback(() => {
    pinoutRequestSeq.current += 1
    setPinoutState({ status: 'idle' })
    setSelectedComp(0)
    setHoveredPinNumber(null)
    setSearch('')
    setSortKey('pin_number')
    setSortDir('asc')
    setFilterSignalType('all')
    setFilterConnection('all')
  }, [])

  useEffect(() => {
    resetPinoutView()
  }, [selectedProjectRoot, selectedTargetName, resetPinoutView])

  // Load pinout data
  const loadPinout = useCallback(async () => {
    if (!selectionKey || !selectedProjectRoot || !selectedTargetName) return
    pinoutRequestSeq.current += 1
    const requestSeq = pinoutRequestSeq.current
    setPinoutState({ status: 'loading', selectionKey })
    try {
      const data = await api.pinout.get(selectedProjectRoot, selectedTargetName)
      if (requestSeq !== pinoutRequestSeq.current) return
      setPinoutState({ status: 'loaded', selectionKey, report: data })
    } catch (e) {
      if (requestSeq !== pinoutRequestSeq.current) return
      setPinoutState({
        status: 'error',
        selectionKey,
        message: e instanceof Error ? e.message : 'Failed to load pinout data',
      })
    }
  }, [selectionKey, selectedProjectRoot, selectedTargetName])

  useEffect(() => { loadPinout() }, [loadPinout])

  const report = pinoutState.status === 'loaded' && pinoutState.selectionKey === selectionKey
    ? pinoutState.report
    : null
  const loadingMessage = pinoutState.status === 'loading' && pinoutState.selectionKey === selectionKey
  const errorMessage = pinoutState.status === 'error' && pinoutState.selectionKey === selectionKey
    ? pinoutState.message
    : null

  // Current component
  const comp = report?.components?.[selectedComp] || null

  useEffect(() => {
    if (!report?.components.length) return
    setSelectedComp(index => Math.min(index, report.components.length - 1))
  }, [report])

  // Filter and sort pins
  const filteredPins = useMemo<PinInfo[]>(() => {
    if (!comp) return []

    const query = search.trim().toLowerCase()
    const valueForSort = SORT_VALUE[sortKey]
    const pins = comp.pins
      .filter(pin => filterSignalType === 'all' || pin.signal_type === filterSignalType)
      .filter(pin =>
        filterConnection === 'all' ||
        (filterConnection === 'connected' ? pin.is_connected : !pin.is_connected)
      )
      .filter(pin =>
        !query ||
        pin.pin_name.toLowerCase().includes(query) ||
        pin.pin_number?.toLowerCase().includes(query) ||
        pin.interfaces.some(iface => iface.toLowerCase().includes(query)) ||
        pin.connected_to.some(connection => connection.toLowerCase().includes(query)) ||
        pin.net_name?.toLowerCase().includes(query)
      )

    pins.sort((a, b) => {
      const cmp = valueForSort(a).localeCompare(valueForSort(b), undefined, { numeric: true })
      return sortDir === 'asc' ? cmp : -cmp
    })

    return pins
  }, [comp, search, sortKey, sortDir, filterSignalType, filterConnection])

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  // Unique signal types for filter
  const signalTypes = useMemo(() => {
    if (!comp) return []
    return [...new Set(comp.pins.map(p => p.signal_type))].sort()
  }, [comp])

  const totalPins = comp?.pins.length ?? 0

  // Check if footprint data is available
  const hasFootprint = Boolean(comp?.footprint_uuid)

  // Handle pad hover from footprint viewer → scroll to table row
  const handlePadHover = useCallback((padNumber: string) => {
    setHoveredPinNumber(padNumber)
    const row = document.getElementById(getPinRowId(padNumber))
    if (row) {
      row.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [])

  const updateHoverFromPoint = useCallback((x: number, y: number) => {
    const el = document.elementFromPoint(x, y)
    if (!el) {
      setHoveredPinNumber(null)
      return
    }
    const row = el.closest('tr[data-pin-number]')
    setHoveredPinNumber(row?.getAttribute('data-pin-number') ?? null)
  }, [])

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      mousePos.current = { x: e.clientX, y: e.clientY }
    }
    const onWheel = () => {
      requestAnimationFrame(() => {
        if (mousePos.current) {
          updateHoverFromPoint(mousePos.current.x, mousePos.current.y)
        }
      })
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('wheel', onWheel, { passive: true })
    return () => {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('wheel', onWheel)
    }
  }, [updateHoverFromPoint])

  if (loadingMessage) {
    return (
      <div className="pinout-panel sidebar-panel">
        <EmptyState title="Loading pinout data..." />
      </div>
    )
  }

  if (errorMessage) {
    return (
      <div className="pinout-panel sidebar-panel">
        <EmptyState
          title="Error loading pinout"
          description={errorMessage}
          className="error"
        />
        <div className="pinout-error-actions">
          <button onClick={loadPinout} className="action-btn secondary">Retry</button>
        </div>
      </div>
    )
  }

  return (
    <div className="pinout-panel sidebar-panel">
      {/* Header */}
      <div className="panel-toolbar-row pinout-header">
        <h2 className="pinout-title">Pinout Table</h2>

        {/* Component tabs */}
        {report && report.components.length > 1 && (
          <div className="pinout-tabs">
            {report.components.map((c, i) => (
              <button
                key={c.name}
                onClick={() => setSelectedComp(i)}
                className={`action-btn secondary pinout-tab ${i === selectedComp ? 'is-active' : ''}`}
              >
                {c.name.split('.').pop()}
              </button>
            ))}
          </div>
        )}

        {selectedProjectRoot && selectedTargetName && (
          <button onClick={loadPinout} className="action-btn secondary" title="Refresh">Refresh</button>
        )}
      </div>

      {!report || report.components.length === 0 ? (
        <EmptyState
          title={!selectedProjectRoot ? 'No project selected' : !selectedTargetName ? 'No target selected' : 'No pinout data available'}
          description={
            !selectedProjectRoot
              ? 'Select a project in the sidebar to view pinout data.'
              : !selectedTargetName
                ? 'Select a target in the sidebar to view pinout data.'
                : 'Add the generate_pinout_details trait to a component and run ato build.'
          }
        />
      ) : (
        <>
      {/* Filters bar */}
      <div className="panel-toolbar-row pinout-filters">
        <div className="pinout-search-box">
          <PanelSearchBox
            value={search}
            onChange={setSearch}
            placeholder="Search pins, interfaces, connections..."
          />
        </div>

        <div className="bom-project-select">
          <select
            value={filterSignalType}
            onChange={e => setFilterSignalType(e.target.value)}
          >
            <option value="all">All types</option>
            {signalTypes.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>

        <div className="bom-project-select">
          <select
            value={filterConnection}
            onChange={e => setFilterConnection(parseConnectionFilter(e.target.value))}
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

      {/* Side-by-side layout: Table + Footprint Viewer */}
      <div className="pinout-content">
        {/* Table */}
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
                const pinNumber = pin.pin_number
                const isHovered = pinNumber !== null && hoveredPinNumber === pinNumber
                const hasNotes = pin.notes.length > 0
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
                    onMouseLeave={() => setHoveredPinNumber(prev => (pinNumber && prev === pinNumber ? null : prev))}
                  >
                    <td className="pinout-cell">
                      <code className="pinout-dim-code">{pin.pin_number || '-'}</code>
                    </td>
                    <td className="pinout-cell">
                      <code className="pinout-pin-name">{pin.pin_name}</code>
                    </td>
                    <td className="pinout-cell">
                      <SignalBadge type={pin.signal_type} />
                    </td>
                    <td className="pinout-cell">
                      {pin.interfaces.length > 0
                        ? pin.interfaces.map((iface, i) => (
                            <span key={i} className="pinout-interface-tag">
                              {iface}
                            </span>
                          ))
                        : <span className="pinout-placeholder">-</span>
                      }
                    </td>
                    <td className="pinout-cell pinout-connected-cell">
                      {pin.connected_to.length > 0
                        ? (
                          <div title={pin.connected_to.join('\n')}>
                            {pin.connected_to.map((c, i) => (
                              <div key={`${c}-${i}`} className="pinout-connected-item">
                                <code className="pinout-connected-code">{c}</code>
                              </div>
                            ))}
                          </div>
                        )
                        : <span className="pinout-placeholder">-</span>
                      }
                    </td>
                    <td className="pinout-cell">
                      {pin.net_name
                        ? <code>{pin.net_name}</code>
                        : <span className="pinout-placeholder">-</span>
                      }
                    </td>
                    <td className="pinout-cell">
                      {hasNotes && pin.notes.map((n, i) => (
                        <span
                          key={i}
                          className={`pinout-note-tag ${n.includes('Unconnected') ? 'is-warning' : ''}`}
                        >
                          {n}
                        </span>
                      ))}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          {filteredPins.length === 0 && comp && (
            <EmptyState
              title="No pins match filters"
              description="Adjust search, signal type, or connection filters."
              className="pinout-no-results"
            />
          )}
        </div>

        {/* Footprint Viewer */}
        {hasFootprint && comp && selectedProjectRoot && selectedTargetName && (
          <div className="pinout-footprint">
            <FootprintViewerCanvas
              projectRoot={selectedProjectRoot}
              targetName={selectedTargetName}
              footprintUuid={comp.footprint_uuid}
              pins={comp.pins}
              selectedPinNumber={hoveredPinNumber}
              onPadClick={handlePadHover}
            />
          </div>
        )}
      </div>
      </>
      )}
    </div>
  )
}
