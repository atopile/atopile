type JsonPrimitive = string | number | boolean | null;
type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
type EventProps = Record<string, JsonValue>;

type PostHogLike = {
  init?: (apiKey: string, options: Record<string, unknown>) => void;
  identify?: (distinctId: string) => void;
  capture?: (event: string, properties?: EventProps) => void;
};

declare global {
  interface Window {
    posthog?: PostHogLike;
  }
}

const POSTHOG_KEY = "phc_IIl9Bip0fvyIzQFaOAubMYYM2aNZcn26Y784HcTeMVt";
const POSTHOG_HOST = "https://telemetry.atopileapi.com";
const POSTHOG_SCRIPT = `${POSTHOG_HOST}/static/array.js`;
const POSTHOG_SCRIPT_ID = "atopile-posthog-js";
const DISTINCT_ID_KEY = "atopile_playground_distinct_id";

let initialized = false;
let loadPromise: Promise<void> | null = null;
let clientReady = false;
const pendingEvents: Array<{ event: string; properties: EventProps }> = [];

function randomId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getDistinctId(): string {
  try {
    const existing = window.localStorage.getItem(DISTINCT_ID_KEY);
    if (existing) return existing;
    const generated = randomId();
    window.localStorage.setItem(DISTINCT_ID_KEY, generated);
    return generated;
  } catch {
    return randomId();
  }
}

function shouldSkipTelemetry(): boolean {
  if (navigator.doNotTrack === "1") {
    return true;
  }
  const params = new URLSearchParams(window.location.search);
  return params.get("telemetry") === "0";
}

function ensurePosthogScript(): Promise<void> {
  if (loadPromise) {
    return loadPromise;
  }

  loadPromise = new Promise<void>((resolve, reject) => {
    const existing = document.getElementById(POSTHOG_SCRIPT_ID) as HTMLScriptElement | null;
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("PostHog script failed to load")), {
        once: true,
      });
      return;
    }

    const script = document.createElement("script");
    script.id = POSTHOG_SCRIPT_ID;
    script.async = true;
    script.crossOrigin = "anonymous";
    script.src = POSTHOG_SCRIPT;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("PostHog script failed to load"));
    document.head.appendChild(script);
  });

  return loadPromise;
}

function flushPendingEvents(): void {
  if (!clientReady || !window.posthog?.capture) return;
  while (pendingEvents.length > 0) {
    const item = pendingEvents.shift();
    if (!item) return;
    window.posthog.capture(item.event, item.properties);
  }
}

export function captureEvent(event: string, properties: EventProps = {}): void {
  const eventName = `playground_${event}`;
  if (clientReady && window.posthog?.capture) {
    window.posthog.capture(eventName, properties);
    return;
  }
  pendingEvents.push({ event: eventName, properties });
}

export async function initAnalytics(page: "landing" | "dashboard"): Promise<void> {
  if (initialized || shouldSkipTelemetry()) {
    return;
  }
  initialized = true;

  try {
    await ensurePosthogScript();
    const posthog = window.posthog;
    if (!posthog || typeof posthog.init !== "function") {
      return;
    }

    posthog.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      autocapture: false,
      capture_pageview: false,
      persistence: "localStorage+cookie",
    });

    const distinctId = getDistinctId();
    if (typeof posthog.identify === "function") {
      posthog.identify(distinctId);
    }

    clientReady = true;
    flushPendingEvents();
    captureEvent("page_view", {
      page,
      path: window.location.pathname,
      query: window.location.search,
    });
  } catch {
    // Analytics must never affect UX.
  }
}

