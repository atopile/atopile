import { useState, useEffect, useCallback, useMemo } from 'react'
import { api } from '../api/client'
import type { PinoutData, PinInfo } from '../types/build'

// ---------------------------------------------------------------------------
//  Signal type color badges
// ---------------------------------------------------------------------------

const SIGNAL_COLORS: Record<string, { bg: string; fg: string }> = {
  digital: { bg: '#264f78', fg: '#9cdcfe' },
  analog: { bg: '#2d4a2d', fg: '#a3d9a5' },
  power: { bg: '#5c2020', fg: '#f5a8a8' },
  ground: { bg: '#3c3c3c', fg: '#aaa' },
  nc: { bg: '#444', fg: '#888' },
}

function SignalBadge({ type }: { type: string }) {
  const colors = SIGNAL_COLORS[type] || SIGNAL_COLORS.digital
  return (
    <span style={{
      display: 'inline-block',
      padding: '1px 8px',
      borderRadius: 3,
      fontSize: '0.85em',
      fontWeight: 600,
      background: colors.bg,
      color: colors.fg,
    }}>
      {type}
    </span>
  )
}

// ---------------------------------------------------------------------------
//  Sortable header
// ---------------------------------------------------------------------------

type SortKey = 'pin_name' | 'signal_type' | 'interfaces' | 'connected_to' | 'voltage' | 'net_name'
type SortDir = 'asc' | 'desc'

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
      style={{ cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap', padding: '8px 12px', textAlign: 'left' }}
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
  const [projects, setProjects] = useState<{ root: string; name: string }[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [targets, setTargets] = useState<string[]>([])
  const [selectedTarget, setSelectedTarget] = useState<string>('default')
  const [report, setReport] = useState<PinoutData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedComp, setSelectedComp] = useState(0)
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('pin_name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [expandedPin, setExpandedPin] = useState<string | null>(null)
  const [filterSignalType, setFilterSignalType] = useState<string>('all')
  const [filterConnection, setFilterConnection] = useState<string>('all')

  // Load projects on mount
  useEffect(() => {
    api.projects.list()
      .then(data => {
        const projs = (data.projects || []).map(p => ({ root: p.root, name: p.name }))
        setProjects(projs)
        if (projs.length > 0 && !selectedProject) {
          setSelectedProject(projs[0].root)
        }
      })
      .catch(() => setProjects([]))
  }, [])

  // Load targets when project changes
  useEffect(() => {
    if (!selectedProject) return
    api.pinout.targets(selectedProject)
      .then(data => {
        setTargets(data.targets || [])
        if (data.targets?.length > 0) {
          setSelectedTarget(data.targets[0])
        }
      })
      .catch(() => setTargets([]))
  }, [selectedProject])

  // Load pinout data
  const loadPinout = useCallback(async () => {
    if (!selectedProject || !selectedTarget) return
    setLoading(true)
    setError(null)
    try {
      const data = await api.pinout.get(selectedProject, selectedTarget)
      setReport(data)
      setSelectedComp(0)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load pinout data')
      setReport(null)
    } finally {
      setLoading(false)
    }
  }, [selectedProject, selectedTarget])

  useEffect(() => { loadPinout() }, [loadPinout])

  // Current component
  const comp = report?.components?.[selectedComp] || null

  // Filter and sort pins
  const filteredPins = useMemo(() => {
    if (!comp) return [] as PinInfo[]
    let pins = comp.pins

    // Signal type filter
    if (filterSignalType !== 'all') {
      pins = pins.filter(p => p.signal_type === filterSignalType)
    }

    // Connection filter
    if (filterConnection === 'connected') {
      pins = pins.filter(p => p.connected_to.length > 0)
    } else if (filterConnection === 'unconnected') {
      pins = pins.filter(p => p.connected_to.length === 0)
    }

    // Search filter
    if (search) {
      const q = search.toLowerCase()
      pins = pins.filter(p =>
        p.pin_name.toLowerCase().includes(q) ||
        p.interfaces.some(i => i.toLowerCase().includes(q)) ||
        p.connected_to.some(c => c.toLowerCase().includes(q)) ||
        (p.net_name && p.net_name.toLowerCase().includes(q))
      )
    }

    // Sort
    pins = [...pins].sort((a, b) => {
      let va: string, vb: string
      switch (sortKey) {
        case 'pin_name': va = a.pin_name; vb = b.pin_name; break
        case 'signal_type': va = a.signal_type; vb = b.signal_type; break
        case 'interfaces': va = a.interfaces.join(','); vb = b.interfaces.join(','); break
        case 'connected_to': va = a.connected_to.join(','); vb = b.connected_to.join(','); break
        case 'voltage': va = a.voltage || ''; vb = b.voltage || ''; break
        case 'net_name': va = a.net_name || ''; vb = b.net_name || ''; break
        default: va = ''; vb = ''
      }
      const cmp = va.localeCompare(vb, undefined, { numeric: true })
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

  // Stats
  const warningCount = comp?.warnings.length ?? 0
  const totalPins = comp?.pins.length ?? 0
  const connectedPins = comp?.pins.filter(p => p.connected_to.length > 0).length ?? 0

  // Container style (uses VS Code CSS variables)
  const containerStyle: React.CSSProperties = {
    padding: '16px 24px',
    maxWidth: 1400,
    margin: '0 auto',
    fontFamily: 'var(--vscode-font-family, monospace)',
    fontSize: 'var(--vscode-font-size, 13px)',
    color: 'var(--vscode-foreground, #ccc)',
  }

  if (loading) {
    return <div style={containerStyle}><p style={{ opacity: 0.6 }}>Loading pinout data...</p></div>
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <p style={{ color: 'var(--vscode-errorForeground, #f44)' }}>{error}</p>
        <button onClick={loadPinout} style={btnStyle}>Retry</button>
      </div>
    )
  }

  if (!report || report.components.length === 0) {
    return (
      <div style={containerStyle}>
        <h2 style={{ marginTop: 0, fontWeight: 500 }}>Pinout Table</h2>
        <p style={{ opacity: 0.6 }}>
          No pinout data available. Add the <code>generate_pinout_details</code> trait
          to a component and run <code>ato build</code>.
        </p>
        {selectedProject && (
          <div style={{ marginTop: 12 }}>
            <label style={labelStyle}>Project: </label>
            <select value={selectedProject} onChange={e => setSelectedProject(e.target.value)} style={selectStyle}>
              {projects.map(p => <option key={p.root} value={p.root}>{p.name}</option>)}
            </select>
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap', marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontWeight: 500 }}>Pinout Table</h2>

        {/* Project selector */}
        {projects.length > 1 && (
          <select value={selectedProject} onChange={e => setSelectedProject(e.target.value)} style={selectStyle}>
            {projects.map(p => <option key={p.root} value={p.root}>{p.name}</option>)}
          </select>
        )}

        {/* Target selector */}
        {targets.length > 1 && (
          <select value={selectedTarget} onChange={e => setSelectedTarget(e.target.value)} style={selectStyle}>
            {targets.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        )}

        {/* Component tabs */}
        {report.components.length > 1 && (
          <div style={{ display: 'flex', gap: 4 }}>
            {report.components.map((c, i) => (
              <button
                key={i}
                onClick={() => setSelectedComp(i)}
                style={{
                  ...btnStyle,
                  background: i === selectedComp
                    ? 'var(--vscode-button-background, #0e639c)'
                    : 'var(--vscode-input-background, #3c3c3c)',
                  color: i === selectedComp
                    ? 'var(--vscode-button-foreground, #fff)'
                    : 'var(--vscode-foreground, #ccc)',
                }}
              >
                {c.name.split('.').pop()}
              </button>
            ))}
          </div>
        )}

        <button onClick={loadPinout} style={btnStyle} title="Refresh">Refresh</button>
      </div>

      {/* Component info bar */}
      {comp && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap',
          padding: '8px 12px', marginBottom: 12,
          background: 'var(--vscode-input-background, #252526)',
          borderRadius: 4,
          fontSize: '0.9em',
        }}>
          <span><strong>{comp.name}</strong></span>
          <span style={{ opacity: 0.7 }}>Type: {comp.type_name}</span>
          <span style={{ opacity: 0.7 }}>Pins: {totalPins}</span>
          <span style={{ opacity: 0.7 }}>Connected: {connectedPins}/{totalPins}</span>
          {warningCount > 0 && (
            <span style={{ color: 'var(--vscode-editorWarning-foreground, #cca700)' }}>
              {warningCount} warning(s)
            </span>
          )}
        </div>
      )}

      {/* Warnings */}
      {comp && comp.warnings.length > 0 && (
        <div style={{
          padding: '8px 12px', marginBottom: 12,
          background: 'rgba(204, 167, 0, 0.1)',
          border: '1px solid var(--vscode-editorWarning-foreground, #cca700)',
          borderRadius: 4,
        }}>
          {comp.warnings.map((w, i) => (
            <div key={i} style={{ color: 'var(--vscode-editorWarning-foreground, #cca700)' }}>
              {w}
            </div>
          ))}
        </div>
      )}

      {/* Filters bar */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', marginBottom: 12 }}>
        <input
          type="text"
          placeholder="Search pins, interfaces, connections..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            ...inputStyle,
            flex: '1 1 250px',
            minWidth: 200,
          }}
        />

        <select value={filterSignalType} onChange={e => setFilterSignalType(e.target.value)} style={selectStyle}>
          <option value="all">All types</option>
          {signalTypes.map(t => <option key={t} value={t}>{t}</option>)}
        </select>

        <select value={filterConnection} onChange={e => setFilterConnection(e.target.value)} style={selectStyle}>
          <option value="all">All pins</option>
          <option value="connected">Connected</option>
          <option value="unconnected">Unconnected</option>
        </select>

        <span style={{ opacity: 0.6, fontSize: '0.85em' }}>
          {filteredPins.length} of {totalPins} pins
        </span>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '0.9em',
        }}>
          <thead>
            <tr style={{
              borderBottom: '2px solid var(--vscode-panel-border, #444)',
              background: 'var(--vscode-input-background, #252526)',
            }}>
              <SortHeader label="Pin Name" sortKey="pin_name" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
              <SortHeader label="Signal Type" sortKey="signal_type" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
              <SortHeader label="Interfaces" sortKey="interfaces" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
              <SortHeader label="Connected To" sortKey="connected_to" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
              <SortHeader label="Voltage" sortKey="voltage" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
              <SortHeader label="Net Name" sortKey="net_name" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
              <th style={{ padding: '8px 12px', textAlign: 'left' }}>Notes</th>
            </tr>
          </thead>
          <tbody>
            {filteredPins.map((pin) => {
              const isExpanded = expandedPin === pin.pin_name
              const hasNotes = pin.notes.length > 0

              return (
                <tr
                  key={pin.pin_name}
                  onClick={() => setExpandedPin(isExpanded ? null : pin.pin_name)}
                  style={{
                    borderBottom: '1px solid var(--vscode-panel-border, #333)',
                    cursor: 'pointer',
                    background: isExpanded
                      ? 'var(--vscode-list-activeSelectionBackground, rgba(255,255,255,0.05))'
                      : 'transparent',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--vscode-list-hoverBackground, rgba(255,255,255,0.04))')}
                  onMouseLeave={e => (e.currentTarget.style.background = isExpanded ? 'var(--vscode-list-activeSelectionBackground, rgba(255,255,255,0.05))' : 'transparent')}
                >
                  <td style={cellStyle}>
                    <code style={{ fontWeight: 500 }}>{pin.pin_name}</code>
                    {pin.pin_number && (
                      <span style={{ marginLeft: 6, opacity: 0.5, fontSize: '0.85em' }}>
                        (#{pin.pin_number})
                      </span>
                    )}
                  </td>
                  <td style={cellStyle}>
                    <SignalBadge type={pin.signal_type} />
                  </td>
                  <td style={cellStyle}>
                    {pin.interfaces.length > 0
                      ? pin.interfaces.map((iface, i) => (
                          <span key={i} style={{
                            display: 'inline-block',
                            padding: '1px 6px',
                            marginRight: 4,
                            marginBottom: 2,
                            borderRadius: 3,
                            background: 'var(--vscode-badge-background, #4d4d4d)',
                            color: 'var(--vscode-badge-foreground, #fff)',
                            fontSize: '0.85em',
                          }}>
                            {iface}
                          </span>
                        ))
                      : <span style={{ opacity: 0.4 }}>-</span>
                    }
                  </td>
                  <td style={{ ...cellStyle, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {pin.connected_to.length > 0
                      ? (
                        <span title={pin.connected_to.join('\n')}>
                          {pin.connected_to.map((c, i) => (
                            <div key={i} style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              <code style={{ fontSize: '0.85em' }}>{c}</code>
                            </div>
                          ))}
                        </span>
                      )
                      : <span style={{ opacity: 0.4 }}>-</span>
                    }
                  </td>
                  <td style={cellStyle}>
                    {pin.voltage
                      ? <code>{pin.voltage}</code>
                      : <span style={{ opacity: 0.4 }}>-</span>
                    }
                  </td>
                  <td style={cellStyle}>
                    {pin.net_name
                      ? <code>{pin.net_name}</code>
                      : <span style={{ opacity: 0.4 }}>-</span>
                    }
                  </td>
                  <td style={cellStyle}>
                    {hasNotes && pin.notes.map((n, i) => (
                      <span key={i} style={{
                        display: 'inline-block',
                        padding: '1px 6px',
                        marginRight: 4,
                        borderRadius: 3,
                        background: n.includes('Unconnected')
                          ? 'rgba(204, 167, 0, 0.15)'
                          : 'rgba(100, 100, 100, 0.2)',
                        color: n.includes('Unconnected')
                          ? 'var(--vscode-editorWarning-foreground, #cca700)'
                          : 'inherit',
                        fontSize: '0.85em',
                      }}>
                        {n}
                      </span>
                    ))}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {filteredPins.length === 0 && comp && (
        <div style={{ textAlign: 'center', padding: 32, opacity: 0.5 }}>
          No pins match the current filter
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
//  Shared styles
// ---------------------------------------------------------------------------

const btnStyle: React.CSSProperties = {
  padding: '4px 12px',
  border: '1px solid var(--vscode-button-border, transparent)',
  borderRadius: 3,
  background: 'var(--vscode-button-secondaryBackground, #3c3c3c)',
  color: 'var(--vscode-button-secondaryForeground, #ccc)',
  cursor: 'pointer',
  fontSize: '0.9em',
}

const selectStyle: React.CSSProperties = {
  padding: '4px 8px',
  border: '1px solid var(--vscode-input-border, #444)',
  borderRadius: 3,
  background: 'var(--vscode-input-background, #3c3c3c)',
  color: 'var(--vscode-input-foreground, #ccc)',
  fontSize: '0.9em',
}

const inputStyle: React.CSSProperties = {
  padding: '6px 10px',
  border: '1px solid var(--vscode-input-border, #444)',
  borderRadius: 3,
  background: 'var(--vscode-input-background, #3c3c3c)',
  color: 'var(--vscode-input-foreground, #ccc)',
  outline: 'none',
  fontSize: '0.9em',
}

const labelStyle: React.CSSProperties = {
  opacity: 0.7,
  fontSize: '0.9em',
}

const cellStyle: React.CSSProperties = {
  padding: '6px 12px',
  verticalAlign: 'top',
}
