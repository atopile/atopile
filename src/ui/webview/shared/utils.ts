import { useEffect, useState } from 'react';
import AnsiToHtml from 'ansi-to-html';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import type { Build, BuildStage } from "../../shared/generated-types";
import { SOURCE_COLORS, type TimeMode } from "../../shared/types";
import { createWebviewLogger } from './logger';
import { WebviewRpcClient, rpcClient } from './rpcClient';

/** Canonical mapping from status string → Lucide icon component. */
export const STATUS_ICONS: Record<string, LucideIcon> = {
  success: CheckCircle2,
  failed: XCircle,
  error: XCircle,
  warning: AlertTriangle,
  cancelled: AlertCircle,
};

// ANSI to HTML converter
export const ansiConverter = new AnsiToHtml({
  fg: '#e5e5e5',
  bg: 'transparent',
  newline: true,
  escapeXML: true,
});

const logger = createWebviewLogger("WebviewUtils");

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
  if (!Number.isFinite(seconds) || seconds < 0) return "";
  if (seconds < 1) return `${seconds.toFixed(2)}s`;
  if (seconds < 10) return `${seconds.toFixed(1)}s`;
  const total = Math.floor(seconds);
  if (total < 60) return `${total}s`;
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  if (mins < 60) return `${mins}m ${secs}s`;
  const hours = Math.floor(mins / 60);
  return `${hours}h ${mins % 60}m`;
}

/** Format a unix epoch (seconds) into a relative "time ago" string. */
export function formatRelativeSeconds(epochSeconds: number): string {
  if (!Number.isFinite(epochSeconds) || epochSeconds <= 0) return "";
  const diffMs = Date.now() - epochSeconds * 1000;
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return "yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return new Date(epochSeconds * 1000).toLocaleDateString();
}

/** Extract a display counter like "#3" from a build ID. */
export function getBuildCounter(buildId: string | null): string | null {
  if (!buildId) return null;
  const match = buildId.match(/^build-(\d+)-/);
  if (match) return `#${match[1]}`;
  return `#${buildId}`;
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
  const blobAsset = WebviewRpcClient.useSubscribe("blobAsset");
  const [state, setState] = useState({ url: "", error: null as string | null, loading: false });
  const enabled = Boolean(action && payload);
  const requestKey = payload ? JSON.stringify(payload) : "";

  useEffect(() => {
    if (!enabled || !action || !payload) {
      setState({ url: "", error: null, loading: false });
      return;
    }
    logger.info(`useBlobAssetUrl request action=${action} requestKey=${requestKey}`);
    setState({ url: "", error: null, loading: true });
    rpcClient?.sendAction(action, payload);
  }, [action, enabled, requestKey]);

  useEffect(() => {
    if (!enabled || !action) {
      return;
    }
    if (blobAsset.action !== action || blobAsset.requestKey !== requestKey) {
      return;
    }
    logger.info(
      `useBlobAssetUrl response action=${action} requestKey=${requestKey} loading=${String(blobAsset.loading)} contentType=${blobAsset.contentType || "null"} filename=${blobAsset.filename || "null"} error=${blobAsset.error || "null"} data=${blobAsset.data ? "present" : "missing"}`,
    );
    if (blobAsset.loading) {
      setState({ url: "", error: null, loading: true });
      return;
    }
    if (blobAsset.error || !blobAsset.data) {
      setState({
        url: "",
        error: blobAsset.error || "Failed to load asset",
        loading: false,
      });
      return;
    }

    const bytes = decodeBase64(blobAsset.data);
    const buffer = new ArrayBuffer(bytes.byteLength);
    new Uint8Array(buffer).set(bytes);
    const blob = new Blob([buffer], {
      type: blobAsset.contentType || "application/octet-stream",
    });
    const url = URL.createObjectURL(blob);
    logger.info(
      `useBlobAssetUrl created object URL action=${action} requestKey=${requestKey} bytes=${String(bytes.byteLength)}`,
    );
    setState({ url, error: null, loading: false });
    return () => {
      URL.revokeObjectURL(url);
    };
  }, [action, blobAsset, enabled, requestKey]);

  return state;
}
