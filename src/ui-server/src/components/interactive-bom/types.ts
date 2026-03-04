export interface BomGroup {
  id: string;
  footprintName: string;
  value: string | null;
  package: string;
  designators: string[];
  quantity: number;
  footprintIndices: number[];
}

export interface BomEnrichment {
  mpn: string | null;
  manufacturer: string | null;
  lcsc: string | null;
  type: string | null;
  picked: 'manual' | 'auto' | null;
  unitCost: number | null;
  stock: number | null;
}
