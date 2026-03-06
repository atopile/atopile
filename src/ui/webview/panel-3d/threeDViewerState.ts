import type { Build } from "../../shared/types";
import { requestBroker } from "../shared/vscodeApi";

export interface ResolvedThreeDModel {
  exists: boolean;
  modelPath: string;
  modelUri: string;
  version: number | null;
}

export function getSelectedThreeDBuild(
  projectRoot: string | null,
  target: string | null,
  currentBuilds: Build[],
  previousBuilds: Build[],
): Build | null {
  if (!projectRoot || !target) {
    return null;
  }

  const match = (candidate: Build) =>
    candidate.projectRoot === projectRoot && candidate.name === target;

  return currentBuilds.find(match) ?? previousBuilds.find(match) ?? null;
}

export async function resolveThreeDModel(
  projectRoot: string,
  target: string,
): Promise<ResolvedThreeDModel> {
  return requestBroker.request<ResolvedThreeDModel>("resolveThreeDModel", {
    projectRoot,
    target,
  });
}
