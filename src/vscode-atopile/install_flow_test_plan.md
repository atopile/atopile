# @vscode-atopile install flow review + test plan

## Scope
Covers the extension install/bootstrap flow: auto-install of `ato` via uv, LSP startup, backend server startup, and config-driven overrides (`atopile.ato`, `atopile.from`, `atopile.autoInstall`).

## Findings (from code review)
- Auto-install can be marked failed before it runs: `initServer()` immediately fires a restart, which calls `startOrRestartServer()` and reports an error when `getAtoBin()` is null, even though `setup.activate()` runs later and may succeed.
  - `src/vscode-atopile/src/common/server.ts:182`
  - `src/vscode-atopile/src/extension.ts:88-123`
  - `src/vscode-atopile/src/ui/setup.ts:126-167`
- `atopile.autoInstall=false` silently exits without prompt or guidance (commented-out dialog), leaving the extension idle.
  - `src/vscode-atopile/src/ui/setup.ts:144-163`
- uv invocation hardcodes Python `-p 3.13`; systems that cannot provision 3.13 will fail even if other versions would work.
  - `src/vscode-atopile/src/common/findbin.ts:105-118`
- `getAtoCommand()` uses single-quote wrapping for paths with spaces; this is POSIX-centric and can break on Windows terminal shells.
  - `src/vscode-atopile/src/common/findbin.ts:45-50`

## Test plan

### 1) Fresh install, autoInstall=true
- Preconditions:
  - No `atopile.ato` or `atopile.from` configured.
  - No extension-managed uv in global storage.
  - Clean VS Code/Cursor profile.
- Steps:
  - Open a workspace containing `ato.yaml` to activate the extension.
  - Observe the progress notification.
- Expected:
  - uv is downloaded and extracted.
  - `getAtoBin()` self-check succeeds.
  - “Installed atopile via uv” info message is shown.
  - LSP starts successfully.
  - Backend server becomes healthy.
  - App state shows `installing=false` with no error.

### 2) autoInstall=false with no ato configured
- Preconditions:
  - `atopile.autoInstall=false`.
  - No `atopile.ato` or `atopile.from`.
- Steps:
  - Activate extension.
- Expected (current behavior):
  - No install attempt and no prompt.
  - LSP fails to start (error logged).
  - Document as expected or adjust UX if needed.

### 3) Valid `atopile.ato` path
- Preconditions:
  - `atopile.ato` points to a valid `ato` binary.
- Steps:
  - Activate extension.
- Expected:
  - No uv download.
  - LSP and backend server start.

### 4) Invalid `atopile.ato` path
- Preconditions:
  - `atopile.ato` points to a non-existent file.
- Steps:
  - Activate extension.
- Expected:
  - Error logged for invalid path.
  - Auto-install runs if enabled.

### 5) `atopile.from` variants
- Preconditions:
  - `atopile.ato` unset.
- Steps:
  - Set `atopile.from` to `atopile@<version>`; activate.
  - Set `atopile.from` to `git+https://github.com/atopile/atopile.git@main`; activate.
- Expected:
  - uv uses `--from <value>`.
  - `ato self-check` reflects the selected version.
  - LSP and backend use the selected version.

### 6) Settings change → restart behavior
- Steps:
  - Change `atopile.from` or `atopile.ato` while extension is active.
- Expected:
  - `onDidChangeAtoBinInfo` fires.
  - LSP restarts and backend server restarts.
  - No stale version remains.

### 7) Race: install vs initial LSP start
- Preconditions:
  - Fresh install with slow network.
- Steps:
  - Activate extension.
- Expected (current behavior):
  - Possible early error from initial LSP start before install completes.
  - After install, restart should recover.

### 8) Network failure for uv download
- Preconditions:
  - Block GitHub release download.
- Steps:
  - Activate extension.
- Expected:
  - Error toast “Failed to install uv…”.
  - Extension does not crash and remains idle.

### 9) Windows path with spaces
- Preconditions:
  - Windows machine with space in user profile path, or `atopile.ato` path containing spaces.
- Steps:
  - Trigger backend server start and a terminal command (e.g., build).
- Expected:
  - Command quoting is accepted by the terminal shell.

### 10) Reinstall/cleanup
- Steps:
  - Remove extension-managed uv (`globalStorage/uv-bin`) and restart IDE.
- Expected:
  - uv is re-downloaded and install completes.

## Notes
- For structured test reporting, prefer `ato dev test --llm` when adding automated coverage.
