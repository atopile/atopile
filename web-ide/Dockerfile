# OpenVSCode Server with atopile pre-configured
# Based on: https://github.com/gitpod-io/openvscode-server
#
# Build context must be the REPO ROOT (not web-ide/).
# Example: docker build -f web-ide/Dockerfile .

ARG OPENVSCODE_VERSION=1.106.3
ARG KICAD_VERSION=9.0.7
ARG ATOPILE_VERSION=0.0.0dev

# ──────────────────────────────────────────────────────────────────
# Stage 1: OpenVSCode Server
# ──────────────────────────────────────────────────────────────────
FROM gitpod/openvscode-server:${OPENVSCODE_VERSION} AS openvscode

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
    npx vsce package --out /vsix/

# ──────────────────────────────────────────────────────────────────
# Stage 4: Final image on KiCad base
# ──────────────────────────────────────────────────────────────────
FROM ghcr.io/kicad/kicad:${KICAD_VERSION}

# Environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOME=/home/openvscode-server
ENV OPENVSCODE_SERVER_ROOT=/home/.openvscode-server
ENV PATH=${OPENVSCODE_SERVER_ROOT}/bin:${HOME}/.local/bin:$PATH

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash -d ${HOME} openvscode-server && \
    mkdir -p ${OPENVSCODE_SERVER_ROOT} && \
    chown -R openvscode-server:openvscode-server ${HOME}

# Copy OpenVSCode Server from stage 1
COPY --from=openvscode --chown=openvscode-server:openvscode-server \
    /home/.openvscode-server ${OPENVSCODE_SERVER_ROOT}

# Install uv for Python management
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

# Copy built artifacts from builder stages
COPY --from=wheel-builder --chown=openvscode-server:openvscode-server \
    /wheels/*.whl /tmp/artifacts/
COPY --from=vsix-builder --chown=openvscode-server:openvscode-server \
    /vsix/*.vsix /tmp/artifacts/

# Copy scripts and default workspace
COPY --chown=openvscode-server:openvscode-server \
    web-ide/scripts/ /tmp/scripts/
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

# Copy default VS Code settings
RUN mkdir -p ${OPENVSCODE_SERVER_ROOT}/data/Machine && \
    cp /tmp/scripts/settings.json ${OPENVSCODE_SERVER_ROOT}/data/Machine/settings.json

# Set up entrypoint
RUN cp /tmp/scripts/entrypoint.sh ${HOME}/.local/bin/entrypoint.sh && \
    chmod +x ${HOME}/.local/bin/entrypoint.sh

# Create workspace directory
RUN mkdir -p ${HOME}/workspace

# Clean up build artifacts (keep default-workspace for entrypoint seeding)
RUN rm -rf /tmp/artifacts /tmp/scripts

# Expose OpenVSCode Server port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Entrypoint seeds workspace on first run, then starts server
ENTRYPOINT ["entrypoint.sh"]
CMD ["--host", "0.0.0.0", "--port", "3000", "--without-connection-token", \
     "--default-folder", "/home/openvscode-server/workspace"]
