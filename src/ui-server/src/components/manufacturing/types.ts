/**
 * TypeScript types for the Manufacturing Export Wizard.
 */

export type ManufacturingBuildStatus = 'pending' | 'building' | 'ready' | 'confirmed' | 'failed';

export interface ManufacturingBuild {
  projectRoot: string;
  targetName: string;
  status: ManufacturingBuildStatus;
  buildId: string | null;
  error: string | null;
}

export interface CostEstimate {
  pcbCost: number;
  componentsCost: number;
  assemblyCost: number;
  totalCost: number;
  currency: string;
  quantity: number;
  // Breakdown details
  pcbBreakdown?: {
    baseCost: number;
    areaCost: number;
    layerCost: number;
  };
  componentsBreakdown?: {
    uniqueParts: number;
    totalParts: number;
  };
  assemblyBreakdown?: {
    baseCost: number;
    perPartCost: number;
  };
}

// =============================================================================
// JLCPCB Detailed Cost Estimation Types
// =============================================================================

export interface BoardDimensions {
  widthMm: number;
  heightMm: number;
  areaMm2: number;
  areaCm2: number;
  isSmallBoard: boolean;
  isLargeBoard: boolean;
}

export interface AssemblySides {
  topCount: number;
  bottomCount: number;
  isDoubleSided: boolean;
  totalComponents: number;
}

export interface PartsCategorization {
  basicCount: number;
  preferredCount: number;
  extendedCount: number;
  unknownCount: number;
  totalUniqueParts: number;
  partsWithLoadingFee: number;
}

export interface BoardSummary {
  dimensions: BoardDimensions | null;
  layerCount: number;
  copperLayers: string[];
  totalThicknessMm: number | null;
  copperFinish: string | null;
  assembly: AssemblySides;
  parts: PartsCategorization;
  estimatedSolderJoints: number;
}

export interface DetailedPCBBreakdown {
  baseCost: number;
  layerCost: number;
  sizeCost: number;
  total: number;
}

export interface DetailedAssemblyBreakdown {
  setupFee: number;
  stencilFee: number;
  solderJointsCost: number;
  loadingFees: number;
  loadingFeePartsCount: number;
  total: number;
}

export interface DetailedComponentsBreakdown {
  total: number;
  uniqueParts: number;
  totalParts: number;
}

export interface DetailedCostEstimate {
  pcbCost: number;
  componentsCost: number;
  assemblyCost: number;
  totalCost: number;
  currency: string;
  quantity: number;
  assemblyType: 'economic' | 'standard';
  pcbBreakdown: DetailedPCBBreakdown;
  componentsBreakdown: DetailedComponentsBreakdown;
  assemblyBreakdown: DetailedAssemblyBreakdown;
  boardSummary: BoardSummary | null;
}

export type FileExportType =
  | 'gerbers'
  | 'bom_csv'
  | 'bom_json'
  | 'pick_and_place'
  | 'step'
  | 'glb'
  | 'kicad_pcb'
  | 'kicad_sch'
  | 'svg'
  | 'dxf'
  | 'png'
  | 'testpoints'
  | 'variables_report'
  | 'datasheets';

export interface FileExportOption {
  type: FileExportType;
  label: string;
  description: string;
  extension: string;
  available: boolean;
}

export interface BuildOutputs {
  gerbers: string | null;
  bomJson: string | null;
  bomCsv: string | null;
  pickAndPlace: string | null;
  step: string | null;
  glb: string | null;
  kicadPcb: string | null;
  kicadSch: string | null;
  pcbSummary: string | null;
  svg: string | null;
  dxf: string | null;
  png: string | null;
  testpoints: string | null;
  variablesReport: string | null;
  powerTree: string | null;
  datasheets: string[];
  fileSizes?: Record<string, number>;
}

export interface GitStatus {
  hasUncommittedChanges: boolean;
  changedFiles: string[];
}

export interface ManufacturingWizardState {
  isOpen: boolean;
  currentStep: 1 | 2 | 3;
  selectedBuilds: ManufacturingBuild[];
  hasUncommittedChanges: boolean;
  uncommittedWarningDismissed: boolean;
  changedFiles: string[];
  exportDirectory: string;
  selectedFileTypes: FileExportType[];
  costEstimate: CostEstimate | null;
  quantity: number;
  isLoadingGitStatus: boolean;
  isLoadingCost: boolean;
  isExporting: boolean;
  exportError: string | null;
}

export const DEFAULT_FILE_TYPES: FileExportType[] = [
  'gerbers',
  'bom_csv',
  'pick_and_place',
];

export const FILE_EXPORT_OPTIONS: FileExportOption[] = [
  {
    type: 'gerbers',
    label: 'Gerbers',
    description: 'PCB manufacturing files (Gerber RS-274X)',
    extension: '.zip',
    available: true,
  },
  {
    type: 'bom_csv',
    label: 'BOM (CSV)',
    description: 'Bill of materials spreadsheet',
    extension: '.csv',
    available: true,
  },
  {
    type: 'bom_json',
    label: 'BOM (JSON)',
    description: 'Bill of materials data',
    extension: '.json',
    available: true,
  },
  {
    type: 'pick_and_place',
    label: 'Pick & Place',
    description: 'Component placement file for assembly',
    extension: '.csv',
    available: true,
  },
  {
    type: 'step',
    label: '3D Model (STEP)',
    description: 'CAD-compatible 3D model',
    extension: '.step',
    available: true,
  },
  {
    type: 'glb',
    label: '3D Model (GLB)',
    description: 'Web-compatible 3D model',
    extension: '.glb',
    available: true,
  },
  {
    type: 'kicad_pcb',
    label: 'KiCad PCB',
    description: 'KiCad PCB layout file',
    extension: '.kicad_pcb',
    available: true,
  },
  {
    type: 'kicad_sch',
    label: 'KiCad Schematic',
    description: 'KiCad schematic file',
    extension: '.kicad_sch',
    available: true,
  },
  {
    type: 'svg',
    label: 'PCB Render (SVG)',
    description: 'Vector PCB render',
    extension: '.svg',
    available: true,
  },
  {
    type: 'dxf',
    label: 'DXF Drawing',
    description: 'CAD drawing exchange format',
    extension: '.dxf',
    available: true,
  },
  {
    type: 'png',
    label: 'PCB Render (PNG)',
    description: 'Raster PCB render',
    extension: '.png',
    available: true,
  },
  {
    type: 'testpoints',
    label: 'Test Points',
    description: 'Test point locations',
    extension: '.json',
    available: true,
  },
  {
    type: 'variables_report',
    label: 'Variables Report',
    description: 'Solved parameter values',
    extension: '.json',
    available: true,
  },
  {
    type: 'datasheets',
    label: 'Datasheets',
    description: 'Component datasheets',
    extension: '.pdf',
    available: true,
  },
];

// =============================================================================
// Manufacturing Dashboard Types
// =============================================================================

export type DashboardStep = 'build' | 'review' | 'export';

export interface ReviewComment {
  pageId: string;
  text: string;
  timestamp: string;
}

export interface ReviewPageDefinition {
  id: string;
  label: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  icon: React.ComponentType<any>;
  order: number;
  isAvailable: (outputs: BuildOutputs) => boolean;
}

export interface ReviewPageProps {
  outputs: BuildOutputs;
  bomData: unknown;
  boardSummary: BoardSummary | null;
  projectRoot: string;
  targetName: string;
  isReviewed: boolean;
  onMarkReviewed: (reviewed: boolean) => void;
  comments: ReviewComment[];
  onAddComment: (text: string) => void;
}

export interface FabHouse {
  id: string;
  name: string;
  orderUrl: string;
  supported: boolean;
}

export interface ManufacturingDashboardState {
  projectRoot: string;
  targetName: string;
  activeStep: DashboardStep;
  activeReviewPage: string | null;
  reviewedPages: Record<string, boolean>;
  reviewComments: ReviewComment[];
  outputs: BuildOutputs | null;
  buildStatus: ManufacturingBuildStatus;
  buildStages: string[];
  bomData: unknown;
  boardSummary: BoardSummary | null;
  gitStatus: GitStatus | null;
  exportConfig: {
    directory: string;
    selectedFileTypes: FileExportType[];
    fabHouse: string;
    pcbQuantity: number;
    pcbaQuantity: number;
  };
  costEstimate: CostEstimate | null;
  isExporting: boolean;
  exportResult: { success: boolean; files: string[]; errors: string[] | null } | null;
  artifactVerification: Record<string, boolean>;
}

// BOMData is imported from '../../types/build' — dashboard components should
// import it from there directly.
