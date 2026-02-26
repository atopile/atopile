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
  highlightedIndex: number
  setHighlightedIndex: (v: number | ((prev: number) => number)) => void
}

const SelectCtx = createContext<SelectContextValue | null>(null)

function useSelectCtx() {
  const ctx = useContext(SelectCtx)
  if (!ctx) throw new Error('Select.* must be used inside <Select>')
  return ctx
}

/** Public hook — use from custom triggers that compose Select */
export const useSelectContext = useSelectCtx

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
  /** Extra class appended to root div */
  className?: string
  children: ReactNode
}

export function Select({
  items,
  value: valueProp,
  defaultValue = null,
  onValueChange,
  disabled = false,
  className,
  children,
}: SelectProps) {
  const [open, setOpenRaw] = useState(false)
  const [internalValue, setInternalValue] = useState(defaultValue)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)

  const isControlled = valueProp !== undefined
  const value = isControlled ? valueProp : internalValue

  // Sync highlight to selected item on open, reset on close
  const setOpen = useCallback(
    (v: boolean) => {
      setOpenRaw(v)
      if (v) {
        const idx = items.findIndex((i) => i.value === (isControlled ? valueProp : internalValue))
        setHighlightedIndex(idx >= 0 ? idx : 0)
      } else {
        setHighlightedIndex(-1)
      }
    },
    [items, isControlled, valueProp, internalValue],
  )

  const handleChange = useCallback(
    (v: string | null) => {
      if (!isControlled) setInternalValue(v)
      onValueChange?.(v)
    },
    [isControlled, onValueChange],
  )

  // Clamp highlightedIndex when the item list shrinks (e.g. filtered combobox)
  useEffect(() => {
    if (items.length > 0 && highlightedIndex >= items.length) {
      setHighlightedIndex(items.length - 1)
    }
  }, [items.length, highlightedIndex])

  const rootClass = className ? `select-root ${className}` : 'select-root'

  return (
    <SelectCtx.Provider value={{ open, setOpen, value, onValueChange: handleChange, items, disabled, highlightedIndex, setHighlightedIndex }}>
      <div className={rootClass}>{children}</div>
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
  const { open, setOpen, items, highlightedIndex, setHighlightedIndex, onValueChange } = useSelectCtx()
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

  // Keyboard navigation
  useEffect(() => {
    if (!open) return
    function handleKey(e: KeyboardEvent) {
      switch (e.key) {
        case 'Escape':
          setOpen(false)
          break
        case 'ArrowDown':
          e.preventDefault()
          setHighlightedIndex((i: number) => Math.min(i + 1, items.length - 1))
          break
        case 'ArrowUp':
          e.preventDefault()
          setHighlightedIndex((i: number) => Math.max(i - 1, 0))
          break
        case 'Enter': {
          e.preventDefault()
          const item = items[highlightedIndex]
          if (item) {
            onValueChange(item.value)
            setOpen(false)
          }
          break
        }
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open, setOpen, items, highlightedIndex, setHighlightedIndex, onValueChange])

  // Scroll highlighted item into view
  useEffect(() => {
    if (!open || highlightedIndex < 0 || !ref.current) return
    const el = ref.current.querySelector('[data-highlighted="true"]') as HTMLElement
    el?.scrollIntoView({ block: 'nearest' })
  }, [open, highlightedIndex])

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
  const { value: selected, onValueChange, setOpen, items, highlightedIndex, setHighlightedIndex } = useSelectCtx()
  const isSelected = value === selected
  const itemIndex = items.findIndex((i) => i.value === value)
  const isHighlighted = itemIndex === highlightedIndex

  return (
    <button
      type="button"
      role="option"
      aria-selected={isSelected}
      data-selected={isSelected ? 'true' : undefined}
      data-highlighted={isHighlighted ? 'true' : undefined}
      data-disabled={disabled ? 'true' : undefined}
      className={`select-item ${className}`.trim()}
      onClick={() => {
        if (disabled) return
        onValueChange(value)
        setOpen(false)
      }}
      onMouseEnter={() => {
        if (!disabled) setHighlightedIndex(itemIndex)
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
