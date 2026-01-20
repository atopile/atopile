# Architecture Comparison: Orchestrator vs VS Code Extension

This document analyzes the orchestrator architecture from `tools/orchestrator/` and compares it to the current VS Code extension implementation in `src/vscode-atopile/`. It provides a plan for re-architecting the extension to follow the orchestrator's clean separation of concerns.

## Table of Contents
1. [Orchestrator Architecture Summary](#1-orchestrator-architecture-summary)
2. [Current Extension Architecture Summary](#2-current-extension-architecture-summary)
3. [Key Architectural Differences](#3-key-architectural-differences)
4. [10 Orchestrator Data Flow Examples](#4-10-orchestrator-data-flow-examples)
5. [10 Extension Examples (Current vs Proposed)](#5-10-extension-examples-current-vs-proposed)
6. [Re-Architecture Plan](#6-re-architecture-plan)

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

## Summary

The orchestrator architecture provides:
- **Clear separation** between UI, logic, and API layers
- **Type-safe events** preventing runtime errors
- **Testable business logic** without React/VS Code
- **Scalable patterns** for adding new features
- **Predictable state flow** via single dispatch

The migration maintains backward compatibility while incrementally adopting the new patterns.
