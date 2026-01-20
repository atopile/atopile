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
    }
}

// Create mock VS Code API
window.acquireVsCodeApi = () => ({
    postMessage: mockPostMessage,
    getState: mockGetState,
    setState: mockSetState,
});

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
