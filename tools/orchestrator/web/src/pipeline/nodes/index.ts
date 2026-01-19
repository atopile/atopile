export { AgentNode } from './AgentNode';
export { TriggerNode } from './TriggerNode';
export { ConditionNode } from './ConditionNode';
export { WaitNode } from './WaitNode';

import type { NodeTypes } from '@xyflow/react';
import { AgentNode } from './AgentNode';
import { TriggerNode } from './TriggerNode';
import { ConditionNode } from './ConditionNode';
import { WaitNode } from './WaitNode';

// Cast to NodeTypes to satisfy React Flow's type requirements
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const nodeTypes: NodeTypes = {
  agent: AgentNode as any,
  trigger: TriggerNode as any,
  condition: ConditionNode as any,
  wait: WaitNode as any,
};
