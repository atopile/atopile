import { useEffect, useState } from 'react';
import AnsiToHtml from 'ansi-to-html';
import type { Build, BuildStage } from "../../shared/generated-types";
import { SOURCE_COLORS, type TimeMode } from "../../shared/types";
import { rpcClient } from './rpcClient';

// ANSI to HTML converter
export const ansiConverter = new AnsiToHtml({
  fg: '#e5e5e5',
  bg: 'transparent',
  newline: true,
  escapeXML: true,
});

/** Hash a string to a deterministic color from SOURCE_COLORS. */
export function hashStringToColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash = hash & hash;
  }
  return SOURCE_COLORS[Math.abs(hash) % SOURCE_COLORS.length];
}

/** Format an ISO timestamp as wall-clock time or delta from a reference. */
export function formatTimestamp(ts: string, mode: TimeMode, firstTimestamp: number): string {
  if (mode === 'wall') {
    const timePart = ts.split('T')[1];
    if (!timePart) return ts;
    return timePart.split('.')[0];
  }
  const logTime = new Date(ts).getTime();
  const delta = logTime - firstTimestamp;
  if (delta < 1000) return `+${delta}ms`;
  if (delta < 60000) return `+${(delta / 1000).toFixed(1)}s`;
  return `+${(delta / 60000).toFixed(1)}m`;
}

/** Format a file path and optional line number as "filename:line". */
export function formatSource(file: string | null | undefined, line: number | null | undefined): string | null {
  if (!file) return null;
  const filename = file.split('/').pop() || file;
  return line ? `${filename}:${line}` : filename;
}

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

interface AssetResponse {
  contentType: string;
  filename: string;
  data: string;
}

function decodeBase64(base64: string): Uint8Array {
  const binary = window.atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

export function useBlobAssetUrl(
  action: string | null,
  payload: Record<string, unknown> | null,
): { url: string; error: string | null; loading: boolean } {
  const [state, setState] = useState({ url: "", error: null as string | null, loading: false });

  useEffect(() => {
    if (!action || !payload) {
      setState({ url: "", error: null, loading: false });
      return;
    }

    let revokedUrl = "";
    let cancelled = false;
    setState({ url: "", error: null, loading: true });

    void rpcClient?.requestAction<AssetResponse>(action, payload)
      .then((result) => {
        if (cancelled || !result?.data) {
          return;
        }
        const bytes = decodeBase64(result.data);
        const buffer = new ArrayBuffer(bytes.byteLength);
        new Uint8Array(buffer).set(bytes);
        const blob = new Blob([buffer], {
          type: result.contentType || "application/octet-stream",
        });
        revokedUrl = URL.createObjectURL(blob);
        setState({ url: revokedUrl, error: null, loading: false });
      })
      .catch((error) => {
        if (!cancelled) {
          setState({
            url: "",
            error: error instanceof Error ? error.message : String(error),
            loading: false,
          });
        }
      });

    return () => {
      cancelled = true;
      if (revokedUrl) {
        URL.revokeObjectURL(revokedUrl);
      }
    };
  }, [action, payload ? JSON.stringify(payload) : ""]);

  return state;
}
