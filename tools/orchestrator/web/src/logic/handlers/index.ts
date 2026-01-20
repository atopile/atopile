/**
 * Event handler dispatcher
 */

import type { UILogic } from '../index';
import type { UIEvent } from '../events';
import { clearError, clearAllErrors } from '../state';
import { handleAgentEvent } from './agents';
import { handleOutputEvent } from './output';
import { handlePipelineEvent, handleSessionEvent, handleEditorEvent } from './pipelines';

/**
 * Main event handler - dispatches to appropriate domain handler
 */
export async function handleEvent(logic: UILogic, event: UIEvent): Promise<void> {
  // Route to appropriate handler based on event type prefix
  if (event.type.startsWith('agents.')) {
    await handleAgentEvent(logic, event as Extract<UIEvent, { type: `agents.${string}` }>);
  } else if (event.type.startsWith('output.')) {
    await handleOutputEvent(logic, event as Extract<UIEvent, { type: `output.${string}` }>);
  } else if (event.type.startsWith('pipelines.')) {
    await handlePipelineEvent(logic, event as Extract<UIEvent, { type: `pipelines.${string}` }>);
  } else if (event.type.startsWith('sessions.')) {
    await handleSessionEvent(logic, event as Extract<UIEvent, { type: `sessions.${string}` }>);
  } else if (event.type.startsWith('editor.')) {
    handleEditorEvent(logic, event as Extract<UIEvent, { type: `editor.${string}` }>);
  } else if (event.type.startsWith('ui.')) {
    handleUIEvent(logic, event as Extract<UIEvent, { type: `ui.${string}` }>);
  } else if (event.type.startsWith('dialog.')) {
    handleDialogEvent(logic, event as Extract<UIEvent, { type: `dialog.${string}` }>);
  } else if (event.type.startsWith('error.')) {
    handleErrorEvent(logic, event as Extract<UIEvent, { type: `error.${string}` }>);
  }
}

// UI event handlers
function handleUIEvent(
  logic: UILogic,
  event: Extract<UIEvent, { type: `ui.${string}` }>
): void {
  switch (event.type) {
    case 'ui.navigate':
      logic.setState((s) => ({
        ...s,
        currentPage: event.payload.page,
      }));
      break;
    case 'ui.toggleVerbose':
      logic.setState((s) => ({
        ...s,
        verbose: event.payload.value,
      }));
      break;
  }
}

// Dialog event handlers
function handleDialogEvent(
  logic: UILogic,
  event: Extract<UIEvent, { type: `dialog.${string}` }>
): void {
  switch (event.type) {
    case 'dialog.open':
      logic.setState((s) => ({
        ...s,
        dialogs: {
          ...s.dialogs,
          [event.payload.dialog]: { open: true, data: event.payload.data },
        },
      }));
      break;
    case 'dialog.close':
      logic.setState((s) => ({
        ...s,
        dialogs: {
          ...s.dialogs,
          [event.payload.dialog]: { open: false },
        },
      }));
      break;
  }
}

// Error event handlers
function handleErrorEvent(
  logic: UILogic,
  event: Extract<UIEvent, { type: `error.${string}` }>
): void {
  switch (event.type) {
    case 'error.clear':
      logic.setState((s) => clearError(s, event.payload.errorId));
      break;
    case 'error.clearAll':
      logic.setState((s) => clearAllErrors(s));
      break;
  }
}

export { handleAgentEvent } from './agents';
export { handleOutputEvent } from './output';
export { handlePipelineEvent, handleSessionEvent, handleEditorEvent } from './pipelines';
