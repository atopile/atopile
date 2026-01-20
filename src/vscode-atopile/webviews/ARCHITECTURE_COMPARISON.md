# Architecture Comparison: Orchestrator vs VS Code Extension

This document analyzes the orchestrator architecture from `tools/orchestrator/` and compares it to the current VS Code extension implementation in `src/vscode-atopile/`. It provides a plan for re-architecting the extension to follow the orchestrator's clean separation of concerns.

## Table of Contents
1. [Orchestrator Architecture Summary](#1-orchestrator-architecture-summary)
2. [Current Extension Architecture Summary](#2-current-extension-architecture-summary)
3. [Key Architectural Differences](#3-key-architectural-differences)
4. [10 Orchestrator Data Flow Examples](#4-10-orchestrator-data-flow-examples)
5. [10 Extension Examples (Current vs Proposed)](#5-10-extension-examples-current-vs-proposed)
6. [Re-Architecture Plan](#6-re-architecture-plan)
7. [High-Level Proposed Architecture](#7-high-level-proposed-architecture)
8. [Complete Feature Flows: Current vs Proposed](#8-complete-feature-flows-current-vs-proposed)
9. [Proposed Project Structure](#9-proposed-project-structure)

---

## 1. Orchestrator Architecture Summary

The orchestrator follows a **clean layered architecture** with strict separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    Components                            ││
│  │  AgentList.tsx, PipelineEditor.tsx, OutputViewer.tsx   ││
│  │  - Pure presentation, no business logic                 ││
│  │  - Dispatch events via useDispatch()                    ││
│  │  - Subscribe to state via useUIState()                  ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    Hooks Layer                           ││
│  │  useLogic.tsx - React bindings                          ││
│  │  - LogicProvider context                                 ││
│  │  - useUIState(), useDispatch(), useAgents(), etc.       ││
│  │  - Transform state → ViewModels for efficient rendering ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   Logic Layer (Pure TS)                  ││
│  │  logic/index.ts - UILogic class                         ││
│  │  logic/events.ts - Typed events (UIEvent union)         ││
│  │  logic/state.ts - State shape & helpers                 ││
│  │  logic/viewmodels.ts - ViewModels for UI                ││
│  │  logic/handlers/*.ts - Event handlers                   ││
│  │  - NO React dependencies - testable in Node.js/Bun     ││
│  │  - Single dispatch() entry point                        ││
│  │  - setState() + notifyListeners() pattern               ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    API Layer                             ││
│  │  logic/api/client.ts - REST API client                  ││
│  │  logic/api/websocket.ts - WebSocket client              ││
│  │  logic/api/types.ts - API response types                ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                      BACKEND (Python)                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    Server Layer                          ││
│  │  server/app.py - FastAPI app setup                      ││
│  │  server/routes/*.py - API endpoints                     ││
│  │  server/dependencies.py - Dependency injection          ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    Core Layer                            ││
│  │  core/agent_manager.py - Business logic                 ││
│  │  core/pipeline_executor.py - Pipeline execution         ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    Models Layer                          ││
│  │  models/agents.py - AgentState, AgentConfig             ││
│  │  models/events.py - GlobalEvent types                   ││
│  │  models/sessions.py - Session state                     ││
│  │  models/pipelines.py - Pipeline definitions             ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Typed Events**: All UI actions are typed events (`UIEvent` discriminated union)
2. **Single Dispatch**: Components call `dispatch({ type: 'agents.spawn', payload: {...} })`
3. **Logic Class**: `UILogic` is a pure TypeScript class - no React
4. **State + Listeners**: `setState()` always calls `notifyListeners()`
5. **ViewModels**: Transform API types to UI-optimized shapes
6. **Testable**: Logic layer runs in Node.js/Bun without React

---

## 2. Current Extension Architecture Summary

The current extension has a **hybrid architecture** mixing multiple patterns:

```
┌─────────────────────────────────────────────────────────────┐
│                    WEBVIEW (React)                           │
│  ┌─────────────────────────────────────────────────────────┐│
│  │            Sidebar.tsx (1100+ lines)                    ││
│  │  - Local React state (useState)                          ││
│  │  - Message handler in useEffect                          ││
│  │  - Action functions defined inline                       ││
│  │  - Direct transformation logic                           ││
│  │  - Business logic mixed with presentation                ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │            Child Components                              ││
│  │  ProblemsPanel, ProjectsPanel, BuildQueuePanel, etc.    ││
│  │  - Receive props from Sidebar                            ││
│  │  - Mostly presentation, some filtering logic             ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │            Types                                         ││
│  │  types/build.ts - AppState, Build, Problem, etc.        ││
│  │  - Good type definitions                                 ││
│  │  - Matches backend Python models                         ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ postMessage/onMessage
┌─────────────────────────────────────────────────────────────┐
│                    EXTENSION (TypeScript)                    │
│  ┌─────────────────────────────────────────────────────────┐│
│  │            vscode-panels.ts                              ││
│  │  - WebviewProvider implementation                        ││
│  │  - Action routing (switch statement)                     ││
│  │  - State sync to webview                                 ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │            appState.ts                                   ││
│  │  - AppStateManager singleton                             ││
│  │  - State ownership                                       ││
│  │  - Change notifications                                  ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                    DASHBOARD SERVER (Python)                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │            server.py - FastAPI                           ││
│  │            state.py - ServerState, AppState              ││
│  │  - Owns canonical state                                  ││
│  │  - WebSocket broadcasts on change                        ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Current Issues

1. **Monolithic Component**: `Sidebar.tsx` is 1100+ lines with mixed concerns
2. **No Event System**: Actions are inline functions calling `vscode.postMessage()`
3. **No Logic Layer**: Business logic scattered between webview and extension
4. **Untestable**: Logic is coupled to React and VS Code APIs
5. **No ViewModels**: Raw state transformations inline in components
6. **Duplicate State**: Both extension and webview maintain state copies

---

## 3. Key Architectural Differences

| Aspect | Orchestrator | Current Extension |
|--------|--------------|-------------------|
| **Event System** | Typed `UIEvent` union, `dispatch()` | Inline `vscode.postMessage()` |
| **Logic Location** | Pure TS `UILogic` class | Mixed in React components |
| **State Updates** | `setState()` + `notifyListeners()` | `useState` + message handler |
| **ViewModels** | Separate `viewmodels.ts` | Inline transformations |
| **Testability** | Logic runs in Node/Bun | Requires React/VS Code |
| **API Client** | Typed `APIClient` class | Inline fetch/axios calls |
| **WebSocket** | `WebSocketClient` + handlers | Direct message handling |
| **Handlers** | Separate files per domain | Switch statement |
| **State Shape** | `UIState` with Maps | `AppState` with arrays |

---

## 4. 10 Orchestrator Data Flow Examples

### Example 1: Spawn Agent

```
┌─────────┐     ┌───────────┐     ┌─────────┐     ┌────────┐     ┌────────┐
│  UI     │ ──▶ │  dispatch │ ──▶ │ handler │ ──▶ │  API   │ ──▶ │ Server │
│ Button  │     │ agents.   │     │ agents. │     │ client │     │ POST   │
│ onClick │     │ spawn     │     │ ts:46   │     │ spawn  │     │ /spawn │
└─────────┘     └───────────┘     └─────────┘     └────────┘     └────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │    setState     │
                              │ agents.set(id)  │
                              │ selectedAgent   │
                              │ loading: false  │
                              └─────────────────┘
```

**Code flow:**
1. `AgentList.tsx` button → `dispatch({ type: 'agents.spawn', payload })`
2. `UILogic.dispatch()` → `handleEvent()` → `handleAgentEvent()`
3. `handlers/agents.ts:handleSpawn()` → `logic.api.agents.spawn()`
4. On success: `logic.setState()` updates agents Map
5. `notifyListeners()` → React re-renders via `useUIState()`

### Example 2: Select Agent

```
dispatch({ type: 'agents.select', payload: { agentId: '123' } })
         │
         ▼
handleSelect(logic, event) {
  logic.setState(s => ({ ...s, selectedAgentId: event.payload.agentId }))
}
```

**Synchronous, no API call** - pure state update.

### Example 3: Delete Agent

```
dispatch({ type: 'agents.delete', payload: { agentId } })
         │
         ▼
1. setState(setLoading(s, `delete-${agentId}`, true))
2. await logic.api.agents.delete(agentId)
3. setState({
     agents: deleteFromMap(s.agents, agentId),
     agentOutputs: new Map without agentId,
     selectedAgentId: clear if was selected
   })
```

### Example 4: Connect to Agent Output (WebSocket)

```
dispatch({ type: 'output.connect', payload: { agentId } })
         │
         ▼
1. logic.ws.connect(agentId, (chunk) => {
     setState(s => appendOutputChunk(s, agentId, chunk))
   })
2. setState(s => setAgentConnected(s, agentId, true))
```

**Real-time streaming via WebSocket callback.**

### Example 5: Global Events (Server Push)

```
WebSocket /ws/events
         │
         ▼
handleGlobalEvent(event) {
  switch(event.type) {
    case 'agent_status_changed':
      setState(s => updateMap(s.agents, event.agent_id, event.data.agent))
    case 'session_node_status_changed':
      setState(s => updatePipelineSessions(...))
  }
}
```

**Server pushes state changes, UILogic updates state.**

### Example 6: Create Pipeline

```
dispatch({ type: 'pipelines.create', payload: { name, nodes, edges, config } })
         │
         ▼
1. setLoading('create', true)
2. response = await api.pipelines.create(payload)
3. setState(s => ({
     pipelines: updateMap(s.pipelines, response.pipeline.id, response.pipeline),
     selectedPipelineId: response.pipeline.id
   }))
```

### Example 7: Resume Agent

```
dispatch({ type: 'agents.resume', payload: { agentId, prompt } })
         │
         ▼
1. setLoading(`resume-${agentId}`, true)
2. await api.agents.resume(agentId, prompt)
3. response = await api.agents.get(agentId)  // Get updated state
4. setState: update agent, add prompt to outputs, set currentRunNumber
```

### Example 8: Rename Agent

```
dispatch({ type: 'agents.rename', payload: { agentId, name } })
         │
         ▼
1. response = await api.agents.rename(agentId, name)
2. setState(s => ({ agents: updateMap(s.agents, agentId, response.agent) }))
```

**No loading state** - fast operation with optimistic feel.

### Example 9: Navigate Between Pages

```
dispatch({ type: 'ui.navigate', payload: { page: 'pipelines' } })
         │
         ▼
handleUIEvent(logic, event) {
  logic.setState(s => ({ ...s, currentPage: event.payload.page }))
}
```

**Pure state update** - no API involved.

### Example 10: Toggle Verbose Mode

```
dispatch({ type: 'ui.toggleVerbose', payload: { value: true } })
         │
         ▼
logic.setState(s => ({ ...s, verbose: event.payload.value }))
```

---

## 5. 10 Extension Examples (Current vs Proposed)

### Example 1: Build Project

**Current Implementation:**
```tsx
// Sidebar.tsx - inline function
const handleBuild = (level: 'project' | 'build' | 'symbol', id: string, label: string) => {
  vscode.postMessage({ type: 'action', action: 'build', level, id, label });
};

// vscode-panels.ts - switch routing
case 'build':
  if (level === 'project') { ... }
  else if (level === 'build') { ... }
  // 50+ lines of build logic
```

**Proposed (Orchestrator Pattern):**
```tsx
// components/ProjectsPanel.tsx
const dispatch = useDispatch();
dispatch({ type: 'builds.start', payload: { level, id, label } });

// logic/handlers/builds.ts
async function handleStartBuild(logic: UILogic, event: BuildStartEvent) {
  logic.setState(s => setLoading(s, `build-${event.payload.id}`, true));
  await logic.api.builds.start(event.payload);
  // Server will push build status via WebSocket
}
```

### Example 2: Problem Click (Navigate to File)

**Current:**
```tsx
// ProblemsPanel.tsx - receives callback prop
<div onClick={() => onProblemClick?.(problem)}>

// Sidebar.tsx - defines handler, calls action
const handleProblemClick = (problem) => {
  action('openFile', { file: problem.file, line: problem.line });
};
```

**Proposed:**
```tsx
// components/ProblemsPanel.tsx
const dispatch = useDispatch();
<div onClick={() => dispatch({
  type: 'navigation.openFile',
  payload: { file: problem.file, line: problem.line }
})}>

// logic/handlers/navigation.ts
function handleOpenFile(logic: UILogic, event) {
  // VS Code extension handles via message bridge
  logic.sendToExtension({ type: 'openFile', ...event.payload });
}
```

### Example 3: Cancel Build

**Current:**
```tsx
// Sidebar.tsx
const handleCancelBuild = (buildId: string) => {
  action('cancelBuild', { buildId });
};
// Passed down through 3 levels of props
```

**Proposed:**
```tsx
// components/BuildQueuePanel.tsx
const dispatch = useDispatch();
dispatch({ type: 'builds.cancel', payload: { buildId } });

// logic/handlers/builds.ts
async function handleCancelBuild(logic: UILogic, event) {
  await logic.api.builds.cancel(event.payload.buildId);
  // Server pushes updated build status
}
```

### Example 4: Install Package

**Current:**
```tsx
// Sidebar.tsx - 10 lines
const handlePackageInstall = (packageId: string, projectRoot: string) => {
  action('installPackage', { packageId, projectRoot });
};
```

**Proposed:**
```tsx
dispatch({ type: 'packages.install', payload: { packageId, projectRoot } });

// logic/handlers/packages.ts
async function handleInstallPackage(logic: UILogic, event) {
  const { packageId, projectRoot } = event.payload;
  logic.setState(s => setLoading(s, `install-${packageId}`, true));

  try {
    await logic.api.packages.install(packageId, projectRoot);
    // Refresh packages list
    await handleRefreshPackages(logic);
  } catch (e) {
    logic.setState(s => addError(s, e.message, 'packages.install'));
  } finally {
    logic.setState(s => setLoading(s, `install-${packageId}`, false));
  }
}
```

### Example 5: Toggle Section Collapse

**Current:**
```tsx
// Sidebar.tsx - local state
const [collapsedSections, setCollapsedSections] = useState<Set<string>>(...);
const toggleSection = (sectionId: string) => { ... };
```

**Proposed:**
```tsx
dispatch({ type: 'ui.toggleSection', payload: { sectionId } });

// logic/handlers/ui.ts - persisted in state
function handleToggleSection(logic: UILogic, event) {
  logic.setState(s => ({
    ...s,
    collapsedSections: s.collapsedSections.has(event.payload.sectionId)
      ? new Set([...s.collapsedSections].filter(id => id !== event.payload.sectionId))
      : new Set([...s.collapsedSections, event.payload.sectionId])
  }));
}
```

### Example 6: Filter Problems by Level

**Current:**
```tsx
// ProblemsPanel.tsx - receives filter as prop
// Sidebar.tsx - manages filter state
const [filter, setFilter] = useState({ levels: [...] });
```

**Proposed:**
```tsx
dispatch({ type: 'problems.toggleLevel', payload: { level: 'warning' } });

// logic/handlers/problems.ts
function handleToggleLevel(logic: UILogic, event) {
  logic.setState(s => {
    const levels = new Set(s.problemFilter.levels);
    if (levels.has(event.payload.level)) {
      levels.delete(event.payload.level);
    } else {
      levels.add(event.payload.level);
    }
    return { ...s, problemFilter: { ...s.problemFilter, levels: [...levels] } };
  });
}
```

### Example 7: Select Atopile Version

**Current:**
```tsx
// Sidebar.tsx
onChange={(e) => action('setAtopileVersion', { version: e.target.value })}

// vscode-panels.ts
case 'setAtopileVersion':
  await setAtopileVersionSetting(data.version);
```

**Proposed:**
```tsx
dispatch({ type: 'atopile.setVersion', payload: { version } });

// logic/handlers/atopile.ts
async function handleSetVersion(logic: UILogic, event) {
  logic.setState(s => ({
    ...s,
    atopile: { ...s.atopile, isInstalling: true, installProgress: { message: 'Installing...' } }
  }));

  try {
    await logic.sendToExtension({ type: 'setAtopileVersion', version: event.payload.version });
    // Extension handles VS Code settings, sends confirmation
  } catch (e) {
    logic.setState(s => ({
      ...s,
      atopile: { ...s.atopile, error: e.message }
    }));
  }
}
```

### Example 8: Expand Project (Lazy Load Modules)

**Current:**
```tsx
// Sidebar.tsx
const handleProjectExpand = (projectRoot: string) => {
  if (!state?.projectModules?.[projectRoot]) {
    action('fetchModules', { projectRoot });
  }
  if (!state?.projectFiles?.[projectRoot]) {
    action('fetchFiles', { projectRoot });
  }
};
```

**Proposed:**
```tsx
dispatch({ type: 'projects.expand', payload: { projectRoot } });

// logic/handlers/projects.ts
async function handleExpandProject(logic: UILogic, event) {
  const { projectRoot } = event.payload;
  const state = logic.getState();

  // Lazy load in parallel
  const promises = [];
  if (!state.projectModules.has(projectRoot)) {
    promises.push(
      logic.api.projects.getModules(projectRoot).then(modules =>
        logic.setState(s => ({
          ...s,
          projectModules: new Map(s.projectModules).set(projectRoot, modules)
        }))
      )
    );
  }
  // ... similar for files
  await Promise.all(promises);
}
```

### Example 9: Search/Filter Build Queue

**Current:** No search, filtering done via props drilling.

**Proposed:**
```tsx
dispatch({ type: 'buildQueue.setFilter', payload: { query: 'my-project' } });

// Selector hook computes filtered view
export function useFilteredBuildQueue(): QueuedBuildViewModel[] {
  const state = useUIState();
  return useMemo(() => {
    const query = state.buildQueueFilter.toLowerCase();
    return Array.from(state.queuedBuilds.values())
      .filter(b => b.name.toLowerCase().includes(query))
      .map(buildToQueueViewModel);
  }, [state.queuedBuilds, state.buildQueueFilter]);
}
```

### Example 10: Receive WebSocket State Update

**Current:**
```tsx
// Sidebar.tsx useEffect
const handleMessage = (event: MessageEvent) => {
  if (msg.type === 'state') {
    setState(safeState);  // Full replacement
  } else if (msg.type === 'update') {
    setState(prev => ({ ...prev, ...msg.data }));  // Merge
  }
};
```

**Proposed:**
```tsx
// logic/index.ts - handleGlobalEvent
private handleGlobalEvent(event: GlobalEvent): void {
  switch (event.type) {
    case 'build_status_changed':
      this.setState(s => ({
        ...s,
        builds: updateMap(s.builds, event.build_id, event.data.build)
      }));
      break;
    case 'problems_updated':
      this.setState(s => ({
        ...s,
        problems: event.data.problems
      }));
      break;
    // ... typed handlers for each event
  }
}
```

---

## 6. Re-Architecture Plan

### Phase 1: Create Logic Layer Foundation

**Files to create:**
```
webviews/src/logic/
├── index.ts          # UILogic class
├── state.ts          # UIState type, initialState, helpers
├── events.ts         # UIEvent union type
├── viewmodels.ts     # ViewModel interfaces
├── handlers/
│   ├── index.ts      # Event routing
│   ├── builds.ts     # Build-related handlers
│   ├── projects.ts   # Project handlers
│   ├── packages.ts   # Package handlers
│   ├── problems.ts   # Problem handlers
│   ├── ui.ts         # UI state handlers
│   └── atopile.ts    # Atopile version handlers
└── api/
    ├── types.ts      # API response types
    ├── client.ts     # REST client (wraps vscode.postMessage)
    └── bridge.ts     # VS Code extension bridge
```

### Phase 2: Define Events

```typescript
// logic/events.ts
export type UIEvent =
  // Build events
  | { type: 'builds.start'; payload: { level: string; id: string; label: string } }
  | { type: 'builds.cancel'; payload: { buildId: string } }
  | { type: 'builds.refresh'; payload?: undefined }
  // Project events
  | { type: 'projects.select'; payload: { projectId: string | null } }
  | { type: 'projects.expand'; payload: { projectRoot: string } }
  // Package events
  | { type: 'packages.install'; payload: { packageId: string; projectRoot: string } }
  | { type: 'packages.refresh'; payload?: undefined }
  // Problem events
  | { type: 'problems.toggleLevel'; payload: { level: 'error' | 'warning' } }
  | { type: 'problems.setFilter'; payload: { buildId?: string; stageId?: string } }
  // Navigation events
  | { type: 'navigation.openFile'; payload: { file: string; line?: number } }
  // UI events
  | { type: 'ui.toggleSection'; payload: { sectionId: string } }
  | { type: 'ui.setSelection'; payload: Selection }
  // Atopile events
  | { type: 'atopile.setVersion'; payload: { version: string } }
  | { type: 'atopile.setSource'; payload: { source: 'release' | 'branch' | 'local' } };
```

### Phase 3: Create UILogic Class

```typescript
// logic/index.ts
export class UILogic {
  private state: UIState;
  private listeners = new Set<StateListener>();
  private extensionBridge: ExtensionBridge;

  constructor(bridge: ExtensionBridge) {
    this.state = createInitialState();
    this.extensionBridge = bridge;
  }

  async dispatch(event: UIEvent): Promise<void> {
    await handleEvent(this, event);
  }

  subscribe(listener: StateListener): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => this.listeners.delete(listener);
  }

  setState(updater: (s: UIState) => UIState): void {
    this.state = { ...updater(this.state), _version: this.state._version + 1 };
    this.notifyListeners();
  }

  // Bridge to VS Code extension
  sendToExtension(message: ExtensionMessage): Promise<void> {
    return this.extensionBridge.send(message);
  }

  // Handle incoming from extension/server
  handleExtensionMessage(message: IncomingMessage): void {
    // Update state based on message type
  }
}
```

### Phase 4: Create React Hooks

```typescript
// hooks/useLogic.tsx
const LogicContext = createContext<UILogic | null>(null);

export function LogicProvider({ children, logic }: { children: ReactNode; logic: UILogic }) {
  return <LogicContext.Provider value={logic}>{children}</LogicContext.Provider>;
}

export function useDispatch(): (event: UIEvent) => Promise<void> {
  const logic = useContext(LogicContext)!;
  return useCallback((event) => logic.dispatch(event), [logic]);
}

export function useUIState(): UIState {
  const logic = useContext(LogicContext)!;
  const [, forceUpdate] = useReducer(x => x + 1, 0);
  const stateRef = useRef(logic.getState());

  useEffect(() => {
    return logic.subscribe(state => {
      stateRef.current = state;
      forceUpdate();
    });
  }, [logic]);

  return stateRef.current;
}

// Domain-specific selectors
export function useProjects(): ProjectViewModel[] { ... }
export function useProblems(): ProblemViewModel[] { ... }
export function useQueuedBuilds(): QueuedBuildViewModel[] { ... }
```

### Phase 5: Refactor Components

**Before (Sidebar.tsx 1100+ lines):**
- All state management
- All handlers
- All transformations
- All child rendering

**After (distributed):**
```
components/
├── Sidebar.tsx        # ~100 lines - layout shell
├── SidebarHeader.tsx  # Header with settings
├── ProjectsSection.tsx
├── BuildQueueSection.tsx
├── ProblemsSection.tsx
├── PackagesSection.tsx
└── shared/
    ├── CollapsibleSection.tsx
    └── LoadingSpinner.tsx
```

Each component:
```tsx
function ProjectsSection() {
  const dispatch = useDispatch();
  const projects = useProjects();  // ViewModel selector
  const loading = useLoading('projects');

  return (
    <CollapsibleSection title="Projects">
      <ProjectList
        projects={projects}
        onSelect={(id) => dispatch({ type: 'projects.select', payload: { projectId: id } })}
        onBuild={(id) => dispatch({ type: 'builds.start', payload: { level: 'project', id, label: '' } })}
      />
    </CollapsibleSection>
  );
}
```

### Phase 6: Migration Steps

1. **Create logic layer** without changing existing code
2. **Add `useDispatch()` alongside existing `action()`**
3. **Migrate one handler at a time** (e.g., start with `builds.cancel`)
4. **Replace inline state transforms** with ViewModels
5. **Split Sidebar.tsx** into smaller components
6. **Remove old code** once all handlers migrated

### Phase 7: Testing

```typescript
// logic/__tests__/builds.test.ts
import { UILogic } from '../index';
import { MockExtensionBridge } from './__mocks__/bridge';

test('cancel build sets loading and calls API', async () => {
  const bridge = new MockExtensionBridge();
  const logic = new UILogic(bridge);

  // Setup initial state
  logic.setState(s => ({
    ...s,
    builds: new Map([['build-1', { id: 'build-1', status: 'building' }]])
  }));

  // Dispatch event
  await logic.dispatch({ type: 'builds.cancel', payload: { buildId: 'build-1' } });

  // Verify
  expect(bridge.messages).toContainEqual({ type: 'cancelBuild', buildId: 'build-1' });
});
```

---

## 7. High-Level Proposed Architecture

This section provides a clear, high-level overview of the proposed layered architecture with emphasis on keeping the webview as a pure presentation layer.

### 7.1 Core Principle: Webview is Just a URL

**The webview should contain NO business logic.** It is purely a presentation layer that:
- Receives state via WebSocket (from Python backend)
- Renders that state as UI
- Sends user actions back via WebSocket (to Python backend)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              WEBVIEW PRINCIPLE                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   Development:  Vite dev server (http://localhost:5173)                         │
│   Production:   Compiled JS bundle loaded via webview.html                      │
│                                                                                  │
│   The webview is a DUMB TERMINAL:                                               │
│     • Receives state from Python backend → Renders UI                           │
│     • User clicks → Sends action to Python backend                              │
│     • Single WebSocket connection to backend                                    │
│     • NO business logic, NO REST API calls                                      │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Architecture Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              WEBVIEW (React App)                                 │
│                     Loaded as URL: Vite dev server OR compiled bundle           │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                         PRESENTATION ONLY                                  │  │
│  │                                                                            │  │
│  │   Components: Sidebar, LogViewer, ProjectsPanel, BuildQueue, etc.         │  │
│  │   • Renders state received via WebSocket                                   │  │
│  │   • Dispatches user actions via WebSocket                                  │  │
│  │   • Selectors transform state for display (memoized)                      │  │
│  │   • NO business logic                                                      │  │
│  │                                                                            │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                     │ { type: 'action', ... }      ▲ { type: 'state', data }    │
│                     ▼ User actions                 │ Full/partial state         │
└─────────────────────│──────────────────────────────│────────────────────────────┘
                      │         WebSocket            │
                      │                              │
┌─────────────────────│──────────────────────────────│────────────────────────────┐
│                     │  VS CODE EXTENSION           │                             │
│                     │  (Bootstrap + Thin View)     │                             │
│  ┌──────────────────▼──────────────────────────────│─────────────────────────┐  │
│  │                      RESPONSIBILITIES                                      │  │
│  │                                                                            │  │
│  │  1. BOOTSTRAP INSTALL                                                     │  │
│  │     • Download and install uv (if needed)                                 │  │
│  │     • Install atopile via uv                                              │  │
│  │                                                                            │  │
│  │  2. BOOTSTRAP STARTUP                                                     │  │
│  │     • Start Python backend server: `ato serve`                            │  │
│  │     • Wait for server ready signal                                        │  │
│  │                                                                            │  │
│  │  3. THIN VIEW                                                             │  │
│  │     • Create webview panels                                               │  │
│  │     • Pass backend WebSocket URL to webview                               │  │
│  │     • Handle webview lifecycle (show/hide/dispose)                        │  │
│  │                                                                            │  │
│  │  NO business logic, NO state management, NO action handling               │  │
│  │  The extension is just a LAUNCHER + CONTAINER                             │  │
│  │                                                                            │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                              │ spawn process                                     │
└──────────────────────────────│───────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          PYTHON BACKEND (ato serve)                              │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                      STATE MANAGER (UIState)                               │  │
│  │  • Single source of truth for ALL UI state                                │  │
│  │  • Handles ALL user actions from webview                                  │  │
│  │  • Broadcasts state updates to webview via WebSocket                      │  │
│  │  • Computes derived state / ViewModels                                    │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                              │                     ▲                             │
│                              ▼                     │                             │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                      API LAYER (FastAPI)                                    │  │
│  │  • WebSocket: /ws/ui (bidirectional: state ↔ actions)                     │  │
│  │  • WebSocket: /ws/logs/{build_id} (live build logs)                       │  │
│  │  • REST endpoints for external integrations                               │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                              │                     ▲                             │
│                              ▼                     │                             │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                      CORE LAYER (Business Logic)                           │  │
│  │  • Wraps existing atopile: ConfigManager, Compiler, Solver, LSP           │  │
│  │  • Manages build execution and state                                      │  │
│  │  • Aggregates data from multiple sources                                  │  │
│  │  • Handles package operations, project discovery                          │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                              │                     ▲                             │
│                              ▼                     │                             │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                      MODELS LAYER (Pydantic)                               │  │
│  │  • Canonical data definitions (Project, Build, Package, Problem)          │  │
│  │  • UIState model (what gets sent to webview)                              │  │
│  │  • Action models (what comes from webview)                                │  │
│  │  • TypeScript types generated from Pydantic for webview                   │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Layer Responsibilities

| Layer | Location | Responsibility | What It Does NOT Do |
|-------|----------|----------------|---------------------|
| **Webview** | `webviews/` | Render UI, send actions via WS | NO business logic, NO state management |
| **Extension** | `src/` | Bootstrap (install uv/ato), start backend, create webview | NO business logic, NO state, NO action handling |
| **Backend State** | Python `state/` | UIState management, action handling | NO HTTP concerns |
| **Backend API** | Python `server/` | WebSocket + REST endpoints | NO state logic |
| **Backend Core** | Python `core/` | Business logic, atopile integration | NO UI concerns |
| **Backend Models** | Python `models/` | Data definitions (Pydantic) | NO logic |

### 7.3.1 Extension is Minimal

The VS Code extension has **three jobs only**:

```typescript
// src/extension.ts - THE ENTIRE EXTENSION LOGIC

export async function activate(context: vscode.ExtensionContext) {
  // ═══════════════════════════════════════════════════════════════════════════
  // 1. BOOTSTRAP INSTALL
  // ═══════════════════════════════════════════════════════════════════════════
  const uvPath = await ensureUvInstalled(context);
  const atoPath = await ensureAtopileInstalled(uvPath, context);

  // ═══════════════════════════════════════════════════════════════════════════
  // 2. BOOTSTRAP STARTUP
  // ═══════════════════════════════════════════════════════════════════════════
  const serverProcess = spawn(atoPath, ['serve', '--port', '8501']);
  const wsUrl = await waitForServerReady(serverProcess);  // e.g., ws://localhost:8501/ws/ui

  // ═══════════════════════════════════════════════════════════════════════════
  // 3. THIN VIEW
  // ═══════════════════════════════════════════════════════════════════════════
  const sidebarProvider = new SidebarViewProvider(wsUrl);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider('atopile.sidebar', sidebarProvider)
  );

  // That's it. No logic, no state, no action handling.
}

class SidebarViewProvider implements vscode.WebviewViewProvider {
  constructor(private wsUrl: string) {}

  resolveWebviewView(webviewView: vscode.WebviewView) {
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this.getHtml(webviewView.webview);
  }

  private getHtml(webview: vscode.Webview): string {
    // Just inject the WebSocket URL - webview connects directly to backend
    return `
      <!DOCTYPE html>
      <html>
        <body>
          <div id="root"></div>
          <script>window.ATOPILE_WS_URL = "${this.wsUrl}";</script>
          <script src="${this.getBundleUri(webview)}"></script>
        </body>
      </html>
    `;
  }
}
```

### 7.3.2 Webview Connects Directly to Backend

The webview talks directly to the Python backend via WebSocket - **not through the extension**:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         DIRECT CONNECTION                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   Webview ◄─────── WebSocket ───────► Python Backend                            │
│                                                                                  │
│   The extension is NOT in the data path.                                        │
│   Extension only:                                                                │
│     1. Starts the backend process                                               │
│     2. Gives the webview the WebSocket URL                                      │
│     3. Creates the webview container                                            │
│                                                                                  │
│   After startup, the extension does NOTHING.                                    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.4 Webview Development Setup

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          WEBVIEW BUILD MODES                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  DEVELOPMENT MODE                                                                │
│  ─────────────────                                                               │
│  1. Start Vite dev server:                                                      │
│     $ cd webviews && npm run dev                                                │
│     → Serves at http://localhost:5173                                           │
│                                                                                  │
│  2. Extension loads webview URL:                                                │
│     webview.html = "http://localhost:5173"                                      │
│                                                                                  │
│  3. Benefits:                                                                   │
│     • Hot module replacement (HMR)                                              │
│     • Fast refresh on file changes                                              │
│     • React DevTools support                                                    │
│     • Source maps for debugging                                                 │
│                                                                                  │
│  PRODUCTION MODE                                                                 │
│  ────────────────                                                                │
│  1. Build webview:                                                              │
│     $ cd webviews && npm run build                                              │
│     → Outputs to webviews/dist/                                                 │
│                                                                                  │
│  2. Extension loads compiled bundle:                                            │
│     webview.html = webview.asWebviewUri(distPath)                               │
│                                                                                  │
│  3. Bundle contains:                                                            │
│     • Minified JS                                                               │
│     • CSS                                                                        │
│     • Static assets                                                             │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.5 WebSocket Protocol (Webview ↔ Backend)

The webview connects **directly to the Python backend** via WebSocket. The extension is NOT in the data path.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      COMMUNICATION ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   WEBVIEW ◄─────────── WebSocket ────────────► PYTHON BACKEND                   │
│                                                                                  │
│   Extension does NOT relay messages.                                             │
│   Extension only provides the WebSocket URL at startup.                         │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

```typescript
// ═══════════════════════════════════════════════════════════════════════════════
// MESSAGES: WEBVIEW → BACKEND (User Actions)
// ═══════════════════════════════════════════════════════════════════════════════

type WebviewAction =
  // Build actions
  | { type: 'action'; action: 'build'; payload: { targetIds: string[] } }
  | { type: 'action'; action: 'cancelBuild'; payload: { buildId: string } }

  // Project actions
  | { type: 'action'; action: 'selectProject'; payload: { projectRoot: string } }
  | { type: 'action'; action: 'toggleTarget'; payload: { targetId: string } }

  // Package actions
  | { type: 'action'; action: 'installPackage'; payload: { packageId: string } }
  | { type: 'action'; action: 'removePackage'; payload: { packageId: string } }

  // Navigation actions (backend proxies to VS Code via LSP or command)
  | { type: 'action'; action: 'openFile'; payload: { file: string; line?: number } }
  | { type: 'action'; action: 'revealInExplorer'; payload: { path: string } }

  // UI state actions
  | { type: 'action'; action: 'toggleSection'; payload: { sectionId: string } }
  | { type: 'action'; action: 'setLogFilter'; payload: { levels: string[] } };

// ═══════════════════════════════════════════════════════════════════════════════
// MESSAGES: BACKEND → WEBVIEW (State Updates)
// ═══════════════════════════════════════════════════════════════════════════════

type BackendMessage =
  // Full state (on initial connection or major changes)
  | { type: 'state'; data: UIState }

  // Partial state update (for efficiency)
  | { type: 'patch'; path: string[]; value: unknown }

  // Live events
  | { type: 'event'; event: 'build.log'; data: LogEntry }
  | { type: 'event'; event: 'build.progress'; data: { stage: string; progress: number } }
  | { type: 'event'; event: 'build.completed'; data: { status: BuildStatus } };

// ═══════════════════════════════════════════════════════════════════════════════
// WEBVIEW IMPLEMENTATION - Direct WebSocket Connection
// ═══════════════════════════════════════════════════════════════════════════════

// webviews/src/App.tsx
function App() {
  const [state, setState] = useState<UIState | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Get WebSocket URL injected by extension at startup
    const wsUrl = (window as any).ATOPILE_WS_URL;  // e.g., ws://localhost:8501/ws/ui

    // Connect DIRECTLY to Python backend
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'state') {
        setState(message.data);
      } else if (message.type === 'patch') {
        setState(s => applyPatch(s, message.path, message.value));
      } else if (message.type === 'event') {
        // Handle live events (logs, progress, etc.)
        handleEvent(message.event, message.data);
      }
    };

    ws.onopen = () => {
      // Request initial state
      ws.send(JSON.stringify({ type: 'ready' }));
    };

    return () => ws.close();
  }, []);

  // Dispatch action DIRECTLY to backend (NOT through extension)
  const dispatchAction = useCallback((action: string, payload: unknown) => {
    wsRef.current?.send(JSON.stringify({ type: 'action', action, payload }));
  }, []);

  if (!state) return <Loading />;

  return (
    <StateContext.Provider value={state}>
      <ActionContext.Provider value={dispatchAction}>
        <Router />
      </ActionContext.Provider>
    </StateContext.Provider>
  );
}
```

### 7.6 Backend Handles ALL Logic

**All business logic lives in the Python backend**, not in the extension or webview:

```python
# backend/state/ui_state_manager.py

class UIStateManager:
    """
    Single source of truth for ALL UI state.
    Handles ALL user actions from webview.
    Lives in Python backend, NOT in VS Code extension.
    """

    def __init__(
        self,
        config_manager: ConfigManager,      # Existing atopile
        build_runner: BuildRunner,          # Build execution
        package_service: PackageService,    # Package operations
    ):
        self.state = create_initial_state()
        self.connections: set[WebSocket] = set()

        # Use existing atopile components - don't reimplement!
        self._config = config_manager
        self._builds = build_runner
        self._packages = package_service

    # ─────────────────────────────────────────────────────────────────────────
    # Handle actions from webview (via WebSocket)
    # ─────────────────────────────────────────────────────────────────────────

    async def handle_action(self, action: str, payload: dict) -> None:
        match action:
            case 'build':
                await self._handle_build(payload['targetIds'])
            case 'cancelBuild':
                await self._handle_cancel_build(payload['buildId'])
            case 'selectProject':
                await self._handle_select_project(payload['projectRoot'])
            case 'installPackage':
                await self._handle_install_package(payload['packageId'])
            case 'openFile':
                await self._handle_open_file(payload['file'], payload.get('line'))
            # ... other actions

    # ─────────────────────────────────────────────────────────────────────────
    # Action handlers (business logic lives HERE in Python backend)
    # ─────────────────────────────────────────────────────────────────────────

    async def _handle_build(self, target_ids: list[str]) -> None:
        # Update UI state to show building
        self._update_state(loading={'build': True})

        try:
            # Start build using existing atopile build system
            build = await self._builds.start(target_ids)

            # Update state with new build
            self._update_state(
                builds={**self.state.builds, build.id: build},
                current_build_id=build.id,
                loading={'build': False}
            )

            # Stream logs via WebSocket
            async for log_entry in self._builds.stream_logs(build.id):
                await self._broadcast_event('build.log', log_entry)

        except Exception as e:
            self._update_state(
                loading={'build': False},
                errors={'build': str(e)}
            )

    async def _handle_install_package(self, package_id: str) -> None:
        project_root = self.state.selected_project_root

        self._update_state(
            package_operations={**self.state.package_operations, package_id: 'installing'}
        )

        try:
            # Use existing atopile package system
            await self._packages.install(package_id, project_root)

            # Refresh project config using existing ConfigManager
            project = self._config.load(project_root)

            self._update_state(
                projects={**self.state.projects, project_root: project},
                package_operations={**self.state.package_operations, package_id: 'complete'}
            )

        except Exception as e:
            self._update_state(
                package_operations={**self.state.package_operations, package_id: 'error'},
                errors={f'package:{package_id}': str(e)}
            )

    async def _handle_open_file(self, file: str, line: int | None) -> None:
        # Backend can trigger VS Code to open file via LSP or command server
        # This keeps VS Code-specific logic in the communication layer
        await self._notify_vscode('openFile', {'file': file, 'line': line})

    # ─────────────────────────────────────────────────────────────────────────
    # State management
    # ─────────────────────────────────────────────────────────────────────────

    def _update_state(self, **updates) -> None:
        self.state = self.state.model_copy(update=updates)
        self._broadcast_state()

    async def _broadcast_state(self) -> None:
        """Send state to all connected webviews."""
        message = json.dumps({'type': 'state', 'data': self.state.model_dump()})
        for ws in self.connections:
            await ws.send_text(message)

    async def _broadcast_event(self, event: str, data: dict) -> None:
        """Send live event to all connected webviews."""
        message = json.dumps({'type': 'event', 'event': event, 'data': data})
        for ws in self.connections:
            await ws.send_text(message)
```

### 7.7 Why All Logic in Backend?

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     WHY PUT ALL LOGIC IN PYTHON BACKEND?                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  1. REUSE EXISTING ATOPILE CODE                                                  │
│     • ConfigManager already parses ato.yaml                                     │
│     • BuildRunner already executes builds                                       │
│     • PackageService already handles ato add/remove                             │
│     • Don't reimplement in TypeScript - just wrap in Python                     │
│                                                                                  │
│  2. SINGLE SOURCE OF TRUTH                                                       │
│     • State lives in Python backend (UIStateManager)                            │
│     • Webview is just a "view" of that state                                   │
│     • Extension is just a launcher - no state                                   │
│     • No synchronization issues between multiple copies                         │
│                                                                                  │
│  3. SIMPLER EXTENSION                                                            │
│     • Extension only does: install uv, install ato, start backend, show webview │
│     • No business logic in TypeScript                                           │
│     • Easier to maintain - all logic in one place (Python)                      │
│     • Extension changes rarely needed                                           │
│                                                                                  │
│  4. TESTABILITY                                                                  │
│     • Python backend is easily unit tested with pytest                          │
│     • Mock ConfigManager, BuildRunner, etc.                                     │
│     • Webview tests are just "does it render state correctly?"                 │
│     • No need to test TypeScript business logic                                 │
│                                                                                  │
│  5. PORTABILITY                                                                  │
│     • Same Python backend could serve web dashboard                             │
│     • Same backend could serve CLI dashboard                                    │
│     • Different frontends, same logic                                           │
│                                                                                  │
│  6. DEVELOPMENT EXPERIENCE                                                       │
│     • Vite HMR for fast UI iteration on webview                                 │
│     • Python changes just restart backend                                       │
│     • Don't need to reload VS Code extension for logic changes                  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.8 Data Flow Summary

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ EXAMPLE: User clicks "Install Package"                                           │
└─────────────────────────────────────────────────────────────────────────────────┘

1. WEBVIEW (React)
   User clicks button
        │
        ▼
   dispatchAction('installPackage', { packageId: 'atopile/resistors' })
        │
        ▼
   websocket.send({ type: 'action', action: 'installPackage', payload: {...} })
        │
        ▼ WebSocket (DIRECT to backend - extension NOT involved)
────────────────────────────────────────────────────────────────────────────────────

2. PYTHON BACKEND (state/ui_state_manager.py)
   ws_handler receives message
        │
        ▼
   state_manager.handle_action('installPackage', { packageId: 'atopile/resistors' })
        │
        ▼
   _handle_install_package({ packageId })
        │
        ├──▶ _update_state(package_operations={packageId: 'installing'})
        │           │
        │           ▼ _broadcast_state()
        │    websocket.send({ type: 'state', data: newState })
        │           │
        │           ▼ Webview re-renders with loading spinner
        │
        ├──▶ packages.install(packageId, projectRoot)  ◄── Use existing atopile!
        │           │
        │           ▼ Runs: ato add atopile/resistors
        │    Returns success
        │
        ├──▶ config.load(projectRoot)  ◄── Refresh using existing ConfigManager
        │           │
        │           ▼ Returns updated project with new dependency
        │
        └──▶ _update_state(
               projects={root: updatedProject},
               package_operations={packageId: 'complete'}
             )
                    │
                    ▼ _broadcast_state()
             websocket.send({ type: 'state', data: newState })
                    │
                    ▼ WebSocket
────────────────────────────────────────────────────────────────────────────────────

3. WEBVIEW (React)
        │
        ▼
   ws.onmessage receives new state
        │
        ▼
   setState(message.data)
        │
        ▼
   Components re-render showing package installed ✓


┌─────────────────────────────────────────────────────────────────────────────────┐
│ NOTE: The VS Code extension is NOT in this data flow!                            │
│                                                                                  │
│ Extension only:                                                                  │
│   1. Installed uv and atopile at startup                                        │
│   2. Started the Python backend server                                          │
│   3. Created the webview and gave it the WebSocket URL                          │
│                                                                                  │
│ After that, the extension does NOTHING. It's just a container.                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 7.10 Simplified Webview Structure

Since the webview has no business logic, its structure is minimal:

```
webviews/
├── src/
│   ├── main.tsx                 # Entry point
│   ├── App.tsx                  # State receiver, action dispatcher
│   │
│   ├── context/                 # Simple React context (NO logic hooks)
│   │   ├── StateContext.tsx     # Holds state from extension
│   │   └── ActionContext.tsx    # Dispatch function to extension
│   │
│   ├── components/              # Pure presentational components
│   │   ├── Sidebar/
│   │   │   ├── index.tsx
│   │   │   ├── ProjectsSection.tsx
│   │   │   ├── BuildQueueSection.tsx
│   │   │   └── ProblemsSection.tsx
│   │   │
│   │   ├── LogViewer/
│   │   │   ├── index.tsx
│   │   │   ├── LogEntry.tsx
│   │   │   └── LogFilters.tsx
│   │   │
│   │   └── shared/
│   │       ├── Button.tsx
│   │       ├── Spinner.tsx
│   │       └── CollapsibleSection.tsx
│   │
│   ├── selectors/               # Memoized state selectors (optional, for performance)
│   │   ├── projects.ts          # selectProjects(state) → ProjectViewModel[]
│   │   ├── builds.ts            # selectBuilds(state) → BuildViewModel[]
│   │   └── problems.ts          # selectProblems(state) → ProblemViewModel[]
│   │
│   └── types/                   # TypeScript types (shared with extension)
│       ├── state.ts             # UIState type
│       ├── actions.ts           # Action types
│       └── models.ts            # Project, Build, Package, etc.
│
├── vite.config.ts               # Vite configuration
├── package.json
└── tsconfig.json

NO logic/, NO api/, NO hooks/ for business logic
The webview is JUST rendering + dispatching
```

**Key difference from typical React apps:**
- NO `useEffect` for data fetching
- NO `useState` for form state that calls APIs
- NO custom hooks that encapsulate business logic
- Just `useState` to hold what the extension sends
- Just `useContext` to read state and dispatch actions

```typescript
// webviews/src/components/ProjectsSection.tsx

import { useContext, useMemo } from 'react';
import { StateContext, ActionContext } from '../context';
import { selectProjects } from '../selectors/projects';

export function ProjectsSection() {
  const state = useContext(StateContext);
  const dispatch = useContext(ActionContext);

  // Selector transforms state for display (memoized)
  const projects = useMemo(() => selectProjects(state), [state]);

  return (
    <section>
      <h2>Projects</h2>
      {projects.map(project => (
        <div
          key={project.root}
          onClick={() => dispatch('selectProject', { projectRoot: project.root })}
        >
          {project.name}
          {project.isSelected && ' ✓'}
        </div>
      ))}
    </section>
  );
}

// NO API calls, NO business logic
// Just: read state → render → dispatch on click
```

### 7.11 The Model Layer In Depth

The Model layer defines the **shape of data** throughout the application. It serves as the contract between frontend and backend.

#### 7.11.1 Model Type Definitions

```typescript
// webviews/src/logic/models/package.ts

/**
 * Package as returned from the packages.atopile.io API
 * This is the "raw" API response shape
 */
export interface PackageAPIResponse {
  id: string;
  name: string;
  description: string;
  author: string;
  version: string;
  downloads: number;
  created_at: string;      // ISO date string
  updated_at: string;      // ISO date string
  dependencies: string[];
  tags: string[];
  repository_url: string | null;
  documentation_url: string | null;
}

/**
 * Package as stored in UIState
 * Normalized for efficient lookups and updates
 */
export interface Package {
  id: string;
  name: string;
  description: string;
  author: string;
  latestVersion: string;
  installedVersion: string | null;  // null if not installed
  isInstalled: boolean;
  isUpdatable: boolean;             // installedVersion < latestVersion
  downloadCount: number;
  tags: string[];
  repositoryUrl: string | null;
}

/**
 * Package as displayed in UI components
 * Formatted for presentation
 */
export interface PackageViewModel {
  id: string;
  displayName: string;              // e.g., "atopile/resistors"
  description: string;
  authorDisplay: string;            // e.g., "by atopile"
  versionDisplay: string;           // e.g., "v1.2.3" or "v1.0.0 → v1.2.3"
  statusBadge: 'installed' | 'updatable' | 'available';
  downloadCountFormatted: string;   // e.g., "1.2k downloads"
  tags: string[];
  actions: PackageAction[];         // Available actions based on state
}

export type PackageAction =
  | { type: 'install' }
  | { type: 'update' }
  | { type: 'remove' }
  | { type: 'viewDetails' };
```

#### 7.11.2 Model Relationships

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MODEL RELATIONSHIPS                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Project (1) ────────< Build (many)                                     │
│     │                     │                                              │
│     │                     └────────< Stage (many)                       │
│     │                                   │                                │
│     │                                   └────────< Problem (many)       │
│     │                                                                    │
│     └────────< InstalledPackage (many)                                  │
│                     │                                                    │
│                     └──── references ──── Package (registry)            │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  UIState contains:                                               │    │
│  │    projects: Map<projectRoot, Project>                          │    │
│  │    builds: Map<buildId, Build>                                  │    │
│  │    packages: Map<packageId, Package>                            │    │
│  │    problems: Map<buildId, Problem[]>                            │    │
│  │    installedPackages: Map<projectRoot, Map<packageId, version>> │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 7.11.3 All Model Types

```typescript
// webviews/src/logic/models/index.ts

// ═══════════════════════════════════════════════════════════════════════
// PROJECT MODELS
// ═══════════════════════════════════════════════════════════════════════

export interface Project {
  root: string;                      // Absolute path to project root
  name: string;                      // From ato.yaml or directory name
  manifestPath: string;              // Path to ato.yaml
  targets: string[];                 // Build target IDs in this project
  installedPackages: Map<string, string>;  // packageId → version
}

export interface Target {
  id: string;                        // Unique identifier (root + buildName)
  projectRoot: string;               // Parent project
  buildName: string;                 // Name from ato.yaml builds section
  entry: string;                     // Entry point (e.g., "main.ato:App")
  pcbPath: string | null;            // Expected .kicad_pcb path
  modelPath: string | null;          // Expected .glb path
}

// ═══════════════════════════════════════════════════════════════════════
// BUILD MODELS
// ═══════════════════════════════════════════════════════════════════════

export type BuildStatus =
  | 'pending'
  | 'building'
  | 'success'
  | 'failed'
  | 'cancelled';

export interface Build {
  id: string;
  targetId: string;
  status: BuildStatus;
  startedAt: Date | null;
  completedAt: Date | null;
  duration: number | null;           // milliseconds
  stages: Stage[];
  currentStage: string | null;
  errorMessage: string | null;
}

export interface Stage {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped';
  startedAt: Date | null;
  completedAt: Date | null;
  logs: LogEntry[];
}

export interface LogEntry {
  timestamp: Date;
  level: 'debug' | 'info' | 'warning' | 'error' | 'alert';
  message: string;
  source: string;                    // Stage or component that emitted
}

// ═══════════════════════════════════════════════════════════════════════
// PROBLEM MODELS
// ═══════════════════════════════════════════════════════════════════════

export type ProblemSeverity = 'error' | 'warning' | 'info' | 'hint';

export interface Problem {
  id: string;
  buildId: string;
  stageId: string;
  severity: ProblemSeverity;
  message: string;
  file: string | null;
  line: number | null;
  column: number | null;
  code: string | null;               // Error code (e.g., "E001")
  source: string;                    // "atopile" | "kicad" | "solver"
}

// ═══════════════════════════════════════════════════════════════════════
// PACKAGE MODELS
// ═══════════════════════════════════════════════════════════════════════

export interface Package {
  id: string;                        // e.g., "atopile/resistors"
  name: string;
  description: string;
  author: string;
  latestVersion: string;
  installedVersion: string | null;
  isInstalled: boolean;
  isUpdatable: boolean;
  downloadCount: number;
  tags: string[];
  repositoryUrl: string | null;
  documentationUrl: string | null;
}

export interface PackageDetails extends Package {
  readme: string | null;
  changelog: string | null;
  versions: PackageVersion[];
  dependencies: PackageDependency[];
}

export interface PackageVersion {
  version: string;
  publishedAt: Date;
  downloads: number;
}

export interface PackageDependency {
  packageId: string;
  versionConstraint: string;         // e.g., "^1.0.0"
}

// ═══════════════════════════════════════════════════════════════════════
// ATOPILE BINARY MODELS
// ═══════════════════════════════════════════════════════════════════════

export type AtopileSource = 'release' | 'branch' | 'local';

export interface AtopileInstallation {
  source: AtopileSource;
  version: string | null;            // For 'release' source
  branch: string | null;             // For 'branch' source
  localPath: string | null;          // For 'local' source
  resolvedBinaryPath: string | null;
  isInstalling: boolean;
  error: string | null;
}

export interface AtopileVersion {
  version: string;
  publishedAt: Date;
  isPrerelease: boolean;
}
```

### 7.12 The API Layer In Depth

The API layer lives in the **Python backend**, providing WebSocket and REST endpoints. The webview communicates directly with these endpoints - **not through the extension**.

#### 7.12.1 Backend API Architecture (Python)

```python
# backend/server/routes/ui.py

from fastapi import APIRouter, WebSocket
from ..state import UIStateManager

router = APIRouter()

@router.websocket("/ws/ui")
async def ui_websocket(websocket: WebSocket, state_manager: UIStateManager):
    """
    Main WebSocket endpoint for UI communication.
    Webview connects DIRECTLY here - extension is NOT involved.
    """
    await websocket.accept()
    state_manager.connections.add(websocket)

    # Send initial state
    await websocket.send_json({'type': 'state', 'data': state_manager.state.model_dump()})

    try:
        while True:
            message = await websocket.receive_json()
            if message['type'] == 'action':
                await state_manager.handle_action(message['action'], message['payload'])
    finally:
        state_manager.connections.discard(websocket)
```

#### 7.12.2 TypeScript Types for Frontend

The webview uses TypeScript types that match the backend Pydantic models:

```typescript
// webviews/src/types/api.ts (generated from Pydantic or manually maintained)

import type {
  Package, PackageDetails,
  Build,
  Project,
  AtopileVersion
} from './models';

/**
 * WebSocket message types - matches backend protocol
 */
export type WebSocketMessage =
  | { type: 'state'; data: UIState }
  | { type: 'patch'; path: string[]; value: unknown }
  | { type: 'event'; event: string; data: unknown };

/**
 * Action message sent from webview to backend
 */
export type ActionMessage = {
  type: 'action';
  action: string;
  payload: unknown;
};

  // ─────────────────────────────────────────────────────────────────────
  // PACKAGES API
  // ─────────────────────────────────────────────────────────────────────

  packages = {
    /**
     * Search packages in the registry
     */
    search: async (query: string, options?: PackageSearchOptions): Promise<Package[]> => {
      return this.bridge.send({
        type: 'api.packages.search',
        payload: { query, ...options }
      });
    },

    /**
     * Get detailed information about a specific package
     */
    getDetails: async (packageId: string): Promise<PackageDetails> => {
      return this.bridge.send({
        type: 'api.packages.getDetails',
        payload: { packageId }
      });
    },

    /**
     * Get packages installed in a project
     */
    getInstalled: async (projectRoot: string): Promise<InstalledPackage[]> => {
      return this.bridge.send({
        type: 'api.packages.getInstalled',
        payload: { projectRoot }
      });
    },

    /**
     * Install a package into a project
     */
    install: async (packageId: string, projectRoot: string, version?: string): Promise<void> => {
      return this.bridge.send({
        type: 'api.packages.install',
        payload: { packageId, projectRoot, version }
      });
    },

    /**
     * Update a package to latest version
     */
    update: async (packageId: string, projectRoot: string): Promise<void> => {
      return this.bridge.send({
        type: 'api.packages.update',
        payload: { packageId, projectRoot }
      });
    },

    /**
     * Remove a package from a project
     */
    remove: async (packageId: string, projectRoot: string): Promise<void> => {
      return this.bridge.send({
        type: 'api.packages.remove',
        payload: { packageId, projectRoot }
      });
    }
  };

  // ─────────────────────────────────────────────────────────────────────
  // BUILDS API
  // ─────────────────────────────────────────────────────────────────────

  builds = {
    /**
     * Start a build for specified targets
     */
    start: async (targetIds: string[]): Promise<Build> => {
      return this.bridge.send({
        type: 'api.builds.start',
        payload: { targetIds }
      });
    },

    /**
     * Cancel a running build
     */
    cancel: async (buildId: string): Promise<void> => {
      return this.bridge.send({
        type: 'api.builds.cancel',
        payload: { buildId }
      });
    },

    /**
     * Get build details including logs
     */
    get: async (buildId: string): Promise<Build> => {
      return this.bridge.send({
        type: 'api.builds.get',
        payload: { buildId }
      });
    },

    /**
     * Get recent builds for a project
     */
    list: async (projectRoot: string, limit?: number): Promise<Build[]> => {
      return this.bridge.send({
        type: 'api.builds.list',
        payload: { projectRoot, limit: limit ?? 10 }
      });
    }
  };

  // ─────────────────────────────────────────────────────────────────────
  // PROJECTS API
  // ─────────────────────────────────────────────────────────────────────

  projects = {
    /**
     * Discover all projects in workspace
     */
    discover: async (): Promise<Project[]> => {
      return this.bridge.send({
        type: 'api.projects.discover',
        payload: {}
      });
    },

    /**
     * Get project details including targets
     */
    get: async (projectRoot: string): Promise<Project> => {
      return this.bridge.send({
        type: 'api.projects.get',
        payload: { projectRoot }
      });
    },

    /**
     * Get modules defined in a project
     */
    getModules: async (projectRoot: string): Promise<Module[]> => {
      return this.bridge.send({
        type: 'api.projects.getModules',
        payload: { projectRoot }
      });
    },

    /**
     * Get variables/parameters in a project
     */
    getVariables: async (projectRoot: string): Promise<Variable[]> => {
      return this.bridge.send({
        type: 'api.projects.getVariables',
        payload: { projectRoot }
      });
    }
  };

  // ─────────────────────────────────────────────────────────────────────
  // ATOPILE API
  // ─────────────────────────────────────────────────────────────────────

  atopile = {
    /**
     * Get available atopile versions
     */
    getVersions: async (): Promise<AtopileVersion[]> => {
      return this.bridge.send({
        type: 'api.atopile.getVersions',
        payload: {}
      });
    },

    /**
     * Get current installation info
     */
    getInstallation: async (): Promise<AtopileInstallation> => {
      return this.bridge.send({
        type: 'api.atopile.getInstallation',
        payload: {}
      });
    },

    /**
     * Set the atopile version/source
     */
    setVersion: async (source: AtopileSource, value: string): Promise<void> => {
      return this.bridge.send({
        type: 'api.atopile.setVersion',
        payload: { source, value }
      });
    }
  };
}

// ─────────────────────────────────────────────────────────────────────────
// API REQUEST/RESPONSE TYPES
// ─────────────────────────────────────────────────────────────────────────

export interface PackageSearchOptions {
  tags?: string[];
  author?: string;
  limit?: number;
  offset?: number;
}

export interface InstalledPackage {
  packageId: string;
  version: string;
  installedAt: Date;
}

export interface Module {
  name: string;
  file: string;
  line: number;
  type: 'module' | 'component' | 'interface';
}

export interface Variable {
  name: string;
  value: string;
  unit: string | null;
  file: string;
  line: number;
}
```

#### 7.12.2 Bridge Message Types

```typescript
// webviews/src/logic/api/messages.ts

/**
 * Messages sent from webview to extension
 */
export type BridgeMessage =
  // Package operations
  | { type: 'api.packages.search'; payload: { query: string; tags?: string[]; limit?: number } }
  | { type: 'api.packages.getDetails'; payload: { packageId: string } }
  | { type: 'api.packages.getInstalled'; payload: { projectRoot: string } }
  | { type: 'api.packages.install'; payload: { packageId: string; projectRoot: string; version?: string } }
  | { type: 'api.packages.update'; payload: { packageId: string; projectRoot: string } }
  | { type: 'api.packages.remove'; payload: { packageId: string; projectRoot: string } }

  // Build operations
  | { type: 'api.builds.start'; payload: { targetIds: string[] } }
  | { type: 'api.builds.cancel'; payload: { buildId: string } }
  | { type: 'api.builds.get'; payload: { buildId: string } }
  | { type: 'api.builds.list'; payload: { projectRoot: string; limit: number } }

  // Project operations
  | { type: 'api.projects.discover'; payload: {} }
  | { type: 'api.projects.get'; payload: { projectRoot: string } }
  | { type: 'api.projects.getModules'; payload: { projectRoot: string } }
  | { type: 'api.projects.getVariables'; payload: { projectRoot: string } }

  // Atopile operations
  | { type: 'api.atopile.getVersions'; payload: {} }
  | { type: 'api.atopile.getInstallation'; payload: {} }
  | { type: 'api.atopile.setVersion'; payload: { source: AtopileSource; value: string } }

  // Navigation (VS Code specific)
  | { type: 'navigation.openFile'; payload: { file: string; line?: number; column?: number } }
  | { type: 'navigation.revealInExplorer'; payload: { path: string } }

  // Terminal (VS Code specific)
  | { type: 'terminal.run'; payload: { command: string } }
  | { type: 'terminal.focus'; payload: {} };

/**
 * Messages sent from extension to webview
 */
export type IncomingMessage =
  // State updates
  | { type: 'state.full'; data: UIState }
  | { type: 'state.patch'; path: string[]; value: unknown }

  // Real-time events
  | { type: 'event.build.started'; data: { buildId: string; targetId: string } }
  | { type: 'event.build.progress'; data: { buildId: string; stage: string; progress: number } }
  | { type: 'event.build.completed'; data: { buildId: string; status: BuildStatus } }
  | { type: 'event.build.log'; data: { buildId: string; entry: LogEntry } }

  // Package events
  | { type: 'event.package.installed'; data: { packageId: string; projectRoot: string } }
  | { type: 'event.package.removed'; data: { packageId: string; projectRoot: string } }

  // File system events
  | { type: 'event.file.changed'; data: { path: string } }
  | { type: 'event.project.discovered'; data: { project: Project } };
```

#### 7.12.3 Example: Package Data Flow

Here's a complete example showing how package data flows through all layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ EXAMPLE: User searches for "resistor" packages                               │
└─────────────────────────────────────────────────────────────────────────────┘

1. PRESENTATION LAYER
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ PackagesSection.tsx:                                                     │
   │   const dispatch = useDispatch();                                       │
   │   <SearchInput onChange={(q) => dispatch({                              │
   │     type: 'packages.search',                                            │
   │     payload: { query: q }                                               │
   │   })} />                                                                 │
   └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
2. LOGIC LAYER (Handler)
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ handlers/packages.ts:                                                    │
   │   async function handleSearch(logic: UILogic, event: PackageSearchEvent) {│
   │     const { query } = event.payload;                                    │
   │                                                                          │
   │     // Set loading state                                                │
   │     logic.setState(s => ({                                              │
   │       ...s,                                                              │
   │       packagesLoading: true,                                            │
   │       packagesSearchQuery: query                                        │
   │     }));                                                                 │
   │                                                                          │
   │     try {                                                               │
   │       // Call API                                                       │
   │       const results = await logic.api.packages.search(query);          │
   │                                                                          │
   │       // Transform API response → Model                                 │
   │       const packages = results.map(transformPackageResponse);          │
   │                                                                          │
   │       // Update state with new packages                                 │
   │       logic.setState(s => ({                                            │
   │         ...s,                                                            │
   │         packages: mergePackages(s.packages, packages),                  │
   │         packagesSearchResults: packages.map(p => p.id),                 │
   │         packagesLoading: false                                          │
   │       }));                                                               │
   │     } catch (error) {                                                   │
   │       logic.setState(s => ({                                            │
   │         ...s,                                                            │
   │         packagesLoading: false,                                         │
   │         packagesError: error.message                                    │
   │       }));                                                               │
   │     }                                                                    │
   │   }                                                                      │
   └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
3. API LAYER (Client)
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ api/client.ts:                                                           │
   │   packages.search = async (query) => {                                  │
   │     return this.bridge.send({                                           │
   │       type: 'api.packages.search',                                      │
   │       payload: { query }                                                │
   │     });                                                                  │
   │   }                                                                      │
   └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ postMessage
4. EXTENSION BRIDGE
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ bridge/handlers.ts:                                                      │
   │   case 'api.packages.search':                                           │
   │     const results = await packageService.search(payload.query);         │
   │     return results;                                                     │
   └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ HTTP
5. PYTHON BACKEND (or external API)
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ GET https://packages.atopile.io/api/search?q=resistor                   │
   │                                                                          │
   │ Response:                                                                │
   │ [                                                                        │
   │   {                                                                      │
   │     "id": "atopile/resistors",                                          │
   │     "name": "resistors",                                                │
   │     "description": "Common resistor footprints and symbols",            │
   │     "author": "atopile",                                                │
   │     "version": "1.2.3",                                                 │
   │     "downloads": 1234,                                                  │
   │     ...                                                                  │
   │   }                                                                      │
   │ ]                                                                        │
   └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ Response flows back up
6. MODEL TRANSFORMATION
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ models/transforms.ts:                                                    │
   │   function transformPackageResponse(api: PackageAPIResponse): Package { │
   │     return {                                                            │
   │       id: api.id,                                                       │
   │       name: api.name,                                                   │
   │       description: api.description,                                     │
   │       author: api.author,                                               │
   │       latestVersion: api.version,                                       │
   │       installedVersion: null,  // Will be enriched later               │
   │       isInstalled: false,                                               │
   │       isUpdatable: false,                                               │
   │       downloadCount: api.downloads,                                     │
   │       tags: api.tags,                                                   │
   │       repositoryUrl: api.repository_url                                 │
   │     };                                                                   │
   │   }                                                                      │
   └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
7. VIEWMODEL SELECTOR (in Hooks layer)
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ hooks/usePackages.ts:                                                    │
   │   export function usePackageSearchResults(): PackageViewModel[] {       │
   │     const state = useUIState();                                         │
   │                                                                          │
   │     return useMemo(() => {                                              │
   │       return state.packagesSearchResults                                │
   │         .map(id => state.packages.get(id))                              │
   │         .filter(Boolean)                                                │
   │         .map(pkg => ({                                                  │
   │           id: pkg.id,                                                   │
   │           displayName: pkg.id,                                          │
   │           description: pkg.description,                                 │
   │           authorDisplay: `by ${pkg.author}`,                            │
   │           versionDisplay: pkg.isUpdatable                               │
   │             ? `v${pkg.installedVersion} → v${pkg.latestVersion}`        │
   │             : `v${pkg.latestVersion}`,                                  │
   │           statusBadge: pkg.isUpdatable ? 'updatable'                    │
   │             : pkg.isInstalled ? 'installed' : 'available',              │
   │           downloadCountFormatted: formatNumber(pkg.downloadCount),      │
   │           tags: pkg.tags,                                               │
   │           actions: getAvailableActions(pkg)                             │
   │         }));                                                             │
   │     }, [state.packagesSearchResults, state.packages]);                  │
   │   }                                                                      │
   └─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
8. PRESENTATION (Re-render)
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ PackageList.tsx:                                                         │
   │   const packages = usePackageSearchResults();                           │
   │   const loading = useLoading('packages');                               │
   │                                                                          │
   │   if (loading) return <Spinner />;                                      │
   │                                                                          │
   │   return (                                                               │
   │     <ul>                                                                 │
   │       {packages.map(pkg => (                                            │
   │         <PackageItem key={pkg.id} package={pkg} />                      │
   │       ))}                                                                │
   │     </ul>                                                                │
   │   );                                                                     │
   └─────────────────────────────────────────────────────────────────────────┘
```

### 7.13 State Shape (UIState)

The UIState is the single source of truth, **owned by the Python backend** and sent to the webview via WebSocket:

```typescript
// webviews/src/types/state.ts (TypeScript mirror of Python Pydantic model)
// OR generated from backend/models/ui_state.py using pydantic2ts

export interface UIState {
  // Version for change detection
  _version: number;

  // ═══════════════════════════════════════════════════════════════════════
  // DOMAIN DATA (normalized, keyed by ID)
  // ═══════════════════════════════════════════════════════════════════════

  projects: Map<string, Project>;           // projectRoot → Project
  targets: Map<string, Target>;             // targetId → Target
  builds: Map<string, Build>;               // buildId → Build
  packages: Map<string, Package>;           // packageId → Package
  problems: Map<string, Problem[]>;         // buildId → Problem[]

  // ═══════════════════════════════════════════════════════════════════════
  // SELECTION STATE
  // ═══════════════════════════════════════════════════════════════════════

  selectedProjectRoot: string | null;
  selectedTargetIds: Set<string>;
  selectedBuildId: string | null;
  selectedPackageId: string | null;

  // ═══════════════════════════════════════════════════════════════════════
  // UI STATE
  // ═══════════════════════════════════════════════════════════════════════

  collapsedSections: Set<string>;
  expandedProjects: Set<string>;
  expandedTargets: Set<string>;

  // ═══════════════════════════════════════════════════════════════════════
  // LOADING / ERROR STATE
  // ═══════════════════════════════════════════════════════════════════════

  loading: Map<string, boolean>;            // 'projects' | 'builds' | etc.
  errors: Map<string, string>;              // 'projects' | 'builds' | etc.

  // ═══════════════════════════════════════════════════════════════════════
  // FILTER STATE
  // ═══════════════════════════════════════════════════════════════════════

  problemFilter: {
    levels: Set<ProblemSeverity>;
    buildId: string | null;
    stageId: string | null;
    searchQuery: string;
  };

  logFilter: {
    levels: Set<LogLevel>;
    stages: Set<string>;
    searchQuery: string;
    autoScroll: boolean;
    timestampMode: 'relative' | 'absolute';
  };

  packagesSearchQuery: string;
  packagesSearchResults: string[];          // Package IDs

  // ═══════════════════════════════════════════════════════════════════════
  // ATOPILE INSTALLATION STATE
  // ═══════════════════════════════════════════════════════════════════════

  atopile: AtopileInstallation;
  availableAtopileVersions: AtopileVersion[];
}

// Initial state factory
export function createInitialState(): UIState {
  return {
    _version: 0,

    projects: new Map(),
    targets: new Map(),
    builds: new Map(),
    packages: new Map(),
    problems: new Map(),

    selectedProjectRoot: null,
    selectedTargetIds: new Set(),
    selectedBuildId: null,
    selectedPackageId: null,

    collapsedSections: new Set(),
    expandedProjects: new Set(),
    expandedTargets: new Set(),

    loading: new Map(),
    errors: new Map(),

    problemFilter: {
      levels: new Set(['error', 'warning']),
      buildId: null,
      stageId: null,
      searchQuery: ''
    },

    logFilter: {
      levels: new Set(['info', 'warning', 'error', 'alert']),
      stages: new Set(),
      searchQuery: '',
      autoScroll: true,
      timestampMode: 'relative'
    },

    packagesSearchQuery: '',
    packagesSearchResults: [],

    atopile: {
      source: 'release',
      version: null,
      branch: null,
      localPath: null,
      resolvedBinaryPath: null,
      isInstalling: false,
      error: null
    },
    availableAtopileVersions: []
  };
}
```

### 7.14 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Maps over Arrays** | O(1) lookups, easy updates without array scanning |
| **Normalized State** | Avoid data duplication, single source of truth |
| **ViewModels in Webview** | Memoized selectors transform backend state for display |
| **All Logic in Python** | Reuse existing atopile code, single language for logic |
| **Direct WebSocket** | Webview talks directly to backend, extension is just launcher |
| **Minimal Extension** | Bootstrap only: install deps, start backend, create webview |
| **Pydantic Models** | Define once in Python, generate TypeScript types |

### 7.15 Backend Model Integration

A critical design principle: **the extension should NOT reimplement existing atopile functionality**. Instead, the backend (Python dashboard server) should integrate with and expose existing atopile systems through a unified API.

#### 7.15.1 Model Source Architecture

The backend aggregates data from multiple sources and presents a unified model to the frontend:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND MODEL SOURCES                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                    UNIFIED API LAYER (FastAPI)                           │    │
│  │  GET /api/projects/{root}/config                                        │    │
│  │  GET /api/projects/{root}/builds                                        │    │
│  │  GET /api/projects/{root}/modules                                       │    │
│  │  WS  /ws/builds/{build_id}/logs                                         │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
│                    ┌─────────────────┼─────────────────┐                        │
│                    ▼                 ▼                 ▼                        │
│  ┌──────────────────────┐ ┌──────────────────┐ ┌──────────────────────┐        │
│  │  ConfigManager       │ │  BuildRunner     │ │  LSP/Compiler        │        │
│  │  (existing atopile)  │ │  (build process) │ │  (existing atopile)  │        │
│  ├──────────────────────┤ ├──────────────────┤ ├──────────────────────┤        │
│  │ • ato.yaml parsing   │ │ • Build logs     │ │ • Module discovery   │        │
│  │ • Project settings   │ │ • Stage progress │ │ • Variable values    │        │
│  │ • Package manifest   │ │ • Problems/errors│ │ • Type information   │        │
│  │ • Build targets      │ │ • Output paths   │ │ • Diagnostics        │        │
│  │ • Paths resolution   │ │ • Duration stats │ │ • Completions        │        │
│  └──────────────────────┘ └──────────────────┘ └──────────────────────┘        │
│           │                       │                       │                     │
│           │                       │                       │                     │
│           ▼                       ▼                       ▼                     │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                    AGGREGATED PROJECT MODEL                               │  │
│  │                                                                           │  │
│  │  ProjectModel {                                                          │  │
│  │    // From ConfigManager                                                 │  │
│  │    config: ProjectConfig,                                                │  │
│  │    targets: Target[],                                                    │  │
│  │    packages: InstalledPackage[],                                         │  │
│  │                                                                           │  │
│  │    // From BuildRunner                                                   │  │
│  │    builds: Build[],                                                      │  │
│  │    currentBuild: Build | null,                                           │  │
│  │    problems: Problem[],                                                  │  │
│  │                                                                           │  │
│  │    // From LSP/Compiler                                                  │  │
│  │    modules: Module[],                                                    │  │
│  │    variables: Variable[],                                                │  │
│  │    diagnostics: Diagnostic[],                                            │  │
│  │  }                                                                        │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### 7.15.2 ConfigManager Integration

The backend wraps the existing `atopile` ConfigManager rather than reimplementing YAML parsing:

```python
# backend/core/project_service.py

from atopile.config import ConfigManager  # Use existing atopile code!
from pydantic import BaseModel

class ProjectConfig(BaseModel):
    """Pydantic model exposed to frontend - derived from ConfigManager"""
    root: str
    name: str
    atopile_version: str | None
    paths: ProjectPaths
    builds: dict[str, BuildConfig]
    dependencies: list[Dependency]

class ProjectPaths(BaseModel):
    src: str
    layout: str
    build: str
    footprints: str | None

class BuildConfig(BaseModel):
    entry: str
    targets: list[str] | None

class Dependency(BaseModel):
    name: str
    version: str
    source: str  # "registry" | "git" | "local"


class ProjectService:
    """
    Wraps atopile's ConfigManager to provide project configuration.
    Does NOT reimplement config parsing - uses existing atopile code.
    """

    def __init__(self, config_manager: ConfigManager):
        self._config = config_manager

    def get_project_config(self, project_root: str) -> ProjectConfig:
        """
        Get project configuration by wrapping ConfigManager.
        Transforms internal atopile types to API-friendly Pydantic models.
        """
        # Use existing atopile ConfigManager
        ato_config = self._config.load(project_root)

        # Transform to API model (don't expose internal atopile types)
        return ProjectConfig(
            root=project_root,
            name=ato_config.project_name,
            atopile_version=ato_config.requires_atopile,
            paths=ProjectPaths(
                src=str(ato_config.paths.src),
                layout=str(ato_config.paths.layout),
                build=str(ato_config.paths.build),
                footprints=str(ato_config.paths.footprints) if ato_config.paths.footprints else None,
            ),
            builds={
                name: BuildConfig(entry=build.entry, targets=build.targets)
                for name, build in ato_config.builds.items()
            },
            dependencies=[
                Dependency(name=dep.name, version=dep.version, source=dep.source)
                for dep in ato_config.dependencies
            ]
        )

    def get_build_targets(self, project_root: str) -> list[Target]:
        """Get available build targets for a project."""
        config = self.get_project_config(project_root)

        return [
            Target(
                id=f"{project_root}:{name}",
                project_root=project_root,
                build_name=name,
                entry=build.entry,
                pcb_path=self._compute_pcb_path(project_root, name),
                model_path=self._compute_model_path(project_root, name),
            )
            for name, build in config.builds.items()
        ]

    def get_installed_packages(self, project_root: str) -> list[InstalledPackage]:
        """Get packages installed in a project from ato.yaml."""
        config = self.get_project_config(project_root)

        return [
            InstalledPackage(
                package_id=dep.name,
                version=dep.version,
                source=dep.source
            )
            for dep in config.dependencies
        ]
```

#### 7.15.3 Cross-Model Relationships

The backend maintains relationships between different model sources:

```python
# backend/core/aggregator.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class AggregatedProject:
    """
    Combines data from multiple sources into a unified project view.
    This is what gets sent to the frontend.
    """
    # Core identity
    root: str
    name: str

    # From ConfigManager
    config: ProjectConfig
    targets: list[Target]
    installed_packages: list[InstalledPackage]

    # From BuildRunner (live state)
    builds: list[Build]
    current_build: Optional[Build]
    problems: list[Problem]

    # From LSP/Compiler
    modules: list[Module]
    variables: list[Variable]

    # Computed relationships
    @property
    def updatable_packages(self) -> list[InstalledPackage]:
        """Packages with newer versions available."""
        return [p for p in self.installed_packages if p.has_update]

    @property
    def last_successful_build(self) -> Optional[Build]:
        """Most recent successful build."""
        return next(
            (b for b in reversed(self.builds) if b.status == 'success'),
            None
        )

    @property
    def all_problems(self) -> list[Problem]:
        """Problems from current build + LSP diagnostics."""
        build_problems = self.current_build.problems if self.current_build else []
        # Deduplicate by file:line:message
        seen = set()
        result = []
        for p in build_problems + self.problems:
            key = (p.file, p.line, p.message)
            if key not in seen:
                seen.add(key)
                result.append(p)
        return result


class ProjectAggregator:
    """
    Aggregates data from multiple sources into unified project models.
    Acts as the single source of truth for the API layer.
    """

    def __init__(
        self,
        project_service: ProjectService,      # Wraps ConfigManager
        build_service: BuildService,          # Manages build state
        lsp_service: LSPService,              # Wraps LSP client
    ):
        self._projects = project_service
        self._builds = build_service
        self._lsp = lsp_service

        # Cache for efficiency
        self._cache: dict[str, AggregatedProject] = {}

        # Subscribe to changes from each source
        self._projects.on_config_changed(self._invalidate_cache)
        self._builds.on_build_changed(self._invalidate_cache)
        self._lsp.on_diagnostics_changed(self._invalidate_cache)

    async def get_project(self, root: str) -> AggregatedProject:
        """Get aggregated project data from all sources."""
        if root in self._cache:
            return self._cache[root]

        # Gather from all sources in parallel
        config, builds, modules, variables = await asyncio.gather(
            self._projects.get_project_config(root),
            self._builds.get_builds(root),
            self._lsp.get_modules(root),
            self._lsp.get_variables(root),
        )

        aggregated = AggregatedProject(
            root=root,
            name=config.name,
            config=config,
            targets=self._projects.get_build_targets(root),
            installed_packages=self._projects.get_installed_packages(root),
            builds=builds,
            current_build=self._builds.get_current_build(root),
            problems=self._builds.get_problems(root),
            modules=modules,
            variables=variables,
        )

        self._cache[root] = aggregated
        return aggregated

    def _invalidate_cache(self, root: str):
        """Called when any source changes."""
        self._cache.pop(root, None)
```

#### 7.15.4 Live Data Integration (Builds + Logs)

Build logs and progress are streamed in real-time, integrating with the static config:

```python
# backend/core/build_service.py

import asyncio
from typing import AsyncGenerator
from datetime import datetime

class BuildService:
    """
    Manages build execution and state.
    Integrates with ConfigManager for target resolution.
    """

    def __init__(self, project_service: ProjectService):
        self._projects = project_service
        self._active_builds: dict[str, Build] = {}
        self._build_history: dict[str, list[Build]] = {}  # project_root -> builds
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    async def start_build(self, target_ids: list[str]) -> Build:
        """
        Start a build for the specified targets.
        Resolves target config from ConfigManager.
        """
        # Group targets by project
        by_project: dict[str, list[str]] = {}
        for target_id in target_ids:
            project_root, build_name = target_id.rsplit(':', 1)
            by_project.setdefault(project_root, []).append(build_name)

        # Validate targets exist in config
        for project_root, build_names in by_project.items():
            config = self._projects.get_project_config(project_root)
            for name in build_names:
                if name not in config.builds:
                    raise ValueError(f"Unknown build target: {name}")

        # Create build record
        build = Build(
            id=f"build-{datetime.now().timestamp()}",
            target_ids=target_ids,
            status='pending',
            started_at=datetime.now(),
            stages=[],
            problems=[],
        )

        # Start build process
        asyncio.create_task(self._run_build(build))

        return build

    async def stream_logs(self, build_id: str) -> AsyncGenerator[LogEntry, None]:
        """
        Stream logs for a build in real-time.
        Used by WebSocket endpoint.
        """
        queue: asyncio.Queue[LogEntry] = asyncio.Queue()
        self._subscribers.setdefault(build_id, []).append(queue)

        try:
            while True:
                entry = await queue.get()
                if entry is None:  # Sentinel for build complete
                    break
                yield entry
        finally:
            self._subscribers[build_id].remove(queue)

    async def _run_build(self, build: Build):
        """Execute the build and emit logs."""
        build.status = 'building'
        self._active_builds[build.id] = build

        try:
            # Use atopile CLI to run build
            process = await asyncio.create_subprocess_exec(
                'ato', 'build',
                *[f'--build={t.split(":")[1]}' for t in build.target_ids],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Stream stdout
            async for line in process.stdout:
                entry = self._parse_log_line(line.decode())
                build.stages[-1].logs.append(entry) if build.stages else None
                await self._emit_log(build.id, entry)

            await process.wait()
            build.status = 'success' if process.returncode == 0 else 'failed'

        except Exception as e:
            build.status = 'failed'
            build.error_message = str(e)

        finally:
            build.completed_at = datetime.now()
            del self._active_builds[build.id]

            # Notify subscribers build is complete
            for queue in self._subscribers.get(build.id, []):
                await queue.put(None)
```

#### 7.15.5 Model Enrichment Pattern

Frontend models are enriched by combining data from multiple backend sources:

```typescript
// Frontend: logic/handlers/projects.ts

async function handleLoadProject(logic: UILogic, event: LoadProjectEvent) {
  const { projectRoot } = event.payload;

  logic.setState(s => setLoading(s, 'project', true));

  try {
    // Single API call returns aggregated data
    const project = await logic.api.projects.get(projectRoot);

    // API response already combines:
    // - Config (from ConfigManager)
    // - Build history (from BuildService)
    // - Modules/variables (from LSP)
    // - Installed packages (from ConfigManager)

    // Enrich packages with registry data for update status
    const installedIds = project.installedPackages.map(p => p.packageId);
    const registryPackages = await logic.api.packages.getMany(installedIds);

    // Merge to determine which packages have updates
    const enrichedPackages = project.installedPackages.map(installed => {
      const registry = registryPackages.find(r => r.id === installed.packageId);
      return {
        ...installed,
        latestVersion: registry?.latestVersion ?? installed.version,
        isUpdatable: registry ?
          semver.gt(registry.latestVersion, installed.version) : false,
        description: registry?.description ?? '',
      };
    });

    logic.setState(s => ({
      ...s,
      projects: new Map(s.projects).set(projectRoot, {
        ...project,
        installedPackages: enrichedPackages,
      }),
      // Also populate related Maps for easy lookup
      targets: mergeIntoMap(s.targets, project.targets, t => t.id),
      builds: mergeIntoMap(s.builds, project.builds, b => b.id),
      modules: new Map(s.modules).set(projectRoot, project.modules),
    }));

  } catch (error) {
    logic.setState(s => setError(s, 'project', error.message));
  } finally {
    logic.setState(s => setLoading(s, 'project', false));
  }
}
```

#### 7.15.6 Model Source Summary

| Model | Primary Source | Enrichment Sources | Update Trigger |
|-------|---------------|-------------------|----------------|
| **Project** | ConfigManager (ato.yaml) | - | File save, manual refresh |
| **Target** | ConfigManager (builds section) | BuildService (last build status) | Config change |
| **Build** | BuildService (runtime) | ConfigManager (target info) | Build start/complete |
| **Stage** | BuildService (runtime) | - | Build progress |
| **LogEntry** | BuildService (stdout/stderr) | - | Real-time stream |
| **Problem** | BuildService + LSP | - | Build complete, file save |
| **Package (installed)** | ConfigManager (dependencies) | Package Registry (updates) | Config change |
| **Package (registry)** | packages.atopile.io API | - | Search, periodic refresh |
| **Module** | LSP/Compiler | - | File save |
| **Variable** | LSP/Compiler | Solver (resolved values) | Build complete |

#### 7.15.7 Why Not Reimplement?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     REIMPLEMENT vs INTEGRATE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ❌ BAD: Reimplementing ConfigManager in TypeScript                         │
│  ─────────────────────────────────────────────────────────────────────────  │
│  • Duplicates YAML parsing logic                                            │
│  • Falls out of sync when atopile changes                                   │
│  • Misses edge cases atopile handles                                        │
│  • Double maintenance burden                                                 │
│  • Can't access Python-only features (solver, compiler)                     │
│                                                                              │
│  ✅ GOOD: Wrapping ConfigManager in Python API                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│  • Single source of truth (atopile's code)                                  │
│  • Automatically gets atopile updates                                       │
│  • Full access to all atopile features                                      │
│  • API models are stable interface for frontend                             │
│  • Can add caching/aggregation without touching atopile                     │
│                                                                              │
│  The extension's job is to PRESENT data, not COMPUTE it.                    │
│  Let atopile do the heavy lifting; the extension just displays results.    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 7.15.8 API Design Principles for Model Integration

1. **Aggregate, Don't Duplicate**: API endpoints should aggregate data from multiple atopile sources, not duplicate their logic.

2. **Transform at Boundaries**: Convert internal atopile types to Pydantic models at the API layer. Don't expose internal atopile classes directly.

3. **Cache Intelligently**: Cache aggregated results, invalidate on source changes (file saves, build events).

4. **Stream Live Data**: Use WebSockets for logs, build progress, and real-time updates. Don't poll.

5. **Enrich on Frontend**: Let the frontend combine data from multiple API calls when needed (e.g., installed packages + registry data).

6. **Version the API**: Frontend models may evolve independently from atopile internals. Keep a stable API contract.

---

## 8. Complete Feature Flows: Current vs Proposed

This section documents every major feature in the extension with its current implementation flow and proposed re-architected flow.

---

### Feature 1: Language Server Protocol (LSP) Integration

**Purpose**: Provides syntax highlighting, completions, hover, go-to-definition, and diagnostics for .ato files.

**Current Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ CURRENT IMPLEMENTATION                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  extension.ts (activation)                                               │
│       │                                                                  │
│       ▼                                                                  │
│  server.ts::startOrRestartServer()                                       │
│       │                                                                  │
│       ├──▶ findAto() resolves binary path                               │
│       │                                                                  │
│       ├──▶ spawn('ato', ['lsp', 'start'])                               │
│       │                                                                  │
│       └──▶ LanguageClient connects to subprocess stdio                  │
│               │                                                          │
│               ▼                                                          │
│  VS Code ◄──── LSP Protocol ────▶ Python atopile process                │
│                                                                          │
│  Triggers for restart:                                                   │
│    - Configuration change (atopile.ato, atopile.from)                   │
│    - Build target change → notifyBuildTargetChange()                    │
│    - Manual restart command                                              │
└─────────────────────────────────────────────────────────────────────────┘

Files involved:
  - src/common/server.ts (startOrRestartServer, LanguageClient setup)
  - src/common/findbin.ts (ato binary resolution)
  - src/common/target.ts (build target change events)
```

**Proposed Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ PROPOSED IMPLEMENTATION                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  logic/handlers/lsp.ts                                                   │
│       │                                                                  │
│       ▼                                                                  │
│  dispatch({ type: 'lsp.start' })                                        │
│       │                                                                  │
│       ├──▶ setState(s => setLoading(s, 'lsp', true))                    │
│       │                                                                  │
│       ├──▶ logic.services.lsp.start(config)                             │
│       │         │                                                        │
│       │         └──▶ LspService class manages LanguageClient            │
│       │                                                                  │
│       └──▶ setState(s => ({ ...s, lspStatus: 'running' }))              │
│                                                                          │
│  dispatch({ type: 'lsp.restart' })                                      │
│       │                                                                  │
│       └──▶ Triggered by config changes, handled in lsp.ts               │
│                                                                          │
│  dispatch({ type: 'lsp.notifyBuildTarget', payload: { target } })       │
│       │                                                                  │
│       └──▶ logic.services.lsp.sendNotification(...)                     │
│                                                                          │
│  Key Changes:                                                            │
│    - LspService class encapsulates LanguageClient lifecycle             │
│    - Events for restart/status tracking flow through UILogic            │
│    - LSP status visible in UI state for user feedback                   │
└─────────────────────────────────────────────────────────────────────────┘

New files:
  - logic/services/lsp.ts (LspService class)
  - logic/handlers/lsp.ts (event handlers)
  - logic/events.ts (LspEvent types)
```

---

### Feature 2: Commands & Buttons (13 Commands)

**Purpose**: Execute atopile CLI commands from VS Code command palette and UI buttons.

**Current Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ CURRENT IMPLEMENTATION                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  package.json registers commands                                         │
│       │                                                                  │
│       ▼                                                                  │
│  buttons.ts::activateButtons(context)                                    │
│       │                                                                  │
│       └──▶ registerCommand() for each command                           │
│               │                                                          │
│               ▼                                                          │
│  Command handlers (inline functions):                                    │
│                                                                          │
│  atoBuild():                                                             │
│    1. Get selected targets from targetModule                            │
│    2. Show progress notification                                         │
│    3. Focus log viewer panel                                             │
│    4. Build command string: "ato build --build target1 --build target2" │
│    5. runAtoCommandInTerminal(command)                                   │
│    6. Emit telemetry('vsce:build_start')                                │
│                                                                          │
│  atoAddPart():                                                           │
│    1. showInputBox() for search query                                    │
│    2. runAtoCommandInTerminal('ato create part --search <query>')       │
│    3. Emit telemetry('vsce:part_create')                                │
│                                                                          │
│  atoLaunchKicad():                                                       │
│    1. Get PCB path from current target                                  │
│    2. Find KiCAD binary path                                            │
│    3. spawn(kicadPath, [pcbPath])                                       │
│    4. Emit telemetry success/fail                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

Files involved:
  - src/ui/buttons.ts (all command handlers)
  - src/common/target.ts (target state)
  - src/common/telemetry.ts (event tracking)
```

**Proposed Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ PROPOSED IMPLEMENTATION                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Extension Layer (thin):                                                 │
│  ─────────────────────                                                   │
│  buttons.ts registers commands, but delegates to UILogic:               │
│                                                                          │
│  registerCommand('atopile.build', () => {                               │
│    logic.dispatch({ type: 'commands.build' });                          │
│  });                                                                     │
│                                                                          │
│  Logic Layer:                                                            │
│  ────────────                                                            │
│  logic/handlers/commands.ts:                                             │
│                                                                          │
│  async function handleBuildCommand(logic: UILogic) {                    │
│    const targets = logic.getState().selectedTargets;                    │
│    if (targets.length === 0) {                                          │
│      logic.setState(s => addNotification(s, 'No targets selected'));    │
│      return;                                                             │
│    }                                                                     │
│                                                                          │
│    logic.setState(s => ({ ...s, buildInProgress: true }));              │
│                                                                          │
│    // Bridge to extension for VS Code-specific actions                  │
│    await logic.bridge.focusPanel('logViewer');                          │
│    await logic.bridge.runInTerminal(buildCommand(targets));             │
│                                                                          │
│    logic.telemetry.track('build_start', { targetCount: targets.length });│
│  }                                                                       │
│                                                                          │
│  async function handleAddPartCommand(logic: UILogic, { query }) {       │
│    logic.setState(s => setLoading(s, 'addPart', true));                 │
│    await logic.bridge.runInTerminal(`ato create part --search ${query}`);│
│    logic.setState(s => setLoading(s, 'addPart', false));                │
│    logic.telemetry.track('part_create');                                 │
│  }                                                                       │
│                                                                          │
│  Key Changes:                                                            │
│    - Command logic moves to handlers/commands.ts                         │
│    - ExtensionBridge handles VS Code-specific APIs                      │
│    - State updates visible in UI (loading, notifications)               │
│    - Testable without VS Code runtime                                   │
└─────────────────────────────────────────────────────────────────────────┘

New files:
  - logic/handlers/commands.ts
  - logic/services/bridge.ts (ExtensionBridge interface)
  - logic/events.ts (CommandEvent types)
```

---

### Feature 3: Project & Build Target Management

**Purpose**: Discover projects via ato.yaml files, manage selected build targets, persist selection.

**Current Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ CURRENT IMPLEMENTATION                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  target.ts (TargetModule singleton):                                     │
│       │                                                                  │
│       ├──▶ State variables:                                             │
│       │      - _selectedTargets: Set<string>                            │
│       │      - _projectRoot: string | undefined                         │
│       │      - _onNeedsRestart: EventEmitter                            │
│       │      - _onBuildTargetsChangedEvent: EventEmitter                │
│       │                                                                  │
│       ├──▶ loadTargets():                                               │
│       │      1. vscode.workspace.findFiles('**/ato.yaml')               │
│       │      2. Parse each YAML → getTargetDataFromManifest()           │
│       │      3. Populate targets Map<string, TargetData>                │
│       │      4. Auto-select if nothing selected                         │
│       │                                                                  │
│       ├──▶ selectTargets(targets: string[]):                            │
│       │      1. Update _selectedTargets                                 │
│       │      2. Fire onBuildTargetsChangedEvent                         │
│       │      3. Trigger LSP notification                                │
│       │                                                                  │
│       └──▶ Watch triggers:                                              │
│              - ato.yaml file save → reloadTargets()                     │
│              - ato binary change → reloadTargets()                      │
│                                                                          │
│  manifest.ts::getTargetDataFromManifest(yamlPath):                       │
│       1. Parse YAML                                                      │
│       2. Extract builds section                                          │
│       3. Compute expected PCB/3D paths                                   │
│       4. Return TargetData for each build                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

Files involved:
  - src/common/target.ts (TargetModule class)
  - src/common/manifest.ts (YAML parsing, path resolution)
```

**Proposed Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ PROPOSED IMPLEMENTATION                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  UIState:                                                                │
│  ─────────                                                               │
│  interface UIState {                                                     │
│    projects: Map<string, Project>;      // projectRoot → Project        │
│    targets: Map<string, TargetData>;    // targetId → TargetData        │
│    selectedProjectRoot: string | null;                                   │
│    selectedTargetIds: Set<string>;                                       │
│  }                                                                       │
│                                                                          │
│  Events:                                                                 │
│  ─────────                                                               │
│  type ProjectEvent =                                                     │
│    | { type: 'projects.refresh' }                                       │
│    | { type: 'projects.select'; payload: { projectRoot: string } }      │
│    | { type: 'targets.toggle'; payload: { targetId: string } }          │
│    | { type: 'targets.selectAll'; payload: { projectRoot: string } }    │
│    | { type: 'targets.clearAll' };                                      │
│                                                                          │
│  Handlers:                                                               │
│  ──────────                                                              │
│  logic/handlers/projects.ts:                                             │
│                                                                          │
│  async function handleRefreshProjects(logic: UILogic) {                 │
│    logic.setState(s => setLoading(s, 'projects', true));                │
│                                                                          │
│    // FileService abstracts VS Code workspace API                       │
│    const manifests = await logic.services.files.findFiles('**/ato.yaml');│
│    const projects = new Map();                                           │
│    const targets = new Map();                                            │
│                                                                          │
│    for (const manifest of manifests) {                                  │
│      const data = parseManifest(manifest);                              │
│      projects.set(data.root, data.project);                             │
│      data.targets.forEach(t => targets.set(t.id, t));                   │
│    }                                                                     │
│                                                                          │
│    logic.setState(s => ({                                               │
│      ...s,                                                               │
│      projects,                                                           │
│      targets,                                                            │
│      loading: clearLoading(s.loading, 'projects')                       │
│    }));                                                                   │
│  }                                                                       │
│                                                                          │
│  function handleToggleTarget(logic: UILogic, { targetId }) {            │
│    logic.setState(s => {                                                │
│      const selected = new Set(s.selectedTargetIds);                     │
│      if (selected.has(targetId)) {                                      │
│        selected.delete(targetId);                                       │
│      } else {                                                            │
│        selected.add(targetId);                                          │
│      }                                                                   │
│      return { ...s, selectedTargetIds: selected };                      │
│    });                                                                   │
│                                                                          │
│    // Notify LSP of target change                                       │
│    logic.dispatch({ type: 'lsp.notifyBuildTarget', payload: {...} });   │
│  }                                                                       │
│                                                                          │
│  Key Changes:                                                            │
│    - State in UILogic, not singleton module                             │
│    - FileService abstracts VS Code workspace.findFiles                  │
│    - Events for all state transitions                                   │
│    - Pure functions for manifest parsing (testable)                     │
└─────────────────────────────────────────────────────────────────────────┘

New files:
  - logic/handlers/projects.ts
  - logic/services/files.ts (FileService interface)
  - logic/utils/manifest.ts (pure parsing functions)
```

---

### Feature 4: Webview Panels (Sidebar + Log Viewer)

**Purpose**: React-based UI panels for project management and build log viewing.

**Current Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ CURRENT IMPLEMENTATION                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  vscode-panels.ts:                                                       │
│       │                                                                  │
│       ├──▶ CustomViewProvider implements WebviewViewProvider            │
│       │      - resolveWebviewView() creates webview                     │
│       │      - Loads bundled React app (main.js from webviews/dist)    │
│       │                                                                  │
│       ├──▶ Message handling (webview → extension):                      │
│       │      webview.onDidReceiveMessage(async (data) => {              │
│       │        if (data.type === 'action') {                            │
│       │          await handleAction(data, panel);                       │
│       │        }                                                         │
│       │      });                                                         │
│       │                                                                  │
│       ├──▶ handleAction() - 500+ line switch statement:                 │
│       │      case 'build': ...                                          │
│       │      case 'selectProject': ...                                  │
│       │      case 'installPackage': ...                                 │
│       │      case 'toggleLogLevel': ...                                 │
│       │      // 30+ cases                                                │
│       │                                                                  │
│       └──▶ State broadcast (extension → webview):                       │
│              appStateManager.onStateChange(state => {                   │
│                panel.webview.postMessage({ type: 'state', data: state });│
│              });                                                         │
│                                                                          │
│  Webviews (React):                                                       │
│  ─────────────────                                                       │
│  Sidebar.tsx (1100+ lines):                                              │
│       - useState for all local state                                    │
│       - useEffect for message handling                                  │
│       - Inline action functions                                         │
│       - All business logic mixed with presentation                      │
│                                                                          │
│  LogViewer.tsx:                                                          │
│       - Similar pattern to Sidebar.tsx                                  │
│       - Log filtering, search, stage management                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

Files involved:
  - src/ui/vscode-panels.ts (CustomViewProvider, handleAction)
  - webviews/src/sidebar.tsx (React component)
  - webviews/src/logViewer.tsx (React component)
```

**Proposed Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ PROPOSED IMPLEMENTATION                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Extension Layer (thin):                                                 │
│  ─────────────────────                                                   │
│  vscode-panels.ts:                                                       │
│       - Creates webview, injects UILogic bridge                         │
│       - Forwards all messages to UILogic                                │
│       - No business logic                                                │
│                                                                          │
│  webview.onDidReceiveMessage(data => {                                  │
│    // Simply forward to logic layer                                     │
│    logic.handleWebviewMessage(data);                                    │
│  });                                                                     │
│                                                                          │
│  logic.subscribe(state => {                                             │
│    panel.webview.postMessage({ type: 'state', data: state });           │
│  });                                                                     │
│                                                                          │
│  Webview Logic Layer:                                                    │
│  ────────────────────                                                    │
│  webviews/src/logic/index.ts (UILogic class)                            │
│  webviews/src/logic/events.ts (all event types)                         │
│  webviews/src/logic/handlers/*.ts (domain handlers)                     │
│                                                                          │
│  Webview React Layer:                                                    │
│  ────────────────────                                                    │
│  webviews/src/App.tsx:                                                   │
│       <LogicProvider logic={logic}>                                     │
│         <Router />                                                       │
│       </LogicProvider>                                                   │
│                                                                          │
│  webviews/src/components/Sidebar.tsx (~100 lines):                      │
│       function Sidebar() {                                               │
│         return (                                                         │
│           <div>                                                          │
│             <ProjectsSection />                                          │
│             <BuildQueueSection />                                        │
│             <ProblemsSection />                                          │
│             <PackagesSection />                                          │
│           </div>                                                         │
│         );                                                               │
│       }                                                                   │
│                                                                          │
│  webviews/src/components/ProjectsSection.tsx:                           │
│       function ProjectsSection() {                                       │
│         const dispatch = useDispatch();                                 │
│         const projects = useProjects(); // ViewModel selector           │
│                                                                          │
│         return (                                                         │
│           <CollapsibleSection title="Projects">                         │
│             {projects.map(p => (                                        │
│               <ProjectItem                                               │
│                 key={p.root}                                             │
│                 project={p}                                              │
│                 onSelect={() => dispatch({                              │
│                   type: 'projects.select',                              │
│                   payload: { projectRoot: p.root }                      │
│                 })}                                                       │
│               />                                                         │
│             ))}                                                          │
│           </CollapsibleSection>                                          │
│         );                                                               │
│       }                                                                   │
│                                                                          │
│  Key Changes:                                                            │
│    - UILogic lives IN the webview (not extension)                       │
│    - Extension becomes thin message forwarder                           │
│    - Sidebar.tsx shrinks from 1100 lines to ~100 lines                 │
│    - Each section is independent component with useDispatch            │
│    - ViewModels transform state for efficient rendering                │
└─────────────────────────────────────────────────────────────────────────┘

New files:
  - webviews/src/logic/index.ts
  - webviews/src/logic/state.ts
  - webviews/src/logic/events.ts
  - webviews/src/logic/handlers/*.ts
  - webviews/src/hooks/useLogic.tsx
  - webviews/src/components/Sidebar.tsx (refactored)
  - webviews/src/components/ProjectsSection.tsx
  - webviews/src/components/BuildQueueSection.tsx
  - webviews/src/components/ProblemsSection.tsx
  - webviews/src/components/PackagesSection.tsx
```

---

### Feature 5: Webview Communication Protocol (30+ Actions)

**Purpose**: Bidirectional message passing between webview and extension.

**Current Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ CURRENT IMPLEMENTATION                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Webview → Extension:                                                    │
│  ─────────────────────                                                   │
│  sidebar.tsx:                                                            │
│    const action = (actionName: string, args: any) => {                  │
│      vscode.postMessage({ type: 'action', action: actionName, ...args });│
│    };                                                                     │
│                                                                          │
│    // Usage scattered throughout component:                             │
│    action('build', { level: 'project', id, label });                    │
│    action('selectProject', { projectRoot });                            │
│    action('toggleTarget', { target, projectRoot });                     │
│    action('installPackage', { packageId, projectRoot });                │
│    // ... 30+ different action calls                                    │
│                                                                          │
│  vscode-panels.ts:                                                       │
│    async function handleAction(data: any, panel: WebviewPanel) {        │
│      switch (data.action) {                                             │
│        case 'build':                                                    │
│          if (data.level === 'project') { ... }                          │
│          else if (data.level === 'build') { ... }                       │
│          break;                                                          │
│        case 'selectProject':                                            │
│          targetModule.selectProject(data.projectRoot);                  │
│          break;                                                          │
│        // ... 30+ cases, 500+ lines total                               │
│      }                                                                   │
│    }                                                                     │
│                                                                          │
│  Extension → Webview:                                                    │
│  ─────────────────────                                                   │
│    // Full state broadcast on any change                                │
│    panel.webview.postMessage({ type: 'state', data: fullAppState });    │
│                                                                          │
│  Issues:                                                                 │
│    - No type safety on actions                                          │
│    - Giant switch statement                                              │
│    - Mixed sync/async handling                                          │
│    - Full state broadcast (inefficient)                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Proposed Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ PROPOSED IMPLEMENTATION                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Typed Events (webviews/src/logic/events.ts):                           │
│  ──────────────────────────────────────────────                         │
│  export type UIEvent =                                                   │
│    // Build events                                                       │
│    | { type: 'builds.start'; payload: BuildStartPayload }               │
│    | { type: 'builds.cancel'; payload: { buildId: string } }            │
│    // Project events                                                     │
│    | { type: 'projects.select'; payload: { projectRoot: string } }      │
│    | { type: 'targets.toggle'; payload: { targetId: string } }          │
│    // Package events                                                     │
│    | { type: 'packages.install'; payload: PackageInstallPayload }       │
│    // ... all 30+ events typed                                          │
│                                                                          │
│  Webview Dispatch:                                                       │
│  ─────────────────                                                       │
│  components/ProjectsSection.tsx:                                         │
│    const dispatch = useDispatch();                                      │
│    dispatch({ type: 'projects.select', payload: { projectRoot } });     │
│    //       ^^^^^^^^^^^^^^^^^^^^^^^^                                    │
│    //       Type-checked at compile time                                │
│                                                                          │
│  Logic Routing (webviews/src/logic/handlers/index.ts):                  │
│  ────────────────────────────────────────────────────                   │
│  export async function handleEvent(logic: UILogic, event: UIEvent) {    │
│    switch (event.type.split('.')[0]) {                                  │
│      case 'builds':                                                     │
│        return handleBuildEvent(logic, event as BuildEvent);             │
│      case 'projects':                                                   │
│        return handleProjectEvent(logic, event as ProjectEvent);         │
│      case 'packages':                                                   │
│        return handlePackageEvent(logic, event as PackageEvent);         │
│      // ... domain-specific handlers                                    │
│    }                                                                     │
│  }                                                                       │
│                                                                          │
│  Extension Bridge Messages:                                              │
│  ──────────────────────────                                              │
│  // Messages that need VS Code APIs go through bridge                   │
│  export type ExtensionMessage =                                          │
│    | { type: 'openFile'; file: string; line?: number }                  │
│    | { type: 'runInTerminal'; command: string }                         │
│    | { type: 'showInputBox'; options: InputBoxOptions }                 │
│    | { type: 'api.build'; targets: string[] }                           │
│    | { type: 'api.installPackage'; packageId: string };                 │
│                                                                          │
│  // UILogic sends bridge messages when VS Code action needed            │
│  logic.bridge.send({ type: 'openFile', file, line });                   │
│                                                                          │
│  State Sync:                                                             │
│  ───────────                                                             │
│  // Instead of full state broadcast, use incremental updates            │
│  export type StateUpdate =                                               │
│    | { type: 'state.full'; data: UIState }                              │
│    | { type: 'state.patch'; path: string[]; value: unknown };           │
│                                                                          │
│  // Extension sends patches for efficiency                              │
│  panel.postMessage({ type: 'state.patch', path: ['builds', id], value });│
│                                                                          │
│  Key Changes:                                                            │
│    - All events typed with discriminated union                          │
│    - Handlers split by domain (builds, projects, packages)              │
│    - Extension bridge for VS Code-specific actions                      │
│    - Incremental state updates instead of full broadcast                │
└─────────────────────────────────────────────────────────────────────────┘

New files:
  - webviews/src/logic/events.ts (UIEvent union)
  - webviews/src/logic/handlers/index.ts (event routing)
  - webviews/src/logic/handlers/builds.ts
  - webviews/src/logic/handlers/projects.ts
  - webviews/src/logic/handlers/packages.ts
  - webviews/src/logic/bridge.ts (ExtensionBridge)
```

---

### Feature 6: Package Explorer

**Purpose**: Browse, search, install, and manage atopile packages via embedded packages.atopile.io.

**Current Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ CURRENT IMPLEMENTATION                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  packagexplorer.ts:                                                      │
│       │                                                                  │
│       ├──▶ createOrShow() opens WebviewPanel                            │
│       │                                                                  │
│       ├──▶ Embeds iframe: https://packages.atopile.io                   │
│       │                                                                  │
│       ├──▶ Message relay (iframe ↔ extension):                          │
│       │      window.onmessage → panel.postMessage                       │
│       │      panel.onDidReceiveMessage → iframe.postMessage             │
│       │                                                                  │
│       └──▶ Command handlers:                                            │
│              case 'install-package':                                    │
│                runAtoCommandInTerminal(`ato add ${package}`);           │
│              case 'upgrade-package':                                    │
│                runAtoCommandInTerminal(`ato add --upgrade ${package}`); │
│              case 'uninstall-package':                                  │
│                runAtoCommandInTerminal(`ato remove ${package}`);        │
│                                                                          │
│  State Sync:                                                             │
│       - Watches ato.yaml files for installed packages                   │
│       - Sends theme/project info to iframe                              │
│       - Receives package actions from iframe                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

Files involved:
  - src/ui/packagexplorer.ts
```

**Proposed Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ PROPOSED IMPLEMENTATION                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Extension Layer:                                                        │
│  ────────────────                                                        │
│  packagexplorer.ts remains similar (iframe embedding is VS Code-specific)│
│  BUT delegates commands to UILogic:                                      │
│                                                                          │
│  case 'install-package':                                                │
│    logic.dispatch({                                                     │
│      type: 'packages.install',                                          │
│      payload: { packageId, projectRoot }                                │
│    });                                                                   │
│    break;                                                                │
│                                                                          │
│  Logic Layer:                                                            │
│  ────────────                                                            │
│  logic/handlers/packages.ts:                                             │
│                                                                          │
│  async function handleInstallPackage(logic: UILogic, event) {           │
│    const { packageId, projectRoot } = event.payload;                    │
│                                                                          │
│    logic.setState(s => ({                                               │
│      ...s,                                                               │
│      packageOperations: new Map(s.packageOperations).set(packageId, {   │
│        status: 'installing',                                             │
│        startedAt: Date.now()                                             │
│      })                                                                   │
│    }));                                                                   │
│                                                                          │
│    try {                                                                 │
│      await logic.bridge.runInTerminal(`ato add ${packageId}`);          │
│      // Refresh installed packages                                       │
│      await handleRefreshPackages(logic);                                │
│    } catch (e) {                                                        │
│      logic.setState(s => addError(s, e.message, 'packages'));           │
│    } finally {                                                           │
│      logic.setState(s => clearPackageOperation(s, packageId));          │
│    }                                                                     │
│                                                                          │
│    logic.telemetry.track('package_add', { packageId });                 │
│  }                                                                       │
│                                                                          │
│  Key Changes:                                                            │
│    - Package operations tracked in state                                │
│    - Loading/error states visible to UI                                 │
│    - Testable without VS Code                                           │
│    - Telemetry in logic layer                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Feature 7: PCB Preview (KiCanvas)

**Purpose**: Display generated .kicad_pcb files using KiCanvas library.

**Current Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ CURRENT IMPLEMENTATION                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  kicanvas.ts:                                                            │
│       │                                                                  │
│       ├──▶ createOrShow() opens WebviewPanel                            │
│       │                                                                  │
│       ├──▶ getPcbPath():                                                │
│       │      1. Get current target from appStateManager                 │
│       │      2. Return computed .kicad_pcb path                         │
│       │                                                                  │
│       ├──▶ Render KiCanvas HTML:                                        │
│       │      <kicanvas-embed src="${pcbFileUri}" controls="...">        │
│       │                                                                  │
│       └──▶ Watch for changes:                                           │
│              appStateManager.onPcbChanged(newPath => {                  │
│                refreshKiCanvas(newPath);                                │
│              });                                                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

Files involved:
  - src/ui/kicanvas.ts
```

**Proposed Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ PROPOSED IMPLEMENTATION                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  This feature is largely VS Code-specific (webview embedding),          │
│  but can benefit from cleaner state subscription:                        │
│                                                                          │
│  kicanvas.ts:                                                            │
│       │                                                                  │
│       └──▶ Subscribe to logic state for PCB path:                       │
│              logic.subscribe(state => {                                 │
│                const pcbPath = selectCurrentPcbPath(state);             │
│                if (pcbPath !== currentPath) {                           │
│                  refreshKiCanvas(pcbPath);                              │
│                }                                                         │
│              });                                                         │
│                                                                          │
│  ViewModels:                                                             │
│  ───────────                                                             │
│  logic/viewmodels/preview.ts:                                            │
│    export function selectCurrentPcbPath(state: UIState): string | null {│
│      const targetId = state.selectedTargetIds.values().next().value;    │
│      if (!targetId) return null;                                        │
│      const target = state.targets.get(targetId);                        │
│      return target?.pcbPath ?? null;                                    │
│    }                                                                     │
│                                                                          │
│  Key Changes:                                                            │
│    - PCB path derived from UIState via selector                         │
│    - No direct appStateManager dependency                               │
│    - Testable selector function                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Feature 8: 3D Model Preview

**Purpose**: Display generated .glb 3D model files using model-viewer.

**Current Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ CURRENT IMPLEMENTATION                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  modelviewer.ts:                                                         │
│       │                                                                  │
│       ├──▶ createOrShow() opens WebviewPanel                            │
│       │                                                                  │
│       ├──▶ getModelPath():                                              │
│       │      1. Get current target from appStateManager                 │
│       │      2. Return computed .glb path                               │
│       │                                                                  │
│       ├──▶ Render model-viewer HTML:                                    │
│       │      <model-viewer src="${modelUri}" camera-controls auto-rotate>│
│       │                                                                  │
│       └──▶ Watch for changes:                                           │
│              appStateManager.on3DModelChanged(newPath => {              │
│                refreshModelViewer(newPath);                             │
│              });                                                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

Files involved:
  - src/ui/modelviewer.ts
```

**Proposed Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ PROPOSED IMPLEMENTATION                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Similar to PCB Preview - subscribe to logic state:                     │
│                                                                          │
│  modelviewer.ts:                                                         │
│       │                                                                  │
│       └──▶ Subscribe to logic state:                                    │
│              logic.subscribe(state => {                                 │
│                const modelPath = selectCurrentModelPath(state);         │
│                if (modelPath !== currentPath) {                         │
│                  refreshModelViewer(modelPath);                         │
│                }                                                         │
│              });                                                         │
│                                                                          │
│  ViewModels:                                                             │
│  ───────────                                                             │
│  logic/viewmodels/preview.ts:                                            │
│    export function selectCurrentModelPath(state: UIState): string | null│
│      const targetId = state.selectedTargetIds.values().next().value;    │
│      if (!targetId) return null;                                        │
│      const target = state.targets.get(targetId);                        │
│      return target?.modelPath ?? null;                                  │
│    }                                                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Feature 9: Atopile Binary Management

**Purpose**: Resolve, install, and manage atopile CLI binary versions.

**Current Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ CURRENT IMPLEMENTATION                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  findbin.ts:                                                             │
│       │                                                                  │
│       ├──▶ findAto(): Promise<string>                                   │
│       │      Resolution priority:                                        │
│       │      1. atopile.ato setting (direct path)                       │
│       │      2. Extension-managed uv + atopile.from version             │
│       │                                                                  │
│       ├──▶ getAtoCommand(): string[]                                    │
│       │      Returns: [uvPath, 'run', '--with', spec, '--python', '3.13']│
│       │                                                                  │
│       └──▶ uvDownloadComplete event triggers LSP restart                │
│                                                                          │
│  setup.ts:                                                               │
│       │                                                                  │
│       ├──▶ setupUv():                                                   │
│       │      1. Check if uv already exists                              │
│       │      2. Download from GitHub releases                           │
│       │      3. Extract to extension storage                            │
│       │      4. Fire uvDownloadComplete event                           │
│       │                                                                  │
│       └──▶ Shows progress notification during download                  │
│                                                                          │
│  vscode-panels.ts (actions):                                             │
│       case 'setAtopileVersion':                                         │
│         await setAtopileVersionSetting(data.version);                   │
│       case 'setAtopileSource':                                          │
│         // Update source (release/branch/local)                         │
│       case 'browseAtopilePath':                                         │
│         // Show file picker                                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

Files involved:
  - src/common/findbin.ts
  - src/ui/setup.ts
  - src/ui/vscode-panels.ts (action handlers)
```

**Proposed Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ PROPOSED IMPLEMENTATION                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  UIState:                                                                │
│  ─────────                                                               │
│  interface AtopileState {                                                │
│    source: 'release' | 'branch' | 'local';                              │
│    version: string | null;         // e.g., "0.3.0"                     │
│    branch: string | null;          // e.g., "main"                      │
│    localPath: string | null;       // e.g., "/path/to/ato"              │
│    availableVersions: string[];                                          │
│    isInstalling: boolean;                                                │
│    installProgress: { message: string; percent?: number } | null;       │
│    error: string | null;                                                │
│    resolvedBinaryPath: string | null;                                   │
│  }                                                                       │
│                                                                          │
│  Events:                                                                 │
│  ─────────                                                               │
│  type AtopileEvent =                                                     │
│    | { type: 'atopile.setSource'; payload: { source: AtopileSource } }  │
│    | { type: 'atopile.setVersion'; payload: { version: string } }       │
│    | { type: 'atopile.setBranch'; payload: { branch: string } }         │
│    | { type: 'atopile.setLocalPath'; payload: { path: string } }        │
│    | { type: 'atopile.browseLocalPath' }                                │
│    | { type: 'atopile.refreshVersions' }                                │
│    | { type: 'atopile.install' };                                       │
│                                                                          │
│  Handlers:                                                               │
│  ──────────                                                              │
│  logic/handlers/atopile.ts:                                              │
│                                                                          │
│  async function handleSetVersion(logic: UILogic, { version }) {         │
│    logic.setState(s => ({                                               │
│      ...s,                                                               │
│      atopile: {                                                          │
│        ...s.atopile,                                                     │
│        version,                                                          │
│        isInstalling: true,                                               │
│        installProgress: { message: 'Installing atopile...' }            │
│      }                                                                   │
│    }));                                                                   │
│                                                                          │
│    try {                                                                 │
│      // Bridge handles VS Code settings update                          │
│      await logic.bridge.updateSetting('atopile.from', version);         │
│      // uv will install on next LSP start                               │
│      await logic.dispatch({ type: 'lsp.restart' });                     │
│    } catch (e) {                                                        │
│      logic.setState(s => ({                                             │
│        ...s,                                                             │
│        atopile: { ...s.atopile, error: e.message }                      │
│      }));                                                                │
│    } finally {                                                           │
│      logic.setState(s => ({                                             │
│        ...s,                                                             │
│        atopile: { ...s.atopile, isInstalling: false }                   │
│      }));                                                                │
│    }                                                                     │
│  }                                                                       │
│                                                                          │
│  Key Changes:                                                            │
│    - Installation state visible in UI                                   │
│    - Progress tracking during install                                   │
│    - Error handling with user feedback                                  │
│    - All settings changes through logic layer                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Feature 10: Example Project Setup

**Purpose**: Download and configure example projects from atopile/atopile repo.

**Current Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ CURRENT IMPLEMENTATION                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  example.ts:                                                             │
│       │                                                                  │
│       ├──▶ listExamples():                                              │
│       │      Fetches directory listing from GitHub API                  │
│       │                                                                  │
│       ├──▶ activateExample():                                           │
│       │      1. showQuickPick() with example names                      │
│       │      2. Download tarball from GitHub                            │
│       │      3. Extract to workspace or temp directory                  │
│       │      4. Open folder if new workspace needed                     │
│       │      5. Reload build targets                                    │
│       │                                                                  │
│       └──▶ Telemetry events:                                            │
│              - vsce:example_list                                         │
│              - vsce:example_start                                        │
│              - vsce:example_complete                                     │
│              - vsce:example_failed                                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

Files involved:
  - src/ui/example.ts
```

**Proposed Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ PROPOSED IMPLEMENTATION                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  UIState:                                                                │
│  ─────────                                                               │
│  interface ExampleState {                                                │
│    availableExamples: Example[];                                         │
│    isLoading: boolean;                                                   │
│    downloadProgress: { example: string; percent: number } | null;       │
│    error: string | null;                                                │
│  }                                                                       │
│                                                                          │
│  Events:                                                                 │
│  ─────────                                                               │
│  type ExampleEvent =                                                     │
│    | { type: 'examples.refresh' }                                       │
│    | { type: 'examples.download'; payload: { exampleName: string } };   │
│                                                                          │
│  Handlers:                                                               │
│  ──────────                                                              │
│  logic/handlers/examples.ts:                                             │
│                                                                          │
│  async function handleRefreshExamples(logic: UILogic) {                 │
│    logic.setState(s => setLoading(s, 'examples', true));                │
│                                                                          │
│    try {                                                                 │
│      const examples = await logic.services.github.listExamples();       │
│      logic.setState(s => ({                                             │
│        ...s,                                                             │
│        examples: { ...s.examples, availableExamples: examples }         │
│      }));                                                                │
│    } catch (e) {                                                        │
│      logic.setState(s => ({                                             │
│        ...s,                                                             │
│        examples: { ...s.examples, error: e.message }                    │
│      }));                                                                │
│    } finally {                                                           │
│      logic.setState(s => setLoading(s, 'examples', false));             │
│    }                                                                     │
│                                                                          │
│    logic.telemetry.track('example_list');                               │
│  }                                                                       │
│                                                                          │
│  async function handleDownloadExample(logic: UILogic, { exampleName }) {│
│    logic.setState(s => ({                                               │
│      ...s,                                                               │
│      examples: {                                                         │
│        ...s.examples,                                                    │
│        downloadProgress: { example: exampleName, percent: 0 }           │
│      }                                                                   │
│    }));                                                                   │
│                                                                          │
│    try {                                                                 │
│      await logic.services.github.downloadExample(exampleName, (pct) => {│
│        logic.setState(s => ({                                           │
│          ...s,                                                           │
│          examples: {                                                     │
│            ...s.examples,                                                │
│            downloadProgress: { example: exampleName, percent: pct }     │
│          }                                                               │
│        }));                                                              │
│      });                                                                 │
│                                                                          │
│      // Bridge opens folder in VS Code                                  │
│      await logic.bridge.openFolder(extractPath);                        │
│      logic.telemetry.track('example_complete', { exampleName });        │
│    } catch (e) {                                                        │
│      logic.setState(s => ({                                             │
│        ...s,                                                             │
│        examples: { ...s.examples, error: e.message }                    │
│      }));                                                                │
│      logic.telemetry.track('example_failed', { exampleName, error: e });│
│    }                                                                     │
│  }                                                                       │
│                                                                          │
│  Key Changes:                                                            │
│    - Download progress visible in UI                                    │
│    - Error states with user feedback                                    │
│    - GitHubService abstracts API calls                                  │
│    - Testable handlers                                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Feature 11: LLM Integration & MCP Server

**Purpose**: Install Claude rules and MCP server for AI-assisted development.

**Current Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ CURRENT IMPLEMENTATION                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  llm.ts:                                                                 │
│       │                                                                  │
│       ├──▶ installClaudeRules():                                        │
│       │      1. Find workspace root                                     │
│       │      2. Create .claude/rules/ directory                         │
│       │      3. Write atopile.md with language docs                     │
│       │                                                                  │
│       ├──▶ installMCPServer():                                          │
│       │      1. Find existing .claude/settings.json                     │
│       │      2. Add atopile MCP server config                           │
│       │      3. Write updated settings                                  │
│       │                                                                  │
│       └──▶ MCP server command:                                          │
│              ato mcp start --no-http                                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

Files involved:
  - src/common/llm.ts
```

**Proposed Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ PROPOSED IMPLEMENTATION                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  UIState:                                                                │
│  ─────────                                                               │
│  interface LLMState {                                                    │
│    claudeRulesInstalled: boolean;                                        │
│    mcpServerInstalled: boolean;                                          │
│    mcpServerRunning: boolean;                                            │
│    error: string | null;                                                │
│  }                                                                       │
│                                                                          │
│  Events:                                                                 │
│  ─────────                                                               │
│  type LLMEvent =                                                         │
│    | { type: 'llm.installClaudeRules' }                                 │
│    | { type: 'llm.installMCPServer' }                                   │
│    | { type: 'llm.checkStatus' };                                       │
│                                                                          │
│  Handlers:                                                               │
│  ──────────                                                              │
│  logic/handlers/llm.ts:                                                  │
│                                                                          │
│  async function handleInstallClaudeRules(logic: UILogic) {              │
│    logic.setState(s => setLoading(s, 'llm', true));                     │
│                                                                          │
│    try {                                                                 │
│      const workspaceRoot = logic.getState().selectedProjectRoot;        │
│      await logic.services.files.ensureDir(`${workspaceRoot}/.claude/rules`);│
│      await logic.services.files.writeFile(                              │
│        `${workspaceRoot}/.claude/rules/atopile.md`,                     │
│        CLAUDE_RULES_CONTENT                                              │
│      );                                                                   │
│      logic.setState(s => ({                                             │
│        ...s,                                                             │
│        llm: { ...s.llm, claudeRulesInstalled: true }                    │
│      }));                                                                │
│    } catch (e) {                                                        │
│      logic.setState(s => ({                                             │
│        ...s,                                                             │
│        llm: { ...s.llm, error: e.message }                              │
│      }));                                                                │
│    } finally {                                                           │
│      logic.setState(s => setLoading(s, 'llm', false));                  │
│    }                                                                     │
│  }                                                                       │
│                                                                          │
│  Key Changes:                                                            │
│    - LLM status visible in UI state                                     │
│    - FileService abstracts file operations                              │
│    - Testable handlers                                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Feature 12: Telemetry & Analytics

**Purpose**: Track usage events for product analytics.

**Current Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ CURRENT IMPLEMENTATION                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  telemetry.ts:                                                           │
│       │                                                                  │
│       ├──▶ initializeTelemetry():                                       │
│       │      - Creates PostHog client                                   │
│       │      - Generates/stores anonymous user ID                       │
│       │                                                                  │
│       ├──▶ emitTelemetry(event: string, properties?: object):           │
│       │      - Checks if telemetry enabled                              │
│       │      - Adds common properties (version, platform)               │
│       │      - Sends to PostHog                                         │
│       │                                                                  │
│       └──▶ Called directly throughout codebase:                         │
│              emitTelemetry('vsce:build_start', { targets });            │
│              emitTelemetry('vsce:part_create');                         │
│              // ... scattered across many files                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

Files involved:
  - src/common/telemetry.ts
  - Called from: buttons.ts, example.ts, vscode-panels.ts, etc.
```

**Proposed Flow**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ PROPOSED IMPLEMENTATION                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  TelemetryService injected into UILogic:                                │
│  ────────────────────────────────────────                               │
│  interface TelemetryService {                                            │
│    track(event: TelemetryEvent, properties?: Record<string, unknown>);  │
│    identify(userId: string, traits?: Record<string, unknown>);          │
│    flush(): Promise<void>;                                               │
│  }                                                                       │
│                                                                          │
│  Typed Events:                                                           │
│  ─────────────                                                           │
│  type TelemetryEvent =                                                   │
│    | 'startup'                                                           │
│    | 'build_start'                                                       │
│    | 'build_complete'                                                    │
│    | 'part_create'                                                       │
│    | 'package_add'                                                       │
│    | 'package_remove'                                                    │
│    | 'project_create'                                                    │
│    | 'example_complete'                                                  │
│    | 'example_failed';                                                   │
│                                                                          │
│  Usage in handlers:                                                      │
│  ──────────────────                                                      │
│  // logic/handlers/builds.ts                                            │
│  async function handleStartBuild(logic: UILogic, event) {               │
│    // ... build logic                                                   │
│    logic.telemetry.track('build_start', {                               │
│      targetCount: event.payload.targets.length                          │
│    });                                                                   │
│  }                                                                       │
│                                                                          │
│  Key Changes:                                                            │
│    - Telemetry calls consolidated in handlers                           │
│    - Typed event names prevent typos                                    │
│    - TelemetryService can be mocked for testing                        │
│    - Single location for analytics logic                                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Proposed Project Structure

This section outlines the recommended directory structure for maintainability and clarity.

### Current Structure (Problems)

```
src/vscode-atopile/
├── src/
│   ├── extension.ts              # Entry point (good)
│   ├── common/                   # Mixed concerns
│   │   ├── appState.ts          # State + WebSocket + business logic
│   │   ├── appState-ws-standalone.ts
│   │   ├── findbin.ts           # Binary resolution
│   │   ├── manifest.ts          # YAML parsing
│   │   ├── server.ts            # LSP management
│   │   ├── target.ts            # Target state singleton
│   │   ├── telemetry.ts         # Analytics
│   │   └── llm.ts               # LLM integration
│   └── ui/
│       ├── buttons.ts           # 13 command handlers (500+ lines)
│       ├── vscode-panels.ts     # Webview + 30 action handlers (800+ lines)
│       ├── setup.ts             # uv installation
│       ├── example.ts           # Example project setup
│       ├── kicanvas.ts          # PCB preview
│       ├── modelviewer.ts       # 3D preview
│       └── packagexplorer.ts    # Package browser
└── webviews/
    └── src/
        ├── sidebar.tsx          # 1100+ lines, mixed concerns
        ├── logViewer.tsx        # Similar issues
        ├── components/          # Presentational components (good)
        └── types/               # Type definitions (good)

Problems:
  ✗ Monolithic files (sidebar.tsx, vscode-panels.ts)
  ✗ Business logic scattered across files
  ✗ No clear separation of concerns
  ✗ Untestable - coupled to React/VS Code
  ✗ No event system
  ✗ State management ad-hoc
```

### Proposed Structure

```
src/vscode-atopile/
├── src/
│   ├── extension.ts                 # Entry point - thin activation
│   │
│   ├── services/                    # VS Code API abstractions
│   │   ├── index.ts                 # Service exports
│   │   ├── files.ts                 # FileService (workspace.findFiles, fs)
│   │   ├── settings.ts              # SettingsService (configuration)
│   │   ├── terminal.ts              # TerminalService (runInTerminal)
│   │   └── dialogs.ts               # DialogService (showInputBox, etc.)
│   │
│   ├── lsp/                         # Language Server (isolated)
│   │   ├── index.ts                 # LspService class
│   │   ├── client.ts                # LanguageClient wrapper
│   │   └── notifications.ts         # LSP notification types
│   │
│   ├── panels/                      # Webview panels (thin wrappers)
│   │   ├── sidebar.ts               # SidebarPanel - message relay
│   │   ├── logViewer.ts             # LogViewerPanel - message relay
│   │   ├── kicanvas.ts              # KiCanvasPanel
│   │   ├── modelviewer.ts           # ModelViewerPanel
│   │   └── packageexplorer.ts       # PackageExplorerPanel
│   │
│   ├── commands/                    # Command registrations (thin)
│   │   ├── index.ts                 # Register all commands
│   │   └── handlers.ts              # Delegates to UILogic
│   │
│   ├── bridge/                      # Extension ↔ Webview bridge
│   │   ├── index.ts                 # ExtensionBridge class
│   │   ├── messages.ts              # Message type definitions
│   │   └── handlers.ts              # Handle messages from webview
│   │
│   └── utils/                       # Pure utilities
│       ├── manifest.ts              # YAML parsing (pure functions)
│       ├── paths.ts                 # Path resolution helpers
│       └── uv.ts                    # uv binary management
│
└── webviews/
    └── src/
        ├── main.tsx                 # Entry point
        ├── App.tsx                  # Router + LogicProvider
        │
        ├── logic/                   # Pure TypeScript logic layer
        │   ├── index.ts             # UILogic class
        │   ├── state.ts             # UIState interface, initialState
        │   ├── events.ts            # UIEvent discriminated union
        │   ├── viewmodels.ts        # ViewModel interfaces + selectors
        │   │
        │   ├── handlers/            # Event handlers by domain
        │   │   ├── index.ts         # Event routing
        │   │   ├── builds.ts        # Build-related handlers
        │   │   ├── projects.ts      # Project/target handlers
        │   │   ├── packages.ts      # Package handlers
        │   │   ├── problems.ts      # Problem handlers
        │   │   ├── logs.ts          # Log viewer handlers
        │   │   ├── atopile.ts       # Atopile version handlers
        │   │   ├── ui.ts            # UI state handlers
        │   │   └── navigation.ts    # File navigation handlers
        │   │
        │   └── api/                 # Extension bridge client
        │       ├── bridge.ts        # ExtensionBridge interface
        │       └── messages.ts      # Message type definitions
        │
        ├── hooks/                   # React bindings
        │   ├── useLogic.tsx         # LogicProvider, useDispatch, useUIState
        │   ├── useProjects.ts       # Project selector hook
        │   ├── useProblems.ts       # Problems selector hook
        │   ├── useBuilds.ts         # Build queue selector hook
        │   └── usePackages.ts       # Packages selector hook
        │
        ├── components/              # React components (presentation)
        │   ├── Sidebar/
        │   │   ├── index.tsx        # ~100 lines, layout shell
        │   │   ├── Header.tsx       # Settings button
        │   │   └── Footer.tsx       # Version info
        │   │
        │   ├── projects/
        │   │   ├── ProjectsSection.tsx
        │   │   ├── ProjectItem.tsx
        │   │   └── TargetItem.tsx
        │   │
        │   ├── builds/
        │   │   ├── BuildQueueSection.tsx
        │   │   ├── BuildItem.tsx
        │   │   └── BuildProgress.tsx
        │   │
        │   ├── problems/
        │   │   ├── ProblemsSection.tsx
        │   │   ├── ProblemItem.tsx
        │   │   └── ProblemFilters.tsx
        │   │
        │   ├── packages/
        │   │   ├── PackagesSection.tsx
        │   │   └── PackageItem.tsx
        │   │
        │   ├── logs/
        │   │   ├── LogViewer.tsx
        │   │   ├── LogEntry.tsx
        │   │   ├── LogFilters.tsx
        │   │   └── StageSelector.tsx
        │   │
        │   └── shared/
        │       ├── CollapsibleSection.tsx
        │       ├── LoadingSpinner.tsx
        │       ├── ErrorBoundary.tsx
        │       └── Icons.tsx
        │
        ├── types/                   # Type definitions
        │   ├── build.ts             # Build, Problem, etc.
        │   ├── project.ts           # Project, Target
        │   └── package.ts           # Package types
        │
        └── __tests__/               # Tests
            ├── logic/
            │   ├── handlers/
            │   │   ├── builds.test.ts
            │   │   ├── projects.test.ts
            │   │   └── ...
            │   └── state.test.ts
            └── hooks/
                └── useProjects.test.ts
```

### Key Structural Principles

1. **Separation of Concerns**
   - `services/` - VS Code API abstractions (testable via mocks)
   - `logic/` - Pure TypeScript business logic (no React/VS Code)
   - `hooks/` - React bindings for logic layer
   - `components/` - Presentation only

2. **Domain-Based Organization**
   - Handlers split by domain (builds, projects, packages)
   - Components organized by feature area
   - Clear ownership of state per domain

3. **Dependency Direction**
   ```
   components → hooks → logic → services
                                    ↓
                              VS Code APIs
   ```

4. **File Size Guidelines**
   - No file should exceed 300 lines
   - Extract when a file has multiple responsibilities
   - One component per file

5. **Testing Strategy**
   - `logic/` layer: Unit tests in Node.js/Bun (fast)
   - `hooks/` layer: React Testing Library
   - `services/` layer: Integration tests with VS Code mocks

6. **Naming Conventions**
   - Event types: `domain.action` (e.g., `builds.start`)
   - Handler functions: `handle{Action}` (e.g., `handleStartBuild`)
   - Selectors: `select{Data}` (e.g., `selectCurrentProject`)
   - Hooks: `use{Data}` (e.g., `useProjects`)

---

## Summary

The orchestrator architecture provides:
- **Clear separation** between UI, logic, and API layers
- **Type-safe events** preventing runtime errors
- **Testable business logic** without React/VS Code
- **Scalable patterns** for adding new features
- **Predictable state flow** via single dispatch

The migration maintains backward compatibility while incrementally adopting the new patterns.
