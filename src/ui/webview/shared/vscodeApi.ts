/**
 * Shared VS Code API instance.
 *
 * acquireVsCodeApi() can only be called once per webview.
 * Import `getVscodeApi` from this module instead of calling it directly.
 */
declare const acquireVsCodeApi:
  | undefined
  | (() => {
      postMessage(message: unknown): void;
    });

type VscodeApi = {
  postMessage(message: unknown): void;
};

let cachedVscodeApi: VscodeApi | null | undefined;

export function getVscodeApi(): VscodeApi | null {
  if (cachedVscodeApi !== undefined) {
    return cachedVscodeApi;
  }

  cachedVscodeApi =
    typeof acquireVsCodeApi === "function" ? acquireVsCodeApi() : null;
  return cachedVscodeApi;
}
