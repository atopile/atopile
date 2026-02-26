import type { Build, BuildStage } from "../../shared/types";

/** Format seconds into a compact human-readable duration. */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(2)}s`;
  const m = Math.floor(seconds / 60);
  const s = (seconds % 60).toFixed(2);
  return `${m}m ${s}s`;
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

