import {
  createContext,
  useContext,
  useState,
  useRef,
  useCallback,
  useEffect,
  type ReactNode,
  type ReactElement,
  cloneElement,
} from 'react'
import './HoverCard.css'

/* ---- Context ---- */

interface HoverCardContextValue {
  open: boolean
  show: () => void
  hide: () => void
  triggerRef: React.RefObject<HTMLElement | null>
}

const HoverCardCtx = createContext<HoverCardContextValue | null>(null)

function useHoverCardCtx() {
  const ctx = useContext(HoverCardCtx)
  if (!ctx) throw new Error('HoverCard.* must be used inside <HoverCard>')
  return ctx
}

/* ---- HoverCard (root) ---- */

export interface HoverCardProps {
  children: ReactNode
}

export function HoverCard({ children }: HoverCardProps) {
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLElement | null>(null)
  const openTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const delayRef = useRef(200)
  const closeDelayRef = useRef(200)

  const show = useCallback(() => {
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current)
    openTimerRef.current = setTimeout(() => setOpen(true), delayRef.current)
  }, [])

  const hide = useCallback(() => {
    if (openTimerRef.current) clearTimeout(openTimerRef.current)
    closeTimerRef.current = setTimeout(() => setOpen(false), closeDelayRef.current)
  }, [])

  // Expose delay setters via refs so trigger can configure them
  const ctx: HoverCardContextValue & {
    delayRef: React.MutableRefObject<number>
    closeDelayRef: React.MutableRefObject<number>
  } = {
    open,
    show,
    hide,
    triggerRef,
    delayRef,
    closeDelayRef,
  }

  useEffect(() => {
    return () => {
      if (openTimerRef.current) clearTimeout(openTimerRef.current)
      if (closeTimerRef.current) clearTimeout(closeTimerRef.current)
    }
  }, [])

  return (
    <HoverCardCtx.Provider value={ctx}>
      {children}
    </HoverCardCtx.Provider>
  )
}

/* ---- HoverCardTrigger ---- */

export interface HoverCardTriggerProps {
  /** Content rendered as the trigger — either children or render prop */
  children?: ReactNode
  /** Render a custom element as the trigger (receives hover handlers) */
  render?: ReactElement
  /** Delay before opening in ms (default 200) */
  delay?: number
  /** Delay before closing in ms (default 200) */
  closeDelay?: number
  className?: string
}

export function HoverCardTrigger({
  children,
  render,
  delay = 200,
  closeDelay = 200,
  className = '',
}: HoverCardTriggerProps) {
  const ctx = useHoverCardCtx() as HoverCardContextValue & {
    delayRef: React.MutableRefObject<number>
    closeDelayRef: React.MutableRefObject<number>
  }
  const { show, hide, triggerRef } = ctx

  // Sync delay values
  ctx.delayRef.current = delay
  ctx.closeDelayRef.current = closeDelay

  const handlers = {
    onMouseEnter: show,
    onMouseLeave: hide,
    onFocus: show,
    onBlur: hide,
  }

  // render prop — clone the element with hover handlers
  if (render) {
    return cloneElement(render, {
      ref: triggerRef,
      ...handlers,
    })
  }

  return (
    <span
      ref={triggerRef as React.RefObject<HTMLSpanElement>}
      className={`hover-card-trigger ${className}`.trim()}
      {...handlers}
    >
      {children}
    </span>
  )
}

/* ---- HoverCardContent ---- */

type Side = 'top' | 'bottom' | 'left' | 'right'

export interface HoverCardContentProps {
  children: ReactNode
  side?: Side
  /** Offset from trigger in px (default 8) */
  sideOffset?: number
  className?: string
}

export function HoverCardContent({
  children,
  side = 'bottom',
  sideOffset = 8,
  className = '',
}: HoverCardContentProps) {
  const { open, show, hide, triggerRef } = useHoverCardCtx()
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
      case 'top':
        top = r.top - c.height - sideOffset
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
      case 'bottom':
      default:
        top = r.bottom + sideOffset
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
      className={`hover-card-content ${className}`.trim()}
      style={pos ? { top: pos.top, left: pos.left } : { visibility: 'hidden' }}
      onMouseEnter={show}
      onMouseLeave={hide}
    >
      {children}
    </div>
  )
}
