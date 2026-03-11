import {
  createContext,
  useContext,
  useState,
  useRef,
  useCallback,
  useEffect,
  type ReactNode,
} from 'react'
import './Tooltip.css'

/* ---- Provider (optional grouping context — sets shared delay) ---- */

interface TooltipProviderProps {
  /** Open delay in ms (default 300) */
  delayDuration?: number
  children: ReactNode
}

const DelayCtx = createContext(300)

export function TooltipProvider({ delayDuration = 300, children }: TooltipProviderProps) {
  return <DelayCtx.Provider value={delayDuration}>{children}</DelayCtx.Provider>
}

/* ---- Tooltip (root wrapper) ---- */

interface TooltipContextValue {
  open: boolean
  setOpen: (v: boolean) => void
  triggerRef: React.RefObject<HTMLElement | null>
  delayMs: number
}

const TooltipCtx = createContext<TooltipContextValue | null>(null)

function useTooltipCtx() {
  const ctx = useContext(TooltipCtx)
  if (!ctx) throw new Error('Tooltip.* must be used inside <Tooltip>')
  return ctx
}

interface TooltipProps {
  children: ReactNode
}

export function Tooltip({ children }: TooltipProps) {
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLElement | null>(null)
  const delayMs = useContext(DelayCtx)

  return (
    <TooltipCtx.Provider value={{ open, setOpen, triggerRef, delayMs }}>
      {children}
    </TooltipCtx.Provider>
  )
}

/* ---- Trigger ---- */

interface TooltipTriggerProps {
  children: ReactNode
  asChild?: boolean
  className?: string
}

export function TooltipTrigger({ children, asChild: _asChild, className = '' }: TooltipTriggerProps) {
  const { setOpen, triggerRef, delayMs } = useTooltipCtx()
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const show = useCallback(() => {
    timerRef.current = setTimeout(() => setOpen(true), delayMs)
  }, [delayMs, setOpen])

  const hide = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    setOpen(false)
  }, [setOpen])

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  return (
    <span
      ref={triggerRef as React.RefObject<HTMLSpanElement>}
      className={`tooltip-trigger ${className}`.trim()}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
    </span>
  )
}

/* ---- Content ---- */

type Side = 'top' | 'bottom' | 'left' | 'right'

interface TooltipContentProps {
  children: ReactNode
  side?: Side
  /** Offset from trigger in px (default 6) */
  sideOffset?: number
  className?: string
}

export function TooltipContent({
  children,
  side = 'top',
  sideOffset = 6,
  className = '',
}: TooltipContentProps) {
  const { open, triggerRef } = useTooltipCtx()
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null)
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) {
      setPos(null)
      return
    }
    const trigger = triggerRef.current
    const content = contentRef.current
    if (!trigger || !content) return

    const r = trigger.getBoundingClientRect()
    const c = content.getBoundingClientRect()

    let top: number
    let left: number

    switch (side) {
      case 'bottom':
        top = r.bottom + sideOffset
        left = r.left + r.width / 2 - c.width / 2
        break
      case 'left':
        top = r.top + r.height / 2 - c.height / 2
        left = r.left - c.width - sideOffset
        break
      case 'right':
        top = r.top + r.height / 2 - c.height / 2
        left = r.right + sideOffset
        break
      case 'top':
      default:
        top = r.top - c.height - sideOffset
        left = r.left + r.width / 2 - c.width / 2
        break
    }

    // Clamp to viewport
    left = Math.max(4, Math.min(left, window.innerWidth - c.width - 4))
    top = Math.max(4, Math.min(top, window.innerHeight - c.height - 4))

    setPos({ top, left })
  }, [open, side, sideOffset, triggerRef])

  if (!open) return null

  return (
    <div
      ref={contentRef}
      className={`tooltip-content ${className}`.trim()}
      role="tooltip"
      style={pos ? { top: pos.top, left: pos.left } : { visibility: 'hidden' }}
    >
      {children}
    </div>
  )
}
