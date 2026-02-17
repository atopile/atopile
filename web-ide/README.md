# atopile Web IDE

Browser-based VS Code environment for atopile using [OpenVSCode Server](https://github.com/gitpod-io/openvscode-server) (MIT licensed).

## Quick Start

```bash
cd web-ide
docker compose up --build

# Open https://localhost:3443
```

That's it. The Docker build compiles everything from source (wheel + extension) — no pre-build steps needed.

## What's Included

- **OpenVSCode Server 1.105.1** — full VS Code in the browser
- **Pre-installed atopile extension** — syntax highlighting, LSP, webviews
- **Python 3.14** with atopile CLI via uv
- **KiCad 9.0.7** for PCB workflows (headless)
- **Example project** — a quickstart `.ato` project seeded on first run

## Directory Structure

```
web-ide/
├── README.md                 # This file
├── PLAN.md                   # Implementation details
├── Dockerfile                # 4-stage multi-stage build
├── docker-compose.yml        # Local development setup
├── .gitignore
├── scripts/
│   ├── build-artifacts.sh    # Optional: local wheel + VSIX build
│   ├── install-extensions.sh # Installs extensions in container
│   ├── entrypoint.sh         # Container entrypoint (workspace init + server)
│   └── settings.json         # Default VS Code settings
└── workspace/                # Default example project (bundled in image)
    ├── ato.yaml
    └── quickstart.ato
```

## How It Works

The Dockerfile uses a **4-stage multi-stage build**:

1. **OpenVSCode Server** — pulls the base editor image
2. **Wheel builder** — compiles the atopile Python wheel from source (with native Zig extensions)
3. **VSIX builder** — builds the VS Code extension from source
4. **Final image** — assembles everything on a KiCad base

This approach ensures the correct platform binaries are always produced, even when building on macOS for a Linux container.

## Local Development

### Prerequisites

- Docker and Docker Compose (that's it!)

### Run

```bash
cd web-ide
docker compose up --build
```

Podman control script (recommended for this repo):

```bash
cd web-ide
cp .env.example .env   # first time only; then edit values
./scripts/web-idectl.sh start
./scripts/web-idectl.sh status
./scripts/web-idectl.sh stop
```

Access at:
- `https://localhost:3443` (required for reliable webviews on non-loopback hosts)
- `https://<machine-ip>:3443` (direct IP access also supported)

If you need remote access from other machines, publish on all interfaces
and set the external hostname/IP used by clients:

```bash
WEB_IDE_BIND_ADDR=0.0.0.0 \
WEB_IDE_HTTPS_PORT=3443 \
WEB_IDE_PUBLIC_HOST=100.118.104.116 \
docker compose up --build
```

Then open inbound firewall/security-group rules for your chosen host ports.

### Podman Notes (Rootless)

- Do not mix `podman` and `sudo podman` for the same compose project.
  - Rootless and rootful runtimes keep separate container state and can conflict on host ports.
- On some rootless setups, foreground `podman compose up` may fail with a `crun ... exec.fifo` error when the service is already running.
  - Use `podman compose up -d` to start/recreate.
  - Use `podman compose logs -f` to follow logs.

### Rebuild After Changes

```bash
docker compose up --build --force-recreate
```

### Bind-Mount Your Own Workspace

To work on a local project instead of the built-in example:

```bash
docker compose run --rm \
  -v "$(pwd)/my-project:/home/openvscode-server/workspace" \
  -p 3443:3443 \
  atopile-web-ide
```

### Optional: Build Artifacts Locally

The `build-artifacts.sh` script builds the wheel and VSIX on your host machine. This is **not needed** for Docker builds (the Dockerfile handles it), but useful for testing:

```bash
./scripts/build-artifacts.sh
```

Note: the wheel is platform-specific to your host OS and won't work in Docker.

## Testing Checklist

- [ ] Container starts and is accessible at port 3443
- [ ] IDE opens in workspace with example project
- [ ] atopile extension is installed and activated
- [ ] Python extension works
- [ ] `ato --version` works in terminal
- [ ] `ato build` works on the example project
- [ ] LSP features work (completion, hover, go-to-definition)
- [ ] Sidebar webview renders correctly

## Verification Commands

```bash
# Check container is running
docker ps | grep atopile-web-ide

# Check installed extensions
docker exec atopile-web-ide /home/.openvscode-server/bin/openvscode-server --list-extensions

# Check atopile version
docker exec atopile-web-ide ato --version

# View logs
docker logs -f atopile-web-ide
```

## Security Note

OpenVSCode Server has **no built-in authentication**. The local setup is intended for development only. For production, deploy behind an authentication proxy (OAuth2 Proxy, Authelia, Cloudflare Access, etc.).

## CI/CD

The GitHub Actions workflow (`.github/workflows/web-ide.yml`) automatically builds and publishes the container image to GHCR on releases.

```bash
# Pull the published image
docker pull ghcr.io/atopile/atopile-web-ide:latest

# Run it
docker run -p 3443:3443 ghcr.io/atopile/atopile-web-ide:latest
```
