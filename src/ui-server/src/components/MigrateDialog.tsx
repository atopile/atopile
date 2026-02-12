import { useState, useEffect, useCallback } from 'react'
import { Loader2, Check, AlertCircle, Package, FileCode, Settings } from 'lucide-react'
import { sendAction, sendActionWithResponse } from '../api/websocket'
import { useStore } from '../store'
import './MigrateDialog.css'

type StepStatus = 'idle' | 'running' | 'success' | 'error'

interface MigrationStep {
  id: string
  label: string
  description: string
  topic: string
  mandatory: boolean
  order: number
}

interface StepGroup {
  key: string
  label: string
  icon: typeof Package
  steps: MigrationStep[]
}

const TOPIC_META: Record<string, { label: string; icon: typeof Package }> = {
  mandatory: { label: 'Mandatory', icon: Package },
  ato_language: { label: 'Ato Language Renames', icon: FileCode },
  project_config: { label: 'Project Config', icon: Settings },
}

// Order topics should appear in the UI
const TOPIC_ORDER = ['mandatory', 'ato_language', 'project_config']

function buildGroups(steps: MigrationStep[]): StepGroup[] {
  const byTopic: Record<string, MigrationStep[]> = {}
  for (const step of steps) {
    if (!byTopic[step.topic]) byTopic[step.topic] = []
    byTopic[step.topic].push(step)
  }

  const groups: StepGroup[] = []
  // Known topics first, in order
  for (const topic of TOPIC_ORDER) {
    if (byTopic[topic] && byTopic[topic].length > 0) {
      const meta = TOPIC_META[topic] || { label: topic, icon: Package }
      groups.push({
        key: topic,
        label: meta.label,
        icon: meta.icon,
        steps: byTopic[topic],
      })
      delete byTopic[topic]
    }
  }
  // Any unknown topics appended at the end
  for (const [topic, topicSteps] of Object.entries(byTopic)) {
    if (topicSteps.length > 0) {
      groups.push({
        key: topic,
        label: topic.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        icon: Package,
        steps: topicSteps,
      })
    }
  }
  return groups
}

interface MigrateDialogProps {
  projectRoot: string
  onClose: () => void
}

export function MigrateDialog({ projectRoot, onClose }: MigrateDialogProps) {
  const actualVersion = useStore((state) => state.atopile.actualVersion)

  const [steps, setSteps] = useState<MigrationStep[]>([])
  const [groups, setGroups] = useState<StepGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)

  const [selectedSteps, setSelectedSteps] = useState<Set<string>>(new Set())
  const [stepStatuses, setStepStatuses] = useState<Record<string, StepStatus>>({})
  const [stepErrors, setStepErrors] = useState<Record<string, string>>({})
  const [isMigrating, setIsMigrating] = useState(false)

  // Fetch steps from backend, retrying until WebSocket is connected
  useEffect(() => {
    let cancelled = false
    let retryTimeout: ReturnType<typeof setTimeout>

    async function fetchSteps() {
      try {
        const response = await sendActionWithResponse('getMigrationSteps', {}, { timeoutMs: 15000 })
        if (cancelled) return
        const fetched: MigrationStep[] = (response.result?.steps as MigrationStep[]) || []
        setSteps(fetched)
        setGroups(buildGroups(fetched))
        setSelectedSteps(new Set(fetched.map(s => s.id)))
        setLoading(false)
      } catch (err) {
        if (cancelled) return
        // Retry if WebSocket isn't connected yet
        if (String(err).includes('not connected')) {
          retryTimeout = setTimeout(fetchSteps, 500)
        } else {
          setFetchError(String(err))
          setLoading(false)
        }
      }
    }
    fetchSteps()
    return () => {
      cancelled = true
      clearTimeout(retryTimeout)
    }
  }, [])

  const allDone = isMigrating && steps
    .filter(s => selectedSteps.has(s.id))
    .every(s => stepStatuses[s.id] === 'success' || stepStatuses[s.id] === 'error')

  const hasErrors = Object.values(stepStatuses).some(s => s === 'error')

  const toggleStep = (stepId: string) => {
    if (isMigrating) return
    const step = steps.find(s => s.id === stepId)
    if (step?.mandatory) return
    setSelectedSteps(prev => {
      const next = new Set(prev)
      if (next.has(stepId)) {
        next.delete(stepId)
      } else {
        next.add(stepId)
      }
      return next
    })
  }

  const handleMigrate = () => {
    const selected = steps
      .filter(s => selectedSteps.has(s.id))
      .map(s => s.id)
    if (selected.length === 0) return

    setIsMigrating(true)
    const initialStatuses: Record<string, StepStatus> = {}
    for (const id of selected) {
      initialStatuses[id] = 'running'
    }
    setStepStatuses(initialStatuses)
    setStepErrors({})

    sendAction('migrateProjectSteps', {
      projectRoot,
      steps: selected,
    })
  }

  // Listen for per-step results
  const handleStepResult = useCallback((event: Event) => {
    const detail = (event as CustomEvent).detail as {
      project_root?: string
      step?: string
      success?: boolean
      error?: string | null
    }
    if (detail.project_root !== projectRoot) return
    const stepId = detail.step
    if (!stepId) return

    if (detail.success) {
      setStepStatuses(prev => ({ ...prev, [stepId]: 'success' }))
    } else {
      setStepStatuses(prev => ({ ...prev, [stepId]: 'error' }))
      if (detail.error) {
        setStepErrors(prev => ({ ...prev, [stepId]: detail.error! }))
      }
    }
  }, [projectRoot])

  useEffect(() => {
    window.addEventListener('migration-step-result', handleStepResult)
    return () => window.removeEventListener('migration-step-result', handleStepResult)
  }, [handleStepResult])

  // Keyboard: Escape to close when not migrating
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isMigrating) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isMigrating, onClose])

  const renderStepStatus = (stepId: string) => {
    const status = stepStatuses[stepId]
    if (!status || status === 'idle') return null
    if (status === 'running') {
      return (
        <span className="migrate-step-status">
          <Loader2 size={14} className="spin" />
        </span>
      )
    }
    if (status === 'success') {
      return (
        <span className="migrate-step-status success">
          <Check size={14} />
        </span>
      )
    }
    if (status === 'error') {
      return (
        <span
          className="migrate-step-status error"
          title={stepErrors[stepId] || 'Failed'}
        >
          <AlertCircle size={14} />
        </span>
      )
    }
    return null
  }

  const versionDisplay = actualVersion || 'the latest version'

  if (loading) {
    return (
      <div className="migrate-page">
        <div className="migrate-header">
          <h1 className="migrate-title">Migrate Project</h1>
          <p className="migrate-subtitle">Loading migration steps...</p>
        </div>
        <div className="migrate-loading">
          <Loader2 size={24} className="spin" />
        </div>
      </div>
    )
  }

  if (fetchError) {
    return (
      <div className="migrate-page">
        <div className="migrate-header">
          <h1 className="migrate-title">Migrate Project</h1>
          <p className="migrate-subtitle">Failed to load migration steps.</p>
        </div>
        <div className="migrate-banner error">
          <AlertCircle size={16} />
          <span>{fetchError}</span>
        </div>
        <div className="migrate-actions">
          <button type="button" className="migrate-btn secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="migrate-page">
      {/* Header */}
      <div className="migrate-header">
        <h1 className="migrate-title">Migrate Project</h1>
        <p className="migrate-subtitle">
          It seems your project is not ready for atopile {versionDisplay} yet 😞
        </p>
        <p className="migrate-subtitle">
          Don't worry, this guide will make sure your project will be mostly automatically migrated to the latest standard!
        </p>
      </div>

      {/* Step Groups */}
      <div className="migrate-groups">
        {groups.map(group => {
          const GroupIcon = group.icon
          const groupSteps = group.steps
          if (groupSteps.length === 0) return null

          return (
            <div key={group.key} className="migrate-group">
              <div className="migrate-group-header">
                <GroupIcon size={14} className="migrate-group-icon" />
                <span className="migrate-group-label">{group.label}</span>
              </div>

              <div className="migrate-group-steps">
                {groupSteps.map(step => (
                  <div key={step.id} className="migrate-step-card">
                    <label
                      className={`migrate-step ${step.mandatory ? 'disabled' : ''}`}
                      onClick={(e) => {
                        if ((e.target as HTMLElement).tagName !== 'INPUT') {
                          e.preventDefault()
                          toggleStep(step.id)
                        }
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selectedSteps.has(step.id)}
                        onChange={() => toggleStep(step.id)}
                        disabled={step.mandatory || isMigrating}
                      />
                      <div className="migrate-step-content">
                        <div className="migrate-step-title-row">
                          <span className="migrate-step-label">{step.label}</span>
                          {renderStepStatus(step.id)}
                        </div>
                        <span className="migrate-step-description">{step.description}</span>
                      </div>
                    </label>
                    {stepErrors[step.id] && (
                      <div className="migrate-step-error">{stepErrors[step.id]}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {/* Success / Error banner */}
      {allDone && !hasErrors && (
        <div className="migrate-banner success">
          <Check size={16} />
          <span>Migration complete! You can now close this tab and build your project.</span>
        </div>
      )}
      {allDone && hasErrors && (
        <div className="migrate-banner error">
          <AlertCircle size={16} />
          <span>Some steps failed. Check the errors above and try again or fix them manually.</span>
        </div>
      )}

      {/* Actions */}
      <div className="migrate-actions">
        <button
          type="button"
          className="migrate-btn secondary"
          onClick={onClose}
          disabled={isMigrating && !allDone}
        >
          {allDone ? 'Close' : 'Cancel'}
        </button>
        {!allDone && (
          <button
            type="button"
            className="migrate-btn primary"
            onClick={handleMigrate}
            disabled={isMigrating || selectedSteps.size === 0}
          >
            {isMigrating ? (
              <>
                <Loader2 size={14} className="spin" />
                Migrating...
              </>
            ) : (
              'Run Migration'
            )}
          </button>
        )}
      </div>
    </div>
  )
}
