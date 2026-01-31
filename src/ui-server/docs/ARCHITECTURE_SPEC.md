# UI Architecture Specification

A general-purpose architecture for building event-driven UI applications with clear separation of concerns, testability, and portability.

---

## Overview

This architecture separates concerns into four layers:

| Layer | Purpose | Runtime |
|-------|---------|---------|
| **Model** | Domain logic, data, computation | Python |
| **Backend Server** | API surface, persistence, event routing | Python (FastAPI) |
| **Frontend Server** | UI state, data transformation, action handling | TypeScript (Bun/Browser/Node) |
| **Frontend View** | Pure rendering | React |

---

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                         FRONTEND VIEW                                    │
│                                                                          │
│   Runtime:    React (Browser, Webview, Electron)                         │
│   State:      None - pure function of props                              │
│   Input:      ViewState from Frontend Server                             │
│   Output:     ViewAction events to Frontend Server                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ WebSocket
                                  │ (ViewState ↓, ViewAction ↑)
                                  │
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                         FRONTEND SERVER                                  │
│                                                                          │
│   Runtime:    TypeScript (Bun, Browser, VS Code Extension Host)          │
│   State:      UI state (selection, filters, expanded panels)             │
│   Input:      Events from Backend Server, Actions from View              │
│   Output:     ViewState to View, Requests to Backend Server              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ WebSocket + HTTP
                                  │ (Events ↓, Requests ↑)
                                  │
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                         BACKEND SERVER                                   │
│                                                                          │
│   Runtime:    Python (FastAPI)                                           │
│   State:      Stateless - delegates to Model                             │
│   Input:      HTTP requests, Model events                                │
│   Output:     HTTP responses, WebSocket events                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ In-process Python API
                                  │
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                              MODEL                                       │
│                                                                          │
│   Runtime:    Python                                                     │
│   State:      Domain data (graphs, caches, SQLite if needed)             │
│   Input:      Function calls from Backend Server                         │
│   Output:     Return values, Event callbacks                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Layer Specifications

### MODEL

**Purpose:** Domain logic and data. The "brain" of the application.

**Properties:**
- Contains all business logic
- Owns all domain data
- Emits events for state changes
- No knowledge of HTTP, WebSocket, or UI
- Can use SQLite for persistence if needed

**Responsibilities:**
| DO | DON'T |
|----|-------|
| Domain computation | Handle HTTP requests |
| Data persistence (if needed) | Know about UI state |
| Emit domain events | Format data for display |
| Validate domain rules | Manage connections |

**Communication:**
- **Input:** Synchronous function calls from Backend Server
- **Output:** Return values + event callbacks

**Testing:** Unit tests. Mock external dependencies (filesystem, network).

---

### BACKEND SERVER

**Purpose:** API surface. Bridges Frontend Server and Model.

**Properties:**
- Stateless (can run multiple instances)
- Thin translation layer
- Routes requests to Model
- Broadcasts Model events to connected clients

**Responsibilities:**
| DO | DON'T |
|----|-------|
| Expose REST endpoints | Hold application state |
| Expose WebSocket for events | Contain business logic |
| Translate HTTP ↔ Model calls | Transform data for UI |
| Manage client connections | Make domain decisions |
| Handle authentication | Cache data (Model does this) |

**Communication:**
- **Input (from Frontend Server):** HTTP requests
- **Output (to Frontend Server):** HTTP responses, WebSocket events
- **Input (from Model):** Event callbacks
- **Output (to Model):** Function calls

**Testing:** Integration tests. Mock Model layer, verify request/response contracts.

---

### FRONTEND SERVER

**Purpose:** UI state management. Data transformation for view.

**Properties:**
- Owns all UI state
- Transforms domain data → view data
- Handles user actions
- Can run in multiple environments (Bun, Browser, VS Code)

**Responsibilities:**
| DO | DON'T |
|----|-------|
| Manage UI state | Contain domain logic |
| Transform data for view | Persist data |
| Handle user actions | Make domain decisions |
| Compute derived view state | Access Model directly |
| Cache backend data locally | Render UI |

**Communication:**
- **Input (from View):** ViewAction events via WebSocket
- **Output (to View):** ViewState via WebSocket
- **Input (from Backend):** Domain events via WebSocket
- **Output (to Backend):** HTTP requests

**State Ownership:**
```
Frontend Server OWNS:
  - Selection state (what's selected)
  - Filter state (active filters)
  - UI state (expanded panels, scroll position)
  - View preferences (sort order, display mode)

Frontend Server CACHES:
  - Domain data from Backend (for transformation)
```

**Testing:** Unit tests. Mock Backend WebSocket, verify state transitions.

---

### FRONTEND VIEW

**Purpose:** Pure rendering. Stateless.

**Properties:**
- Pure function of ViewState
- No state management
- No data fetching
- No business logic
- Emits actions, does not handle them

**Responsibilities:**
| DO | DON'T |
|----|-------|
| Render UI from ViewState | Hold state |
| Emit ViewAction on user input | Fetch data |
| Handle local UI interactions | Transform data |
| Animate/transition | Make decisions |

**Communication:**
- **Input:** ViewState (complete UI state as props)
- **Output:** ViewAction (user intentions)

**Testing:** Visual/snapshot tests only. All logic tested at Frontend Server layer.

---

## Communication Protocols

### View ↔ Frontend Server (WebSocket)

```typescript
// Frontend Server → View
interface ViewState {
    // Complete state needed to render UI
    // View is pure function: render(ViewState) → UI
    [key: string]: any;
}

// View → Frontend Server  
interface ViewAction {
    type: string;
    payload?: any;
}
```

**Properties:**
- Single WebSocket connection
- Server pushes complete ViewState on every change
- View emits actions, never requests data
- Connection loss = reconnect and receive full state

---

### Frontend Server ↔ Backend Server

**WebSocket (Events):**
```typescript
// Backend → Frontend Server
interface BackendEvent {
    type: string;      // Domain event type
    data: any;         // Event payload
}
```

**HTTP (Requests):**
```typescript
// Frontend Server → Backend
// Standard REST: GET/POST/PUT/DELETE
// Returns domain data (not view-formatted)
```

**Properties:**
- WebSocket for real-time events (Backend → Frontend Server)
- HTTP for requests (Frontend Server → Backend)
- No polling - all updates via events
- Frontend Server subscribes to relevant event types

---

### Backend Server ↔ Model

**In-process Python:**
```python
# Backend calls Model
result = model.do_something(params)

# Model emits events via callback
def on_model_event(event: Event):
    broadcast_to_clients(event)

model.subscribe(on_model_event)
```

**Properties:**
- Synchronous function calls
- Event callbacks for async notifications
- No serialization overhead (same process)

---

## Event Flow Patterns

### Pattern 1: User Action → Domain Change

```
View                Frontend Server       Backend Server        Model
  │                       │                     │                 │
  │ ViewAction            │                     │                 │
  │──────────────────────>│                     │                 │
  │                       │                     │                 │
  │                       │ HTTP POST           │                 │
  │                       │────────────────────>│                 │
  │                       │                     │                 │
  │                       │                     │ function call   │
  │                       │                     │────────────────>│
  │                       │                     │                 │
  │                       │                     │    Event        │
  │                       │                     │<────────────────│
  │                       │                     │                 │
  │                       │ WebSocket Event     │                 │
  │                       │<────────────────────│                 │
  │                       │                     │                 │
  │ ViewState             │                     │                 │
  │<──────────────────────│                     │                 │
```

### Pattern 2: UI-Only State Change

```
View                Frontend Server
  │                       │
  │ ViewAction            │
  │ (e.g., toggle panel)  │
  │──────────────────────>│
  │                       │
  │                       │ (update local state)
  │                       │
  │ ViewState             │
  │<──────────────────────│

No Backend involved - Frontend Server owns this state.
```

### Pattern 3: Background Event

```
                    Frontend Server       Backend Server        Model
                          │                     │                 │
                          │                     │    Event        │
                          │                     │<────────────────│
                          │                     │                 │
                          │ WebSocket Event     │                 │
                          │<────────────────────│                 │
                          │                     │                 │
                          │ (update cached data,│                 │
                          │  recompute ViewState)                 │
                          │                     │                 │
  View                    │                     │                 │
  │ ViewState             │                     │                 │
  │<──────────────────────│                     │                 │
```

---

## Testing Strategy

### Principle: Test Without UI

All application logic is testable without rendering UI:

| Layer | Test Type | What to Mock |
|-------|-----------|--------------|
| Model | Unit | External services, filesystem |
| Backend Server | Integration | Model layer |
| Frontend Server | Unit | Backend WebSocket/HTTP |
| Frontend View | Visual only | Nothing (uses real ViewState) |

### Frontend Server Testing (Most Important)

```typescript
// Test state transitions
test("action updates state correctly", () => {
    const server = new FrontendServer(mockBackend);
    
    server.dispatch({ type: "SELECT_ITEM", id: "123" });
    
    expect(server.getViewState().selectedId).toBe("123");
});

// Test event handling
test("backend event updates view state", () => {
    const server = new FrontendServer(mockBackend);
    
    mockBackend.emit("item:updated", { id: "123", name: "New Name" });
    
    expect(server.getViewState().items[0].name).toBe("New Name");
});

// Test data transformation
test("transforms domain data to view format", () => {
    const server = new FrontendServer(mockBackend);
    server.setDomainData({ items: [...] });
    
    const viewState = server.getViewState();
    
    expect(viewState.displayItems).toMatchExpectedFormat();
});
```

---

## Properties Summary

| Property | Model | Backend | Frontend Server | View |
|----------|-------|---------|-----------------|------|
| State | Domain data | None | UI state | None |
| Logic | Domain | Routing | UI/Transform | None |
| Testable | Unit | Integration | Unit | Visual |
| Scalable | No (stateful) | Yes (stateless) | Per-client | N/A |
| Runtime | Python | Python | TS (any) | React |

---

## Principles

1. **Event-driven, no polling**
   - All updates flow via events
   - No `setInterval`, no periodic fetching
   - Producers push, consumers react

2. **Stateless Backend Server**
   - Can scale horizontally
   - All state in Model or Frontend Server
   - Request → Model → Response

3. **Testable without UI**
   - Frontend Server is fully unit testable
   - View is just snapshot tests
   - All logic tested before rendering

4. **Clear state ownership**
   - Model: Domain data
   - Backend: Nothing (passes through)
   - Frontend Server: UI state + cached data
   - View: Nothing (props only)

5. **Portable Frontend**
   - Same Frontend Server code in Bun/Browser/VS Code
   - Same View code everywhere React runs
   - Only entry point differs
