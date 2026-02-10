export interface SchematicBOMParameter {
  name: string;
  value: string;
  unit?: string | null;
}

export interface SchematicBOMUsage {
  address: string;
  designator: string;
}

export interface SchematicBOMComponent {
  id: string;
  lcsc?: string | null;
  manufacturer?: string | null;
  mpn?: string | null;
  type?: string;
  value?: string | null;
  package?: string | null;
  description?: string | null;
  quantity?: number;
  unitCost?: number | null;
  stock?: number | null;
  source?: string | null;
  parameters?: SchematicBOMParameter[];
  usages?: SchematicBOMUsage[];
}

export interface SchematicBOMData {
  version?: string;
  build_id?: string;
  components?: SchematicBOMComponent[];
}

export interface SchematicVariable {
  name: string;
  spec?: string | null;
  specTolerance?: string | null;
  actual?: string | null;
  actualTolerance?: string | null;
  unit?: string | null;
  type?: string;
  meetsSpec?: boolean | null;
  source?: string | null;
}

export interface SchematicVariableNode {
  name: string;
  path: string;
  type?: 'module' | 'interface' | 'component';
  typeName?: string | null;
  variables?: SchematicVariable[];
  children?: SchematicVariableNode[];
}

export interface SchematicVariablesData {
  version?: string;
  build_id?: string;
  nodes?: SchematicVariableNode[];
}
