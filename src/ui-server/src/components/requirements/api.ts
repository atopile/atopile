/** API helpers for requirement editing, plot editing, and rerun. */

type WindowGlobals = Window & {
  __ATOPILE_API_URL__?: string;
  __ATOPILE_PROJECT_ROOT__?: string;
  __ATOPILE_TARGET__?: string;
};

function getApiUrl(): string {
  return (window as WindowGlobals).__ATOPILE_API_URL__ || '';
}

function getProjectRoot(): string {
  return (window as WindowGlobals).__ATOPILE_PROJECT_ROOT__ || '';
}

function getTarget(): string {
  return (window as WindowGlobals).__ATOPILE_TARGET__ || 'default';
}

export interface UpdateRequirementParams {
  source_file: string;
  var_name: string;
  updates: Record<string, string>;
}

export interface UpdateRequirementResponse {
  success: boolean;
  applied: Record<string, string>;
}

export async function updateRequirement(
  params: UpdateRequirementParams,
): Promise<UpdateRequirementResponse> {
  const apiUrl = getApiUrl();
  if (!apiUrl) throw new Error('API URL not configured');

  const res = await fetch(`${apiUrl}/api/requirements/update`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Update failed (${res.status}): ${detail}`);
  }

  return res.json();
}

export interface CreatePlotParams {
  source_file: string;
  req_var_name: string;
  plot_var_name: string;
  plot_type?: string;
  fields: Record<string, string>;
}

export async function createPlot(
  params: CreatePlotParams,
): Promise<{ success: boolean; plotVarName: string }> {
  const apiUrl = getApiUrl();
  if (!apiUrl) throw new Error('API URL not configured');

  const res = await fetch(`${apiUrl}/api/plots/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Create plot failed (${res.status}): ${detail}`);
  }

  return res.json();
}

export interface RerunResponse {
  success: boolean;
  message: string;
  buildTargets: Array<{ buildId: string; target: string }>;
}

export async function rerunSimulation(): Promise<RerunResponse> {
  const apiUrl = getApiUrl();
  const projectRoot = getProjectRoot();
  const target = getTarget();
  if (!apiUrl) throw new Error('API URL not configured');
  if (!projectRoot) throw new Error('Project root not configured');

  const res = await fetch(`${apiUrl}/api/requirements/rerun`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_root: projectRoot, target }),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Rerun failed (${res.status}): ${detail}`);
  }

  return res.json();
}

export interface RerunSingleParams {
  netlist_path: string;
  spice_sources: string;
  sim_type: string;
  net: string;
  measurement: string;
  tran_start: number;
  tran_stop: number;
  tran_step: number;
  settling_tolerance: number | null;
  context_nets: string[];
  min_val: number | null;
  max_val: number | null;
}

export interface RerunSingleResponse {
  actual: number | null;
  passed: boolean;
  timeSeries: {
    time: number[];
    signals: Record<string, number[]>;
  };
}

export async function rerunSingleSimulation(
  params: RerunSingleParams,
): Promise<RerunSingleResponse> {
  const apiUrl = getApiUrl();
  if (!apiUrl) throw new Error('API URL not configured');

  const res = await fetch(`${apiUrl}/api/simulations/rerun-single`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Single rerun failed (${res.status}): ${detail}`);
  }

  return res.json();
}
