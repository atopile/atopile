import { useState, useRef, useEffect } from 'react';

export interface EditableFieldProps {
  value: string;
  displayValue?: string;
  onSave: (newValue: string) => Promise<void>;
  /** If provided, renders a dropdown instead of a text input */
  options?: { value: string; label: string }[];
  /** CSS class for the wrapper */
  className?: string;
  /** Whether editing is enabled */
  enabled?: boolean;
  /** Unit suffix shown after value */
  unit?: string;
}

export const MEASUREMENT_OPTIONS = [
  { value: 'final_value', label: 'Final Value' },
  { value: 'average', label: 'Average' },
  { value: 'settling_time', label: 'Settling Time' },
  { value: 'peak_to_peak', label: 'Peak to Peak' },
  { value: 'overshoot', label: 'Overshoot' },
  { value: 'rms', label: 'RMS' },
  { value: 'envelope', label: 'Envelope' },
  { value: 'max', label: 'Max' },
  { value: 'min', label: 'Min' },
  { value: 'duty_cycle', label: 'Duty Cycle' },
  { value: 'frequency', label: 'Frequency' },
  { value: 'sweep', label: 'Sweep' },
  { value: 'gain_db', label: 'Gain (dB)' },
  { value: 'phase_deg', label: 'Phase (deg)' },
  { value: 'bandwidth_3db', label: 'Bandwidth 3dB' },
  { value: 'bode_plot', label: 'Bode Plot' },
  { value: 'efficiency', label: 'Efficiency' },
];

export const CAPTURE_OPTIONS = [
  { value: 'transient', label: 'Transient' },
  { value: 'ac', label: 'AC Analysis' },
  { value: 'dcop', label: 'DC Operating Point' },
];

export function EditableField({
  value,
  displayValue,
  onSave,
  options,
  className = '',
  enabled = true,
  unit,
}: EditableFieldProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement | HTMLSelectElement>(null);

  useEffect(() => { setDraft(value); }, [value]);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      if (inputRef.current instanceof HTMLInputElement) {
        inputRef.current.select();
      }
    }
  }, [editing]);

  if (!enabled) {
    return <span className={className}>{displayValue ?? value}{unit ? ` ${unit}` : ''}</span>;
  }

  const commit = async (newVal: string) => {
    if (newVal === value) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await onSave(newVal);
      setDraft(newVal);
    } catch {
      setDraft(value);
    } finally {
      setSaving(false);
      setEditing(false);
    }
  };

  const label = options
    ? (options.find(o => o.value === value)?.label ?? value)
    : (displayValue ?? value);

  if (!editing) {
    return (
      <span
        className={`${className} ric-editable`}
        onClick={() => setEditing(true)}
        title="Click to edit"
      >
        {label}{unit ? ` ${unit}` : ''}
      </span>
    );
  }

  if (options) {
    return (
      <select
        ref={inputRef as React.RefObject<HTMLSelectElement>}
        className={`ric-edit-control ric-edit-select ${saving ? 'ric-saving' : ''}`}
        value={draft}
        onChange={e => {
          setDraft(e.target.value);
          commit(e.target.value);
        }}
        onBlur={() => { if (!saving) setEditing(false); }}
        onKeyDown={e => {
          if (e.key === 'Escape') { setDraft(value); setEditing(false); }
        }}
        disabled={saving}
      >
        {options.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    );
  }

  return (
    <input
      ref={inputRef as React.RefObject<HTMLInputElement>}
      className={`ric-edit-control ric-edit-input ${saving ? 'ric-saving' : ''}`}
      type="text"
      value={draft}
      onChange={e => setDraft(e.target.value)}
      onBlur={() => { if (!saving) commit(draft); }}
      onKeyDown={e => {
        if (e.key === 'Enter') commit(draft);
        if (e.key === 'Escape') { setDraft(value); setEditing(false); }
      }}
      disabled={saving}
    />
  );
}
