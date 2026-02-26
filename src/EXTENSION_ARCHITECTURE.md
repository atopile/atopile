# Extension Architecture

```mermaid
flowchart LR
  subgraph EXTPROC["Extension Host (Node)"]
    EXT["Extension"]
  end

  subgraph WEBVIEWS["Webview Processes (Chromium)"]
    WV1["Sidebar"]
    WV2@{ shape: st-rect, label: "Panels (N)" }
  end

  subgraph HUB["UI Hub (Node)"]
    UIWS["WS Server<br/>/atopile-ui"]
    STORE["Store<br/>(module singleton)"]
    COREWS["WS Client<br/>→ /atopile-core"]
    UIWS <--> STORE
    STORE <--> COREWS
  end

  subgraph CORE["Core Server (Python)"]
    WSS["WS Server<br/>/atopile-core"]
    SVC["Build queue<br/>Project discovery"]
    WSS <--> SVC
  end

  EXT -.->|"spawns"| HUB
  EXT -.->|"spawns"| CORE
  EXT -.->|"spawns"| WV1
  EXT -.->|"spawns"| WV2

  WV1 -->|"subscribe"| UIWS
  WV1 -->|"action"| UIWS
  UIWS -->|"state"| WV1

  WV2 -->|"subscribe"| UIWS
  WV2 -->|"action"| UIWS
  UIWS -->|"state"| WV2

  COREWS -->|"action"| WSS
  WSS -->|"state"| COREWS

  subgraph LEGEND[" "]
    direction LR
    L1["A"] -.->|"lifecycle"| L2["B"]
    L3["A"] -->|"websocket"| L4["B"]
  end

  classDef state fill:#e3f2fd,color:#0d47a1
  classDef legend fill:none,stroke:none
  class UIWS,STORE,COREWS,WSS,SVC state
  class LEGEND legend
  class L1,L2,L3,L4 legend
```

## WebSocket Protocol

All communication uses JSON messages with a `type` field.

### Message Types

| Type | Direction | Purpose |
|------|-----------|---------|
| `subscribe` | Webview → Hub | Register interest in store keys (e.g. `core_status`, `project_state`) |
| `action` | Webview → Hub → Core | Trigger an operation (e.g. `start_build`, `select_project`) |
| `state` | Core → Hub → Webview | Push updated state slices to subscribers |

### Endpoints

- `/atopile-ui` — Hub WS server, accepts webview connections
- `/atopile-core` — Core server WS endpoint, hub connects as a client

## Startup Sequence

1. Extension assigns free ports for hub and core server
2. Hub (Node) starts, opens WS server on `/atopile-ui`
3. Extension registers sidebar + panel webviews (immediately available)
4. Core server (Python, `ato serve core`) starts, opens WS on `/atopile-core`
5. Hub connects to core server, sends `discover_projects` action
6. Webviews connect to hub, subscribe to store keys, receive state updates
