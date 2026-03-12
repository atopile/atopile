import {
  Plug,
  Box,
  Cpu,
  SlidersHorizontal,
  Sparkles,
} from 'lucide-react'
import './TypeIcon.css'

/**
 * Returns the appropriate lucide icon for an ato type.
 * Used by StructurePanel, LibraryPanel, and other tree views.
 */
export function typeIcon(itemType: string, size = 12) {
  switch (itemType) {
    case 'interface': return <Plug size={size} />
    case 'module': return <Box size={size} />
    case 'component': return <Cpu size={size} />
    case 'parameter': return <SlidersHorizontal size={size} />
    case 'trait': return <Sparkles size={size} />
    default: return <Box size={size} />
  }
}
