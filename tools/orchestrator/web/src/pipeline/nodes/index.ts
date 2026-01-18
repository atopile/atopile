export { AgentNode } from './AgentNode';
export { TriggerNode } from './TriggerNode';
export { LoopNode } from './LoopNode';
export { ConditionNode } from './ConditionNode';

import type { NodeTypes } from '@xyflow/react';
import { AgentNode } from './AgentNode';
import { TriggerNode } from './TriggerNode';
import { LoopNode } from './LoopNode';
import { ConditionNode } from './ConditionNode';

// Cast to NodeTypes to satisfy React Flow's type requirements
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const nodeTypes: NodeTypes = {
  agent: AgentNode as any,
  trigger: TriggerNode as any,
  loop: LoopNode as any,
  condition: ConditionNode as any,
};
