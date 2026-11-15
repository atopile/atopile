import {
  createContext,
  useContext,
  useState,
  useRef,
  useEffect,
  useCallback,
  useId,
  type ReactNode,
  type HTMLAttributes,
  type KeyboardEvent as ReactKeyboardEvent,
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
  /** Index of the keyboard-highlighted item, or -1 for none. */
  highlightedIndex: number
  setHighlightedIndex: (i: number) => void
  /** Stable id of the listbox, used to wire aria-activedescendant. */
  listboxId: string
  /** Shared keydown handler attached to the trigger (the focused element). */
  onTriggerKeyDown: (e: ReactKeyboardEvent<HTMLButtonElement>) => void
}

const SelectCtx = createContext<SelectContextValue | null>(null)

function useSelectCtx() {
  const ctx = useContext(SelectCtx)
  if (!ctx) throw new Error('Select.* must be used inside <Select>')
  return ctx
}

const optionId = (listboxId: string, index: number) => `${listboxId}-opt-${index}`

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
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const listboxId = useId()
  const typeahead = useRef<{ query: string; timer: ReturnType<typeof setTimeout> | null }>({
    query: '',
    timer: null,
  })

  const isControlled = valueProp !== undefined
  const value = isControlled ? valueProp : internalValue

  const handleChange = useCallback(
    (v: string | null) => {
      if (!isControlled) setInternalValue(v)
      onValueChange?.(v)
    },
    [isControlled, onValueChange],
  )

  // When the list opens, highlight the selected item (or the first one);
  // when it closes, clear the highlight. Deliberately keyed on `open` only so
  // changing the value while open does not move the highlight.
  useEffect(() => {
    if (!open) {
      setHighlightedIndex(-1)
      return
    }
    const selectedIndex = items.findIndex((it) => it.value === value)
    setHighlightedIndex(selectedIndex >= 0 ? selectedIndex : 0)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const runTypeahead = useCallback(
    (char: string) => {
      const n = items.length
      if (n === 0) return
      if (typeahead.current.timer) clearTimeout(typeahead.current.timer)
      const fresh = typeahead.current.query === ''
      typeahead.current.query += char.toLowerCase()
      const query = typeahead.current.query
      // Fresh single char: search after the current item so repeats cycle.
      // Continued query: include the current item so it stays put if it matches.
      const from = fresh ? highlightedIndex : highlightedIndex - 1
      for (let offset = 1; offset <= n; offset++) {
        const idx = (((from + offset) % n) + n) % n
        if (items[idx].label.toLowerCase().startsWith(query)) {
          setHighlightedIndex(idx)
          break
        }
      }
      typeahead.current.timer = setTimeout(() => {
        typeahead.current.query = ''
      }, 500)
    },
    [items, highlightedIndex],
  )

  const onTriggerKeyDown = useCallback(
    (e: ReactKeyboardEvent<HTMLButtonElement>) => {
      if (disabled) return
      const n = items.length
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          if (!open) setOpen(true)
          else if (n > 0) setHighlightedIndex((highlightedIndex + 1) % n)
          break
        case 'ArrowUp':
          e.preventDefault()
          if (!open) setOpen(true)
          else if (n > 0) setHighlightedIndex(highlightedIndex <= 0 ? n - 1 : highlightedIndex - 1)
          break
        case 'Home':
          if (open && n > 0) {
            e.preventDefault()
            setHighlightedIndex(0)
          }
          break
        case 'End':
          if (open && n > 0) {
            e.preventDefault()
            setHighlightedIndex(n - 1)
          }
          break
        case 'Enter':
        case ' ':
          e.preventDefault()
          if (!open) setOpen(true)
          else if (highlightedIndex >= 0 && highlightedIndex < n) {
            handleChange(items[highlightedIndex].value)
            setOpen(false)
          }
          break
        case 'Escape':
          if (open) {
            e.preventDefault()
            setOpen(false)
          }
          break
        case 'Tab':
          if (open) setOpen(false)
          break
        default:
          if (open && e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
            e.preventDefault()
            runTypeahead(e.key)
          }
      }
    },
    [disabled, items, open, highlightedIndex, handleChange, runTypeahead],
  )

  return (
    <SelectCtx.Provider
      value={{
        open,
        setOpen,
        value,
        onValueChange: handleChange,
        items,
        disabled,
        highlightedIndex,
        setHighlightedIndex,
        listboxId,
        onTriggerKeyDown,
      }}
    >
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
  const { open, setOpen, disabled, highlightedIndex, listboxId, onTriggerKeyDown } = useSelectCtx()
  const ref = useRef<HTMLButtonElement>(null)

  return (
    <button
      ref={ref}
      type="button"
      role="combobox"
      aria-expanded={open}
      aria-haspopup="listbox"
      aria-controls={listboxId}
      aria-activedescendant={
        open && highlightedIndex >= 0 ? optionId(listboxId, highlightedIndex) : undefined
      }
      disabled={disabled}
      className={`select-trigger ${className}`.trim()}
      onClick={() => setOpen(!open)}
      onKeyDown={onTriggerKeyDown}
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
  const { open, setOpen, listboxId } = useSelectCtx()
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

  if (!open) return null

  return (
    <div ref={ref} id={listboxId} className={`select-content ${className}`.trim()} role="listbox">
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
  const {
    value: selected,
    onValueChange,
    setOpen,
    items,
    highlightedIndex,
    setHighlightedIndex,
    listboxId,
  } = useSelectCtx()
  const ref = useRef<HTMLButtonElement>(null)
  const isSelected = value === selected
  const index = items.findIndex((i) => i.value === value)
  const isHighlighted = index >= 0 && index === highlightedIndex

  // Keep the keyboard-highlighted item in view as it moves. Optional call so it
  // is a no-op where scrollIntoView is unavailable (e.g. jsdom in tests).
  useEffect(() => {
    if (isHighlighted) ref.current?.scrollIntoView?.({ block: 'nearest' })
  }, [isHighlighted])

  return (
    <button
      ref={ref}
      type="button"
      role="option"
      id={index >= 0 ? optionId(listboxId, index) : undefined}
      aria-selected={isSelected}
      data-selected={isSelected ? 'true' : undefined}
      data-highlighted={isHighlighted ? 'true' : undefined}
      data-disabled={disabled ? 'true' : undefined}
      tabIndex={-1}
      className={`select-item ${className}`.trim()}
      onMouseEnter={() => {
        if (!disabled && index >= 0) setHighlightedIndex(index)
      }}
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
