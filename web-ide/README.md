# Web IDE Layout

The `web-ide/` directory is split into two subprojects:

- `ws/` — the workspace runtime image (OpenVSCode + atopile)
- `spawner/` — the playground/spawner service used to provision workspaces

## Workspace Runtime (`ws/`)

```bash
cd web-ide/ws
docker compose up --build
```

Main docs:

- `web-ide/ws/README.md`
- `web-ide/ws/ARCH.md`
- `web-ide/ws/TESTING.md`

## Spawner (`spawner/`)

```bash
cd web-ide/spawner
uv run main.py server start
```

Main docs:

- `web-ide/spawner/README.md`
