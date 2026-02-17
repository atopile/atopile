/**
 * Safe localStorage helpers for sandboxed/third-party iframe contexts where
 * storage access may throw SecurityError.
 */

function getLocalStorage(): Storage | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function safeLocalStorageGetItem(key: string): string | null {
  const storage = getLocalStorage();
  if (!storage) return null;
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

export function safeLocalStorageSetItem(key: string, value: string): void {
  const storage = getLocalStorage();
  if (!storage) return;
  try {
    storage.setItem(key, value);
  } catch {
    // Ignore storage failures in restricted iframe contexts.
  }
}

export function safeLocalStorageRemoveItem(key: string): void {
  const storage = getLocalStorage();
  if (!storage) return;
  try {
    storage.removeItem(key);
  } catch {
    // Ignore storage failures in restricted iframe contexts.
  }
}
