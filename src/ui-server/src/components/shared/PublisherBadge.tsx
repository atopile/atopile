/**
 * PublisherBadge - Displays package publisher with special styling for official packages.
 */

import './PublisherBadge.css'

interface PublisherBadgeProps {
  /** Publisher name (e.g., "atopile", "vendor") */
  publisher: string
  /** Optional: show "by" prefix */
  showPrefix?: boolean
}

export function PublisherBadge({ publisher, showPrefix = false }: PublisherBadgeProps) {
  const isOfficial = publisher.toLowerCase() === 'atopile'

  return (
    <span className={`publisher-badge ${isOfficial ? 'official' : ''}`}>
      {showPrefix && <span className="publisher-prefix">by </span>}
      {publisher.toLowerCase()}
    </span>
  )
}
