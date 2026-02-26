import type { Build, BuildStage } from "../../shared/types";

/** Format seconds into a compact human-readable duration. */
export function formatDuration(seconds: number): string {
  if (seconds < 1) return "<1s";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

/** Format a unix timestamp into a relative "time ago" string. */
export function formatTimeAgo(unixSeconds: number): string {
  const diff = Math.floor(Date.now() / 1000 - unixSeconds);
  if (diff < 5) return "just now";
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

/** Get the running stage, or the last completed one. */
export function getCurrentStage(build: Build): BuildStage | null {
  const stages = build.stages;
  if (!stages?.length) return null;
  const running = stages.find((s) => s.status === "running");
  if (running) return running;
  const completed = stages.filter(
    (s) => s.status !== "pending" && s.status !== "skipped",
  );
  return completed.length > 0 ? completed[completed.length - 1] : null;
}

/** Return the latest build per target for a given project root. */
export function getLatestPerTarget(
  builds: Build[],
  projectRoot: string | null,
): Build[] {
  if (!projectRoot) return [];
  const seen = new Map<string, Build>();
  for (const b of builds) {
    if (b.projectRoot !== projectRoot) continue;
    const target = b.name ?? "";
    const existing = seen.get(target);
    if (!existing || (b.startedAt ?? 0) > (existing.startedAt ?? 0)) {
      seen.set(target, b);
    }
  }
  return Array.from(seen.values()).map((b) => ({
    ...b,
    currentStage: getCurrentStage(b),
  }));
}