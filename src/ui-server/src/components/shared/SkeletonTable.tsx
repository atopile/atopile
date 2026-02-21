import { Skeleton } from './Skeleton'

export function SkeletonTable() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%', maxWidth: 384 }}>
      {Array.from({ length: 5 }).map((_, index) => (
        <div key={index} style={{ display: 'flex', gap: 16 }}>
          <Skeleton style={{ height: 16, flex: 1 }} />
          <Skeleton style={{ height: 16, width: 96 }} />
          <Skeleton style={{ height: 16, width: 80 }} />
        </div>
      ))}
    </div>
  )
}
