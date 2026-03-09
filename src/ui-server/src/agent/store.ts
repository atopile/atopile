import { DEFAULT_AGENT_STATE, type AgentChatSnapshot, type AgentState } from './state/types';

export interface AgentStoreState {
  agentState: AgentState;
}

export interface AgentStoreActions {
  hydrateAgentState: (payload: Partial<AgentState>) => void;
  setAgentSnapshots: (snapshots: AgentChatSnapshot[]) => void;
  upsertAgentSnapshot: (snapshot: AgentChatSnapshot) => void;
  updateAgentSnapshot: (
    chatId: string,
    updater: (chat: AgentChatSnapshot) => AgentChatSnapshot,
  ) => void;
  setAgentActiveChat: (projectRoot: string, chatId: string | null) => void;
}

type StoreSetter<T> = (partial: Partial<T> | ((state: T) => Partial<T>), replace?: false) => void;

const mergeAgentState = <T extends AgentStoreState>(
  state: T,
  update: Partial<AgentState>,
): Partial<T> =>
  ({
    agentState: {
      ...state.agentState,
      ...update,
    },
  }) as Partial<T>;

export const agentInitialState: AgentStoreState = {
  agentState: DEFAULT_AGENT_STATE,
};

export const createAgentStoreActions = <T extends AgentStoreState>(
  set: StoreSetter<T>,
): AgentStoreActions => ({
  hydrateAgentState: (payload) =>
    set((state) => mergeAgentState(state, payload)),

  setAgentSnapshots: (snapshots) =>
    set((state) => mergeAgentState(state, { snapshots })),

  upsertAgentSnapshot: (snapshot) =>
    set((state) => {
      const previous = state.agentState.snapshots;
      const index = previous.findIndex((chat) => chat.id === snapshot.id);
      if (index < 0) {
        return mergeAgentState(state, { snapshots: [snapshot, ...previous] });
      }
      const next = [...previous];
      next[index] = {
        ...previous[index],
        ...snapshot,
        createdAt: previous[index].createdAt,
      };
      return mergeAgentState(state, { snapshots: next });
    }),

  updateAgentSnapshot: (chatId, updater) =>
    set((state) => {
      const previous = state.agentState.snapshots;
      const index = previous.findIndex((chat) => chat.id === chatId);
      if (index < 0) return {} as Partial<T>;
      const current = previous[index];
      const updated = updater(current);
      const next = [...previous];
      next[index] = {
        ...updated,
        createdAt: current.createdAt,
        updatedAt: Date.now(),
      };
      return mergeAgentState(state, { snapshots: next });
    }),

  setAgentActiveChat: (projectRoot, chatId) =>
    set((state) => {
      const next = { ...state.agentState.activeChatByProject };
      if (chatId) {
        next[projectRoot] = chatId;
      } else {
        delete next[projectRoot];
      }
      return mergeAgentState(state, { activeChatByProject: next });
    }),
});
