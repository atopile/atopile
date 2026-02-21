import './Skeleton.css'

export interface SkeletonProps {
  /** Additional class name — use for sizing (e.g. height/width) */
  className?: string
  /** Inline styles for quick sizing */
  style?: React.CSSProperties
}

export function Skeleton({ className = '', style }: SkeletonProps) {
  return <div className={`skeleton ${className}`.trim()} style={style} />
}
