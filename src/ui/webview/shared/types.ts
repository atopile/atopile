/**
 * Shared TypeScript types matching the Python backend serialization.
 *
 * Core-server types (CamelModel → camelCase keys):
 *   Project, Build, BuildStage
 */

export interface Project {
  root: string;
  name: string;
  displayPath?: string;
  targets: string[];
}

export interface BuildStage {
  name: string;
  stageId?: string;
  displayName?: string;
  elapsedSeconds: number;
  status: string;
  infos?: number;
  warnings?: number;
  errors?: number;
}

export interface Build {
  name: string;
  displayName: string;
  buildId?: string;
  status: string;
  elapsedSeconds: number;
  projectRoot?: string;
  target?: string;
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

export interface ProjectState {
  projects: Project[];
  builds: Build[];
  selected_project: string | null;
  selected_target: string | null;
}