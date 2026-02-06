# OpenVSCode Server Implementation Plan

## Overview

Self-hosted, browser-based VS Code environment for atopile using [OpenVSCode Server](https://github.com/gitpod-io/openvscode-server) (MIT licensed).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    User's Browser                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              OpenVSCode Server (Web UI)                    │  │
│  │  - atopile extension (from local VSIX)                     │  │
│  │  - Python extension                                        │  │
│  │  - Syntax highlighting, LSP, webviews                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP (port 3000)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Docker Container: atopile-web-ide                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  OpenVSCode Server v1.106.3 (port 3000)                   │  │
│  │  - Extensions: atopile (VSIX), Python                      │  │
│  │  - Default folder: /home/openvscode-server/workspace       │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  atopile CLI + LSP Server                                  │  │
│  │  - Python 3.13 via uv (installed as non-root user)        │  │
│  │  - atopile installed from wheel built in Docker            │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  KiCad 9.0.7 (headless)                                   │  │
│  │  - For PCB generation and export                           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | 4-stage build: OpenVSCode + wheel builder + VSIX builder + final |
| `docker-compose.yml` | Local development/testing |
| `scripts/build-artifacts.sh` | Optional: builds wheel + VSIX locally (host-native) |
| `scripts/install-extensions.sh` | Installs extensions inside container |
| `scripts/entrypoint.sh` | Container entrypoint: workspace init + server launch |
| `scripts/settings.json` | Default VS Code settings |
| `workspace/` | Default example project (bundled in image, seeded on first run) |
| `../.dockerignore` | Keeps Docker build context small (at repo root) |

## Build Process

### Multi-Stage Docker Build

The Dockerfile builds everything from source inside Docker — no pre-built
artifacts needed. This guarantees correct platform binaries (works from macOS
building a Linux container).

**Stage 1** — Pull OpenVSCode Server image

**Stage 2** — Build atopile wheel from source:
- Uses `uv` + build deps (cmake, build-essential)
- `SETUPTOOLS_SCM_PRETEND_VERSION` provides the version (no .git needed)
- Produces a Linux wheel with native Zig extensions

**Stage 3** — Build VS Code extension:
- Uses Node.js 20 to compile webviews and package VSIX
- Platform-independent output

**Stage 4** — Assemble final image on KiCad base:
- Copies wheel and VSIX from builder stages
- Installs atopile as non-root user (`~/.local/bin`)
- Installs extensions, settings, entrypoint
- Cleans up build artifacts

### Why Build From Source?

- atopile contains native Zig extensions → the wheel is platform-specific
- Building on macOS produces a macOS wheel that won't run in Linux containers
- Building inside Docker always produces the correct platform wheel
- No external build steps needed — just `docker compose up --build`
- CI and local dev use the same build process

## Dockerfile Details

Key design decisions:
- **KiCad as base** ensures full PCB workflow support (schematic export, DRC, etc.)
- **Non-root user** for all install steps after system packages
- **Entrypoint script** seeds the workspace on first run (when volumes are mounted empty)
- **`--default-folder`** opens the IDE directly in the workspace directory
- **Cleanup step** removes `/tmp/artifacts` and `/tmp/scripts` after install

## Implementation Checklist

- [x] Create `scripts/build-artifacts.sh` (optional local builds)
- [x] Create `scripts/install-extensions.sh`
- [x] Create `scripts/settings.json`
- [x] Create `scripts/entrypoint.sh`
- [x] Create `Dockerfile` (4-stage multi-stage build)
- [x] Create `docker-compose.yml`
- [x] Create `.github/workflows/web-ide.yml`
- [x] Create `workspace/` example project
- [x] Add `.dockerignore` at repo root
- [ ] Test locally: `cd web-ide && docker compose up --build`
- [ ] Verify all test cases

## Testing

```bash
cd web-ide
docker compose up --build

# Open http://localhost:3000
```

### Test Cases

1. **Container Health**
   - Container starts without errors
   - Health check passes
   - Port 3000 is accessible

2. **Workspace**
   - IDE opens in workspace directory
   - Example `quickstart.ato` is present
   - `ato.yaml` is present

3. **Extension**
   - atopile extension appears in Extensions view
   - Extension activates on `.ato` file open
   - Sidebar webview renders

4. **CLI**
   - `ato --version` returns correct version
   - `ato build` works on the example project

5. **LSP**
   - Syntax highlighting works
   - Hover shows type info
   - Go-to-definition works
   - Completion works

6. **Webviews**
   - Sidebar renders
   - 3D viewer loads (if applicable)
   - KiCanvas preview works

## CI/CD

GitHub Actions workflow builds and pushes to GHCR:
- Triggered on releases and manual dispatch
- Version extracted from git tags via `SETUPTOOLS_SCM_PRETEND_VERSION`
- Multi-stage Docker build (no separate artifact steps)
- Docker layer caching via GitHub Actions cache
- Tagged with version and `latest`
- Configurable OpenVSCode and KiCad versions via workflow inputs

## Licenses

| Component | License | Commercial OK |
|-----------|---------|---------------|
| OpenVSCode Server | MIT | Yes |
| KiCad | GPL | Yes (runtime) |
| atopile | MIT | Yes |
| uv | MIT | Yes |

All components are compatible with commercial hosting.

## Security

OpenVSCode Server has **no built-in authentication**. For production deployments,
place behind an authentication proxy (OAuth2 Proxy, Authelia, Cloudflare Access, etc.).
