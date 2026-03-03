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
  description: string | null;
}
