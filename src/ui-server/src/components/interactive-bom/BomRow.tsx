import { memo, useCallback } from 'react';
import type { BomGroup, BomEnrichment } from './types';

interface BomRowProps {
  group: BomGroup;
  enrichment: BomEnrichment | null;
  isSelected: boolean;
  isHovered: boolean;
  onSelect: (groupId: string) => void;
  onHover: (groupId: string | null) => void;
}

export const BomRow = memo(function BomRow({
  group,
  enrichment,
  isSelected,
  isHovered,
  onSelect,
  onHover,
}: BomRowProps) {
  const handleClick = useCallback(() => onSelect(group.id), [onSelect, group.id]);
  const handleMouseEnter = useCallback(() => onHover(group.id), [onHover, group.id]);
  const handleMouseLeave = useCallback(() => onHover(null), [onHover]);

  let className = 'ibom-row';
  if (isSelected) className += ' ibom-row-selected';
  if (isHovered) className += ' ibom-row-hovered';

  const displayValue = group.value || enrichment?.mpn || '-';

  return (
    <div
      className={className}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      role="row"
      tabIndex={-1}
    >
      <span className="ibom-row-qty">{group.quantity}</span>
      <span className="ibom-row-designators">{group.designators.join(', ') || '-'}</span>
      <span className="ibom-row-value">{displayValue}</span>
    </div>
  );
});
