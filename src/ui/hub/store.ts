/**
 * Reactive state store for the hub.
 *
 * Module-level singleton — import `store` directly wherever needed.
 * Notifies listeners when a top-level key changes (deep-equality via JSON).
 */

import { StoreState } from "../shared/types";

export type OnChangeCallback = (key: string, value: unknown, prev: unknown) => void;

export class Store {
  private _state = new StoreState();
  onChange: OnChangeCallback | null = null;

  get<K extends keyof StoreState>(key: K): StoreState[K] {
    return this._state[key];
  }

  /** Fully replace a top-level state key. */
  set<K extends keyof StoreState>(key: K, value: StoreState[K]): void {
    const oldValue = this._state[key];
    if (JSON.stringify(oldValue) === JSON.stringify(value)) return;
    this._state[key] = value;
    this.onChange?.(key, value, oldValue);
  }

  /**
   * Shallow-merge into a top-level state slice (e.g. "coreStatus", "projectState").
   * Only the provided fields are updated; existing fields are preserved.
   */
  merge<K extends keyof StoreState>(key: K, partial: Partial<StoreState[K]>): void {
    const oldValue = this._state[key];
    const value = { ...oldValue, ...partial } as StoreState[K];
    if (JSON.stringify(oldValue) === JSON.stringify(value)) return;

    this._state[key] = value;
    this.onChange?.(key, value, oldValue);
  }

  /** Reset a key back to its default value. */
  clear<K extends keyof StoreState>(key: K): void {
    this.set(key, new StoreState()[key]);
  }
}
