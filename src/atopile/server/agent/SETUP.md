# Agent & DeepPCB Autolayout Setup

How to configure the atopile server-side agent and DeepPCB autolayout features.

## Quick start

Add these to your `~/.zshrc` (or `~/.bashrc`):

```sh
# --- Required ---

# Agent LLM calls (powers /api/agent endpoints and agent tools)
export OPENAI_API_KEY="sk-..."
# or use the namespaced variant (takes priority if both set):
# export ATOPILE_AGENT_OPENAI_API_KEY="sk-..."

# DeepPCB autolayout (powers /api/autolayout and autolayout_* agent tools)
export ATO_DEEPPCB_API_KEY="your-deeppcb-key"

# Enable the chat panel in the UI sidebar (defaults to off)
# Option A: VS Code setting (recommended) — set atopile.enableChat to true
# Option B: Environment variable (for non-VS-Code or CI use)
export UI_ENABLE_CHAT=1

# --- Optional ---

# Exa web search (used by some agent research flows)
export EXA_API_KEY="..."
# or:
# export ATOPILE_AGENT_EXA_API_KEY="..."

# Feature gate — autolayout is enabled by default
# export ATO_ENABLE_AUTOLAYOUT=true
```

Then reload your shell:

```sh
source ~/.zshrc
```

## How it works

### Agent

The agent orchestrator (`orchestrator.py`) uses the OpenAI API to drive a
tool-calling loop. It reads all config from environment variables at startup.

| Variable | Default | What it does |
|---|---|---|
| `OPENAI_API_KEY` | — | **Required.** LLM API key |
| `ATOPILE_AGENT_OPENAI_API_KEY` | — | Takes priority over `OPENAI_API_KEY` |
| `ATOPILE_AGENT_BASE_URL` | `https://api.openai.com/v1` | API base URL (for proxies or compatible providers) |
| `ATOPILE_AGENT_MODEL` | `gpt-5.3-codex` | Model identifier |
| `ATOPILE_AGENT_TIMEOUT_S` | `120` | Per-request timeout (seconds) |
| `ATOPILE_AGENT_MAX_TOOL_LOOPS` | `240` | Max tool invocations per turn |
| `ATOPILE_AGENT_MAX_TURN_SECONDS` | `480` | Max wall-clock time per turn (clamped 30–3600) |

Skills are loaded from `.claude/skills/` relative to the repo root.

### DeepPCB autolayout

The DeepPCB client (`src/faebryk/libs/deeppcb.py`) uses pydantic-settings and
reads from env vars with the `ATO_DEEPPCB_` prefix. Only the API key is required;
all endpoint paths and timeouts have sensible defaults.

| Variable | Default | What it does |
|---|---|---|
| `ATO_DEEPPCB_API_KEY` | — | **Required.** DeepPCB API key |
| `ATO_DEEPPCB_BASE_URL` | `https://api.deeppcb.ai` | API base URL |
| `ATO_DEEPPCB_TIMEOUT_S` | `60` | HTTP request timeout |
| `ATO_DEEPPCB_BOARD_READY_TIMEOUT_S` | `90` | Max wait for board-ready status |
| `ATO_DEEPPCB_BOARD_READY_POLL_S` | `2` | Polling interval while waiting |
| `ATO_DEEPPCB_WEBHOOK_URL` | — | Optional webhook for board status updates |
| `ATO_DEEPPCB_WEBHOOK_TOKEN` | — | Auth token sent with webhook calls |

Alternate prefixes `DEEPPCB_` and `FBRK_DEEPPCB_` also work for all settings.

### Feature gates

| Variable | Default | What it does |
|---|---|---|
| `UI_ENABLE_CHAT` | `false` | **Set to `1` to enable the chat panel** in the UI sidebar. In VS Code, prefer the `atopile.enableChat` setting instead. |
| `ATO_ENABLE_AUTOLAYOUT` | `true` | Set to `false` to disable autolayout endpoints entirely |

## Per-project autolayout config (ato.yaml)

Autolayout can also be configured per build target in `ato.yaml`:

```yaml
build-targets:
  - name: my_board
    entry: main
    autolayout:
      provider: deeppcb
      objective: balanced
      candidate_count: 3
      auto_apply: false
```

## Advanced agent tuning

These are rarely needed but available for debugging or resource-constrained
environments. All are read from environment variables.

| Variable | Default | Notes |
|---|---|---|
| `ATOPILE_AGENT_API_RETRIES` | `4` | Retry count on transient API errors |
| `ATOPILE_AGENT_API_RETRY_BASE_DELAY_S` | `0.5` | Exponential backoff base |
| `ATOPILE_AGENT_API_RETRY_MAX_DELAY_S` | `8.0` | Backoff ceiling |
| `ATOPILE_AGENT_CONTEXT_COMPACT_THRESHOLD` | `120000` | Chars before context compaction |
| `ATOPILE_AGENT_CONTEXT_HARD_MAX_TOKENS` | `170000` | Hard token limit |
| `ATOPILE_AGENT_TRACE_ENABLED` | `1` | Set to `0` to disable trace logging |
| `ATOPILE_AGENT_WORKER_LOOP_GUARD_WINDOW` | `8` | Loop-detection sliding window (4–24) |
| `ATOPILE_AGENT_WORKER_FAILURE_STREAK_LIMIT` | `6` | Max consecutive failures before stop (2–20) |
| `ATOPILE_AGENT_WORKER_NO_PROGRESS_LOOP_LIMIT` | `18` | Max loops without progress (4–60) |

## Verifying your setup

```sh
# Check all required vars are set
echo "OPENAI_API_KEY: $([ -n "$OPENAI_API_KEY" ] && echo 'set' || echo 'MISSING')"
echo "ATO_DEEPPCB_API_KEY: $([ -n "$ATO_DEEPPCB_API_KEY" ] && echo 'set' || echo 'MISSING')"

# Start the server and verify agent health
ato server
# then in another terminal:
curl http://localhost:8367/api/agent/health
```

## Troubleshooting

- **"Autolayout is disabled via ATO_ENABLE_AUTOLAYOUT"** — set `ATO_ENABLE_AUTOLAYOUT=true`
  or unset it (defaults to enabled).
- **Agent returns empty/error** — verify `OPENAI_API_KEY` is valid and has access to the
  configured model (`ATOPILE_AGENT_MODEL`, default `gpt-5.3-codex`).
- **DeepPCB 401/403** — your `ATO_DEEPPCB_API_KEY` is invalid or expired. Get a new one
  from the DeepPCB dashboard.
- **Timeout on autolayout** — increase `ATO_DEEPPCB_TIMEOUT_S` and
  `ATO_DEEPPCB_BOARD_READY_TIMEOUT_S` for large boards.
