// TODO: Add keyboard navigation (arrow keys, type-ahead) if used in
//       VS Code extension webviews where keyboard accessibility matters.
import {
  createContext,
  useContext,
  useState,
  useRef,
  useEffect,
  useCallback,
  type ReactNode,
  type HTMLAttributes,
} from 'react'
import { ChevronDown, Check } from 'lucide-react'
import './Select.css'

/* ---- Types ---- */

interface SelectItem {
  label: string
  value: string | null
}

/* ---- Context ---- */

interface SelectContextValue {
  open: boolean
  setOpen: (v: boolean) => void
  value: string | null
  onValueChange: (v: string | null) => void
  items: SelectItem[]
  disabled: boolean
}

const SelectCtx = createContext<SelectContextValue | null>(null)

function useSelectCtx() {
  const ctx = useContext(SelectCtx)
  if (!ctx) throw new Error('Select.* must be used inside <Select>')
  return ctx
}

/* ---- Select (root) ---- */

export interface SelectProps {
  /** Available items */
  items: SelectItem[]
  /** Controlled value */
  value?: string | null
  /** Default value (uncontrolled) */
  defaultValue?: string | null
  /** Change handler */
  onValueChange?: (value: string | null) => void
  /** Disable the entire select */
  disabled?: boolean
  children: ReactNode
}

export function Select({
  items,
  value: valueProp,
  defaultValue = null,
  onValueChange,
  disabled = false,
  children,
}: SelectProps) {
  const [open, setOpen] = useState(false)
  const [internalValue, setInternalValue] = useState(defaultValue)

  const isControlled = valueProp !== undefined
  const value = isControlled ? valueProp : internalValue

  const handleChange = useCallback(
    (v: string | null) => {
      if (!isControlled) setInternalValue(v)
      onValueChange?.(v)
    },
    [isControlled, onValueChange],
  )

  return (
    <SelectCtx.Provider value={{ open, setOpen, value, onValueChange: handleChange, items, disabled }}>
      <div className="select-root">{children}</div>
    </SelectCtx.Provider>
  )
}

/* ---- SelectTrigger ---- */

export interface SelectTriggerProps extends HTMLAttributes<HTMLButtonElement> {
  'aria-invalid'?: boolean
}

export function SelectTrigger({
  children,
  className = '',
  ...props
}: SelectTriggerProps) {
  const { open, setOpen, disabled } = useSelectCtx()
  const ref = useRef<HTMLButtonElement>(null)

  return (
    <button
      ref={ref}
      type="button"
      role="combobox"
      aria-expanded={open}
      disabled={disabled}
      className={`select-trigger ${className}`.trim()}
      onClick={() => setOpen(!open)}
      {...props}
    >
      {children}
      <ChevronDown size={12} className="select-chevron" />
    </button>
  )
}

/* ---- SelectValue ---- */

export interface SelectValueProps {
  placeholder?: string
}

export function SelectValue({ placeholder = 'Select...' }: SelectValueProps) {
  const { value, items } = useSelectCtx()
  const selected = items.find((i) => i.value === value)

  if (!selected || selected.value === null) {
    return <span className="select-value select-value-placeholder">{selected?.label ?? placeholder}</span>
  }

  return <span className="select-value">{selected.label}</span>
}

/* ---- SelectContent ---- */

export interface SelectContentProps {
  children: ReactNode
  className?: string
}

export function SelectContent({ children, className = '' }: SelectContentProps) {
  const { open, setOpen } = useSelectCtx()
  const ref = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.closest('.select-root')?.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open, setOpen])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open, setOpen])

  if (!open) return null

  return (
    <div ref={ref} className={`select-content ${className}`.trim()} role="listbox">
      {children}
    </div>
  )
}

/* ---- SelectGroup ---- */

export interface SelectGroupProps {
  /** Optional group label */
  label?: string
  children: ReactNode
  className?: string
}

export function SelectGroup({ label, children, className = '' }: SelectGroupProps) {
  return (
    <div className={`select-group ${className}`.trim()} role="group">
      {label && <div className="select-group-label">{label}</div>}
      {children}
    </div>
  )
}

/* ---- SelectItem ---- */

export interface SelectItemProps {
  value: string | null
  disabled?: boolean
  children: ReactNode
  className?: string
}

export function SelectItem({ value, disabled = false, children, className = '' }: SelectItemProps) {
  const { value: selected, onValueChange, setOpen } = useSelectCtx()
  const isSelected = value === selected

  return (
    <button
      type="button"
      role="option"
      aria-selected={isSelected}
      data-selected={isSelected ? 'true' : undefined}
      data-disabled={disabled ? 'true' : undefined}
      className={`select-item ${className}`.trim()}
      onClick={() => {
        if (disabled) return
        onValueChange(value)
        setOpen(false)
      }}
    >
      <span className="select-item-check">
        {isSelected && <Check size={12} />}
      </span>
      {children}
    </button>
  )
}

/* ---- SelectLabel (standalone group heading inside content) ---- */

export interface SelectLabelProps {
  children: ReactNode
  className?: string
}

export function SelectLabel({ children, className = '' }: SelectLabelProps) {
  return <div className={`select-label ${className}`.trim()}>{children}</div>
}

/* ---- SelectSeparator ---- */

export interface SelectSeparatorProps {
  className?: string
}

export function SelectSeparator({ className = '' }: SelectSeparatorProps) {
  return <div role="separator" className={`select-separator ${className}`.trim()} />
}
