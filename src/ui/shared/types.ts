/**
 * Canonical shared types for the atopile UI.
 *
 * Imported by both the hub (Node process) and webview (React) code.
 */

export class StoreState {
  hubStatus = new HubStatus();
  coreStatus = new CoreStatus();
  projectState = new ProjectState();
  latestBuilds: Build[] = [];
  previousBuilds: Build[] = [];
}

export class HubStatus {
  connected: boolean = false;
}

export class CoreStatus {
  connected: boolean = false;
}

export class ProjectState {
  projects: Project[] = [];
  selectedProject: string | null = null;
  selectedTarget: string | null = null;
}

export class Project {
  root: string = "";
  name: string = "";
  targets: string[] = [];
}

export class BuildStage {
  name: string = "";
  stageId?: string;
  elapsedSeconds: number = 0;
  status: string = "";
  infos?: number;
  warnings?: number;
  errors?: number;
}

export class Build {
  name: string = "";
  buildId?: string;
  status: string = "";
  elapsedSeconds: number = 0;
  projectRoot?: string;
  entry?: string;
  startedAt?: number;
  stages?: BuildStage[];
  currentStage?: BuildStage | null;
  totalStages?: number | null;
  warnings?: number;
  errors?: number;
  error?: string;
  returnCode?: number | null;
}

// -- WebSocket protocol messages -------------------------------------------

export const MSG_TYPE = {
  SUBSCRIBE: "subscribe",
  STATE: "state",
  ACTION: "action",
} as const;

export interface SubscribeMessage {
  type: typeof MSG_TYPE.SUBSCRIBE;
  keys: string[];
}

export interface StateMessage {
  type: typeof MSG_TYPE.STATE;
  key: string;
  data: unknown;
}

export interface ActionMessage {
  type: typeof MSG_TYPE.ACTION;
  action: string;
  [key: string]: unknown;
}

export type WebSocketMessage = SubscribeMessage | StateMessage | ActionMessage;
