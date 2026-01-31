/**
 * Vitest test setup file
 * Configures testing environment for React components
 */

import '@testing-library/jest-dom';
import { vi, afterEach } from 'vitest';

// Mock ResizeObserver (not available in jsdom)
class MockResizeObserver {
    callback: ResizeObserverCallback;
    constructor(callback: ResizeObserverCallback) {
        this.callback = callback;
    }
    observe() {}
    unobserve() {}
    disconnect() {}
}

global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

// Mock the VS Code webview API
const mockPostMessage = vi.fn();
const mockGetState = vi.fn(() => undefined);
const mockSetState = vi.fn();

declare global {
    interface Window {
        acquireVsCodeApi: () => {
            postMessage: typeof mockPostMessage;
            getState: typeof mockGetState;
            setState: typeof mockSetState;
        };
        __ATOPILE_API_URL__?: string;
        __ATOPILE_WS_URL__?: string;
    }
}

// Create mock VS Code API
window.acquireVsCodeApi = () => ({
    postMessage: mockPostMessage,
    getState: mockGetState,
    setState: mockSetState,
});

window.__ATOPILE_API_URL__ = window.__ATOPILE_API_URL__ || 'http://127.0.0.1';
window.__ATOPILE_WS_URL__ = window.__ATOPILE_WS_URL__ || 'ws://127.0.0.1';

// Export mocks for test access
export const vscodeApiMocks = {
    postMessage: mockPostMessage,
    getState: mockGetState,
    setState: mockSetState,
    reset: () => {
        mockPostMessage.mockClear();
        mockGetState.mockClear();
        mockSetState.mockClear();
    },
};

// Clean up after each test
afterEach(() => {
    vscodeApiMocks.reset();
});
