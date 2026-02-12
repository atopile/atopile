import { useState, useEffect, useCallback } from 'react'
import { Loader2, Check, AlertCircle, Package, FileCode, Settings } from 'lucide-react'
import { sendAction } from '../api/websocket'
import { useStore } from '../store'
import './MigrateDialog.css'

type StepStatus = 'idle' | 'running' | 'success' | 'error'

interface MigrationStep {
  id: string
  label: string
  description: string
  alwaysChecked: boolean
  group: 'mandatory' | 'ato-renames' | 'project-config'
}

const MIGRATION_STEPS: MigrationStep[] = [
  {
    id: 'force_update_deps',
    label: 'Force update dependencies',
    description: 'Downloads the latest compatible versions of all project dependencies. This can take a few minutes depending on the number of packages.',
    alwaysChecked: true,
    group: 'mandatory',
  },
  {
    id: 'migrate_has_datasheet_defined',
    label: 'Rename has_datasheet_defined',
    description: 'Renames the deprecated has_datasheet_defined trait to the new naming convention used in the latest standard library.',
    alwaysChecked: false,
    group: 'ato-renames',
  },
  {
    id: 'migrate_has_single_electric_reference_shared',
    label: 'Rename has_single_electric_reference_shared',
    description: 'Renames the deprecated has_single_electric_reference_shared trait to match the updated API.',
    alwaysChecked: false,
    group: 'ato-renames',
  },
  {
    id: 'bump_requires_atopile',
    label: 'Bump requires-atopile version',
    description: 'Updates the requires-atopile field in your ato.yaml to match the current atopile version.',
    alwaysChecked: false,
    group: 'project-config',
  },
]

interface StepGroup {
  key: string
  label: string
  icon: typeof Package
  steps: MigrationStep[]
}

const STEP_GROUPS: StepGroup[] = [
  {
    key: 'mandatory',
    label: 'Mandatory',
    icon: Package,
    steps: MIGRATION_STEPS.filter(s => s.group === 'mandatory'),
  },
  {
    key: 'ato-renames',
    label: 'Ato Language Renames',
    icon: FileCode,
    steps: MIGRATION_STEPS.filter(s => s.group === 'ato-renames'),
  },
  {
    key: 'project-config',
    label: 'Project Config',
    icon: Settings,
    steps: MIGRATION_STEPS.filter(s => s.group === 'project-config'),
  },
]

interface MigrateDialogProps {
  projectRoot: string
  onClose: () => void
}

export function MigrateDialog({ projectRoot, onClose }: MigrateDialogProps) {
  const actualVersion = useStore((state) => state.atopile.actualVersion)

  const [selectedSteps, setSelectedSteps] = useState<Set<string>>(
    () => new Set(MIGRATION_STEPS.map(s => s.id))
  )
  const [stepStatuses, setStepStatuses] = useState<Record<string, StepStatus>>({})
  const [stepErrors, setStepErrors] = useState<Record<string, string>>({})
  const [isMigrating, setIsMigrating] = useState(false)

  const allDone = isMigrating && MIGRATION_STEPS
    .filter(s => selectedSteps.has(s.id))
    .every(s => stepStatuses[s.id] === 'success' || stepStatuses[s.id] === 'error')

  const hasErrors = Object.values(stepStatuses).some(s => s === 'error')

  const toggleStep = (stepId: string) => {
    if (isMigrating) return
    const step = MIGRATION_STEPS.find(s => s.id === stepId)
    if (step?.alwaysChecked) return
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
    const steps = MIGRATION_STEPS
      .filter(s => selectedSteps.has(s.id))
      .map(s => s.id)
    if (steps.length === 0) return

    setIsMigrating(true)
    const initialStatuses: Record<string, StepStatus> = {}
    for (const id of steps) {
      initialStatuses[id] = 'running'
    }
    setStepStatuses(initialStatuses)
    setStepErrors({})

    sendAction('migrateProjectSteps', {
      projectRoot,
      steps,
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
        {STEP_GROUPS.map(group => {
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
                      className={`migrate-step ${step.alwaysChecked ? 'disabled' : ''}`}
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
                        disabled={step.alwaysChecked || isMigrating}
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
