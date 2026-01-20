import { memo } from 'react';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'rectangular' | 'circular';
  width?: string | number;
  height?: string | number;
  lines?: number;
}

export const Skeleton = memo(function Skeleton({
  className = '',
  variant = 'text',
  width,
  height,
  lines = 1,
}: SkeletonProps) {
  const baseClass = 'animate-pulse bg-gray-700/50 rounded';

  const variantClass = {
    text: 'h-4',
    rectangular: '',
    circular: 'rounded-full',
  }[variant];

  const style: React.CSSProperties = {
    width: width,
    height: height,
  };

  if (lines > 1) {
    return (
      <div className={`space-y-2 ${className}`}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={`${baseClass} ${variantClass}`}
            style={{
              ...style,
              width: i === lines - 1 ? '75%' : width,
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`${baseClass} ${variantClass} ${className}`}
      style={style}
    />
  );
});

// Pre-built skeleton components for common use cases
export const AgentCardSkeleton = memo(function AgentCardSkeleton() {
  return (
    <div className="p-4 bg-gray-800 border border-gray-700 rounded-lg space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Skeleton variant="circular" width={8} height={8} />
          <Skeleton width={120} />
        </div>
        <Skeleton width={60} height={20} variant="rectangular" />
      </div>

      {/* Prompt preview */}
      <Skeleton lines={2} />

      {/* Footer */}
      <div className="flex items-center justify-between">
        <Skeleton width={80} />
        <div className="flex gap-2">
          <Skeleton width={24} height={24} variant="rectangular" />
          <Skeleton width={24} height={24} variant="rectangular" />
        </div>
      </div>
    </div>
  );
});

export const AgentListSkeleton = memo(function AgentListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <AgentCardSkeleton key={i} />
      ))}
    </div>
  );
});

export const AgentDetailSkeleton = memo(function AgentDetailSkeleton() {
  return (
    <div className="flex flex-col h-full">
      {/* Header skeleton */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Skeleton variant="circular" width={10} height={10} />
            <Skeleton width={150} height={24} />
          </div>
          <div className="flex items-center gap-2">
            <Skeleton width={80} height={28} variant="rectangular" />
            <Skeleton width={32} height={28} variant="rectangular" />
          </div>
        </div>

        {/* Info row */}
        <div className="mt-3 flex items-center gap-4">
          <Skeleton width={100} />
          <Skeleton width={120} />
        </div>
      </div>

      {/* Content skeleton */}
      <div className="flex-1 p-4 space-y-4">
        <Skeleton lines={3} />
        <Skeleton height={100} variant="rectangular" />
        <Skeleton lines={4} />
        <Skeleton height={80} variant="rectangular" />
      </div>
    </div>
  );
});

export const OutputStreamSkeleton = memo(function OutputStreamSkeleton() {
  return (
    <div className="p-4 space-y-3">
      {/* System message */}
      <div className="p-3 bg-gray-800/50 rounded-lg">
        <Skeleton width={100} height={12} className="mb-2" />
        <Skeleton lines={2} />
      </div>

      {/* Assistant message */}
      <div className="p-3 bg-blue-900/20 rounded-lg">
        <Skeleton width={80} height={12} className="mb-2" />
        <Skeleton lines={4} />
      </div>

      {/* Tool use */}
      <div className="p-3 bg-purple-900/20 rounded-lg">
        <Skeleton width={120} height={12} className="mb-2" />
        <Skeleton height={60} variant="rectangular" />
      </div>
    </div>
  );
});

export default Skeleton;
