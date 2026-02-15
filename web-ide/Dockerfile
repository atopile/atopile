# OpenVSCode Server with atopile pre-configured
# Based on: https://github.com/gitpod-io/openvscode-server
#
# Build context must be the REPO ROOT (not web-ide/).
# Example: docker build -f web-ide/Dockerfile .

ARG OPENVSCODE_VERSION=1.105.1
ARG KICAD_VERSION=9.0.7
ARG ATOPILE_VERSION=0.0.0dev

# ──────────────────────────────────────────────────────────────────
# Stage 1: OpenVSCode Server
# ──────────────────────────────────────────────────────────────────
FROM gitpod/openvscode-server:${OPENVSCODE_VERSION} AS openvscode

# ──────────────────────────────────────────────────────────────────
# Stage 1b: Caddy reverse proxy (for WebSocket routing)
# ──────────────────────────────────────────────────────────────────
FROM docker.io/library/caddy:2 AS caddy

# ──────────────────────────────────────────────────────────────────
# Stage 2: Build atopile Python wheel from source
# ──────────────────────────────────────────────────────────────────
FROM ubuntu:24.04 AS wheel-builder

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG ATOPILE_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${ATOPILE_VERSION}

# Copy only what's needed for the wheel build
COPY pyproject.toml /src/pyproject.toml
COPY LICENSE /src/LICENSE
COPY README.md /src/README.md
COPY src/faebryk /src/src/faebryk
COPY src/atopile /src/src/atopile

WORKDIR /src
RUN uv build --wheel --out-dir /wheels

# ──────────────────────────────────────────────────────────────────
# Stage 3: Build VS Code extension (VSIX)
# ──────────────────────────────────────────────────────────────────
FROM node:20-slim AS vsix-builder

WORKDIR /src

# Copy both vscode-atopile and ui-server (webviews build needs ui-server)
COPY src/vscode-atopile /src/src/vscode-atopile
COPY src/ui-server /src/src/ui-server

# Install deps and build webviews + extension
WORKDIR /src/src/vscode-atopile
RUN npm ci && \
    npm run vscode:prepublish && \
    mkdir -p /vsix && \
    npx vsce package --out /vsix/

# ──────────────────────────────────────────────────────────────────
# Stage 4: Final image on KiCad base
# ──────────────────────────────────────────────────────────────────
FROM ghcr.io/kicad/kicad:${KICAD_VERSION}

# KiCad image may use a non-root user; switch to root for system setup
USER root

# Environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOME=/home/openvscode-server
ENV OPENVSCODE_SERVER_ROOT=/home/.openvscode-server
ENV PATH=${OPENVSCODE_SERVER_ROOT}/bin:${HOME}/.local/bin:$PATH
# Backend server: bind to localhost only (accessed via extension, not exposed externally)
ENV ATOPILE_BACKEND_HOST=127.0.0.1
ENV ATOPILE_BACKEND_PORT=8501

# Install runtime + build dependencies + VNC stack for PCBnew viewer
# Note: build-essential/cmake are needed because pynng (transitive dep) compiles from source
# Note: curl and xdotool removed — not needed at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    build-essential \
    cmake \
    xserver-xorg-video-dummy \
    x11-xserver-utils \
    x11vnc \
    openbox \
    websockify \
    novnc \
    && rm -rf /var/lib/apt/lists/*

# Install restricted shell (disables terminal access for the user)
COPY web-ide/scripts/restricted-shell.sh /usr/local/bin/restricted-shell.sh
RUN chmod +x /usr/local/bin/restricted-shell.sh

# Create non-root user with restricted shell (extension commands use /bin/bash explicitly)
RUN useradd -m -s /usr/local/bin/restricted-shell.sh -d ${HOME} openvscode-server && \
    mkdir -p ${OPENVSCODE_SERVER_ROOT} && \
    chown -R openvscode-server:openvscode-server ${HOME} ${OPENVSCODE_SERVER_ROOT}

# Copy OpenVSCode Server from stage 1
COPY --from=openvscode --chown=openvscode-server:openvscode-server \
    /home/.openvscode-server ${OPENVSCODE_SERVER_ROOT}

# Install Caddy reverse proxy (routes /ws/* to backend, everything else to OpenVSCode)
COPY --from=caddy /usr/bin/caddy /usr/local/bin/caddy

# Install uv for Python management
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

# Copy built artifacts from builder stages
COPY --from=wheel-builder --chown=openvscode-server:openvscode-server \
    /wheels/*.whl /tmp/artifacts/
COPY --from=vsix-builder --chown=openvscode-server:openvscode-server \
    /vsix/*.vsix /tmp/artifacts/

# Copy scripts, branding, and default workspace
COPY --chown=openvscode-server:openvscode-server \
    web-ide/scripts/ /tmp/scripts/
COPY --chown=openvscode-server:openvscode-server \
    web-ide/branding/ /tmp/branding/
COPY --chown=openvscode-server:openvscode-server \
    web-ide/workspace/ /tmp/default-workspace/

# ---------- Switch to non-root user for all remaining operations ----------
USER openvscode-server
WORKDIR ${HOME}

# Install atopile from wheel (installs to ~/.local/bin, which is in PATH)
# Must match requires-python in pyproject.toml (>=3.14,<3.15)
RUN uv tool install --python 3.14 /tmp/artifacts/atopile-*.whl

# Install VS Code extensions
RUN /tmp/scripts/install-extensions.sh

# Apply atopile branding (favicon, title, manifest)
RUN /tmp/branding/apply-branding.sh

# Copy default VS Code settings (runtime data dir is $HOME/.openvscode-server/data/,
# NOT $OPENVSCODE_SERVER_ROOT/data/ — the install-extensions.sh step already creates this tree)
RUN cp /tmp/scripts/settings.json ${HOME}/.openvscode-server/data/Machine/settings.json

# Note: uv symlink is created by entrypoint.sh on each startup because the
# User data volume mount shadows this directory on subsequent container starts

# Set up entrypoint and VNC startup script
RUN mkdir -p ${HOME}/.local/etc && \
    cp /tmp/scripts/entrypoint.sh ${HOME}/.local/bin/entrypoint.sh && \
    cp /tmp/scripts/start-pcbnew-vnc.sh ${HOME}/.local/bin/start-pcbnew-vnc.sh && \
    cp /tmp/scripts/Caddyfile ${HOME}/.local/etc/Caddyfile && \
    chmod +x ${HOME}/.local/bin/entrypoint.sh ${HOME}/.local/bin/start-pcbnew-vnc.sh

# Create workspace directory
RUN mkdir -p ${HOME}/workspace

# Clean up build artifacts (keep default-workspace for entrypoint seeding)
RUN rm -rf /tmp/artifacts /tmp/scripts /tmp/branding

# Expose Caddy's port (OpenVSCode on 3001 and backend on 8501 are internal only)
EXPOSE 3000

# Health check (uses Python since curl is not installed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/')" || exit 1

# Entrypoint seeds workspace on first run, then starts Caddy + OpenVSCode Server
ENTRYPOINT ["entrypoint.sh"]
CMD ["--host", "127.0.0.1", "--port", "3001", "--without-connection-token", \
     "--disable-workspace-trust", \
     "--default-folder", "/home/openvscode-server/workspace"]
