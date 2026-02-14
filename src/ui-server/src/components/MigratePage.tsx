import { MigrateDialog } from './MigrateDialog'
import { postToExtension } from '../api/vscodeApi'

interface MigratePageProps {
  projectRoot: string
}

export function MigratePage({ projectRoot }: MigratePageProps) {
  const handleClose = () => {
    // Ask the extension to close this webview panel
    postToExtension({ type: 'closeMigrateTab' })
  }

  if (!projectRoot) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        color: 'var(--vscode-foreground)',
        fontFamily: 'var(--vscode-font-family)',
      }}>
        <p>No project root specified.</p>
      </div>
    )
  }

  return (
    <div style={{ height: '100vh', overflow: 'hidden' }}>
      <MigrateDialog projectRoot={projectRoot} onClose={handleClose} />
    </div>
  )
}
