# Agent UI Refactor Plan

## Context

This plan is based on PR `#1732` (`feature/extension-rewrite`), reviewed at commit `023a957aa6b79ed8b8853286a18cdb62c46a5e45`.

That PR establishes the architectural direction we should align with before pushing the agent UI further.

## Principles From PR #1732

### 1. One canonical state model

The rewrite defines shared top-level state in one place and treats it as the canonical contract between layers.

Relevant files:

- `src/ui/shared/types.ts`
- `src/ui/hub/store.ts`

Principle:

- state should be organized into explicit top-level slices
- views subscribe to slices, not to raw events
- state shape should be shared and typed across boundaries

### 2. Hub-centered flow, not component-centered flow

The rewrite routes all webview traffic through the UI hub, which owns subscriptions and action forwarding.

Relevant files:

- `src/EXTENSION_ARCHITECTURE.md`
- `src/ui/hub/webviewWebSocketServer.ts`
- `src/ui/hub/coreWebSocketClient.ts`
- `src/atopile/server/websocket.py`

Principle:

- webviews should not invent their own transport/runtime protocols
- action dispatch and state fanout belong in the hub/core boundary
- the extension host should be thin and mostly lifecycle-oriented

### 3. Shared protocol helpers instead of ad hoc transport logic

The rewrite uses a shared websocket client abstraction and a small message protocol.

Relevant files:

- `src/ui/shared/webSocketClient.ts`
- `src/ui/webview/shared/webviewWebSocketClient.tsx`

Principle:

- reconnect/subscription/protocol handling should be centralized
- feature UIs should not each reimplement their own message transport semantics

### 4. Thin entrypoints, feature-focused views

The rewrite’s webview entrypoints are small; feature components mostly render and dispatch actions.

Relevant files:

- `src/ui/webview/shared/render.tsx`
- `src/ui/webview/sidebar/main.tsx`

Principle:

- top-level feature screens compose smaller panels
- feature state/reduction lives outside the presentational tree
- panels should be replaceable units, not giant stateful applications

### 5. Prefer typed state pushes over DOM event buses

The rewrite uses websocket state slices rather than browser `CustomEvent` fanout as the primary UI update model.

Principle:

- avoid window-global event protocols for feature state
- avoid parsing backend event payloads inside large React components

## Current Agent UI: Where It Conflicts

### 1. `AgentChatPanel.tsx` is a local mini framework

Relevant file:

- [AgentChatPanel.tsx](/home/np/projects/atopile_agent/src/ui-server/src/components/AgentChatPanel.tsx)

Current problems:

- owns transport event parsing
- owns session/run lifecycle
- owns local persistence/snapshots
- owns progress-to-state reduction
- owns trace/checklist/design-question protocol handling
- owns rendering

This is the opposite of the rewrite direction.

### 2. Agent state is not a first-class store slice

Relevant files:

- [store/index.ts](/home/np/projects/atopile_agent/src/ui-server/src/store/index.ts)
- [AgentChatPanel.tsx](/home/np/projects/atopile_agent/src/ui-server/src/components/AgentChatPanel.tsx)

Current problems:

- canonical state lives in component refs/state instead of the shared store
- agent state cannot be reused by another panel/view
- persistence rules are hidden in the component

### 3. Transport is split across HTTP calls and global DOM events

Relevant files:

- [api/agent.ts](/home/np/projects/atopile_agent/src/ui-server/src/api/agent.ts)
- [api/websocket.ts](/home/np/projects/atopile_agent/src/ui-server/src/api/websocket.ts)

Current problems:

- command path is HTTP
- streaming/progress path is websocket event dispatch
- UI consumes `window` events directly
- protocol semantics are implicit and distributed

This will not port cleanly into the new hub/store architecture.

### 4. Agent progress is not modeled as typed state

Relevant files:

- [api/websocket.ts](/home/np/projects/atopile_agent/src/ui-server/src/api/websocket.ts)
- [AgentChatPanel.tsx](/home/np/projects/atopile_agent/src/ui-server/src/components/AgentChatPanel.tsx)

Current problems:

- progress arrives as ad hoc event payloads
- component mutates pending assistant messages based on local interpretation
- there is no central reducer defining the state machine

### 5. The feature boundary is too wide

The agent feature currently spans:

- HTTP client
- websocket custom events
- component-local persistence
- state machine logic
- rendering

That is too many responsibilities for one feature boundary if we want it to fit the extension rewrite.

## Target Architecture For The Agent UI

The agent feature should be reshaped to match PR `#1732` like this:

### 1. Introduce a canonical `agentState` slice

Add a top-level typed slice that contains:

- sessions by project
- active chat id
- runs by id
- messages/transcript state
- checklist state
- trace state
- tool memory
- design question prompts
- transport/connection status

This should become the single source of truth for the UI.

### 2. Move all agent event reduction into one reducer/service

Create a dedicated reducer layer that converts:

- HTTP responses
- progress events
- run status polls if still needed

into `agentState` updates.

The React tree should never parse raw agent progress payloads directly.

### 3. Replace DOM custom-event consumption with store updates

Short term in this branch:

- keep backend event transport if needed
- stop delivering agent state changes straight into `AgentChatPanel`
- instead, map them into store actions

Long term with the rewrite:

- expose agent state through the hub/store websocket model just like other panels

### 4. Split the current chat panel into feature modules

Recommended split:

- `agent/state/types.ts`
- `agent/state/reducer.ts`
- `agent/state/actions.ts`
- `agent/state/persistence.ts`
- `agent/api/client.ts`
- `agent/components/AgentTranscript.tsx`
- `agent/components/AgentComposer.tsx`
- `agent/components/AgentTracePanel.tsx`
- `agent/components/AgentChecklist.tsx`
- `agent/components/AgentQuestions.tsx`
- `agent/AgentChatPanel.tsx` as a thin composition shell

### 5. Keep persistence outside the main component

The current chat snapshot persistence should move into a dedicated persistence module so:

- serialization rules are explicit
- testing is possible without rendering
- future migration to hub-managed persistence is simpler

### 6. Treat the backend protocol as a typed contract

The agent event payloads should get typed frontend models and a reducer contract similar to the shared typed approach in PR `#1732`.

That means:

- one parser/normalizer
- one update path
- one state transition model

not many small interpretations in the UI tree.

## Recommended Implementation Phases

### Phase 1: State extraction

Goal:

- remove feature state management from `AgentChatPanel.tsx`

Work:

- create `agent/state/types.ts`
- create `agent/state/reducer.ts`
- move snapshot persistence into `agent/state/persistence.ts`
- create store actions/selectors for `agentState`

Exit criteria:

- `AgentChatPanel.tsx` no longer contains persistence normalization logic
- `AgentChatPanel.tsx` no longer owns the canonical chat snapshot model

### Phase 2: Transport normalization

Goal:

- centralize agent transport handling

Work:

- create `agent/api/runtime.ts` or similar
- move HTTP request orchestration out of the component
- move progress-event parsing out of the component
- update the store from one place

Exit criteria:

- `AgentChatPanel.tsx` does not subscribe to `window` custom events
- raw backend payload parsing exists in one module only

### Phase 3: Presentational split

Goal:

- break the monolith into render-focused pieces

Work:

- extract transcript
- extract composer
- extract trace display
- extract checklist block
- extract design-questions block

Exit criteria:

- main chat panel is mostly composition and hook wiring

### Phase 4: Align with extension rewrite hub/store model

Goal:

- make the feature portable to the PR `#1732` architecture

Work:

- define a future `agentState` slice in the shared state model
- move action dispatch toward websocket action/state semantics
- minimize feature-specific transport assumptions

Exit criteria:

- the agent feature can be ported into the hub/store architecture with minimal logic rewrite

## Concrete Plan For This Branch

### Step 1

Introduce a new frontend feature folder for agent state and view decomposition without changing backend transport yet.

### Step 2

Move these out of `AgentChatPanel.tsx` first:

- chat snapshot types
- persistence parsing/serialization
- progress payload parsing
- progress-to-message reduction

These are the highest leverage extractions because they are pure logic.

### Step 3

Add an `agentState` slice to the existing Zustand store and make the panel consume selectors instead of local refs as much as possible.

### Step 4

Create a dedicated agent runtime adapter module that wraps:

- `agentApi`
- websocket agent progress handling
- state updates

### Step 5

Split rendering into components only after the state shape is stable.

This avoids moving a lot of JSX around while the state contract is still changing.

## Non-Goals For The First Refactor Pass

- fully porting the current branch to the PR `#1732` folder layout
- changing backend `/api/agent` transport to the new hub protocol immediately
- redesigning the entire visual treatment

The first pass should be about architecture and state boundaries, not cosmetics.

## Success Criteria

The agent UI refactor is successful when:

- the main panel is no longer a stateful mini framework
- agent state is explicit and testable
- event parsing is centralized
- transport semantics are separated from rendering
- the feature shape matches the extension rewrite principles closely enough to port cleanly later
