/**
 * AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
 *
 * This file is generated from Python Pydantic models in:
 *   src/atopile/dataclasses.py
 *
 * To regenerate, run:
 *   python scripts/generate_types.py
 *
 * The source of truth is the Python Pydantic models.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

/**
 * A project discovered from ato.yaml.
 */
export interface Project {
    displayPath?:    null | string;
    name:            string;
    needsMigration?: boolean;
    root:            string;
    targets:         TargetElement[];
    [property: string]: any;
}

/**
 * A build target from ato.yaml.
 */
export interface TargetElement {
    entry:      string;
    lastBuild?: null | TargetBuildTargetStatus;
    name:       string;
    root:       string;
    [property: string]: any;
}

/**
 * Persisted status from last build of a target.
 */
export interface TargetBuildTargetStatus {
    buildId?:        null | string;
    elapsedSeconds?: number | null;
    errors?:         number;
    stages?:         { [key: string]: any }[] | null;
    status:          BuildStatus;
    timestamp:       string;
    warnings?:       number;
    [property: string]: any;
}

/**
 * Build status states - overall status of a build.
 */
export enum BuildStatus {
    Building = "building",
    Cancelled = "cancelled",
    Failed = "failed",
    Queued = "queued",
    Success = "success",
    Warning = "warning",
}

/**
 * A build target from ato.yaml.
 */
export interface BuildTarget {
    entry:      string;
    lastBuild?: null | BuildTargetBuildTargetStatus;
    name:       string;
    root:       string;
    [property: string]: any;
}

/**
 * Persisted status from last build of a target.
 */
export interface BuildTargetBuildTargetStatus {
    buildId?:        null | string;
    elapsedSeconds?: number | null;
    errors?:         number;
    stages?:         { [key: string]: any }[] | null;
    status:          BuildStatus;
    timestamp:       string;
    warnings?:       number;
    [property: string]: any;
}

/**
 * A build (active, queued, or completed).
 */
export interface Build {
    buildId?:        null | string;
    displayName:     string;
    elapsedSeconds?: number;
    entry?:          null | string;
    error?:          null | string;
    errors?:         number;
    frozen?:         boolean | null;
    logDir?:         null | string;
    logFile?:        null | string;
    name:            string;
    projectName?:    null | string;
    projectRoot?:    null | string;
    queuePosition?:  number | null;
    returnCode?:     number | null;
    stages?:         { [key: string]: any }[];
    standalone?:     boolean;
    startedAt?:      number | null;
    status?:         BuildStatus;
    target?:         null | string;
    timestamp?:      null | string;
    totalStages?:    number | null;
    warnings?:       number;
    [property: string]: any;
}

/**
 * A stage within a build.
 */
export interface BuildStage {
    alerts?:         number;
    displayName?:    null | string;
    elapsedSeconds?: number;
    errors?:         number;
    infos?:          number;
    name:            string;
    stageId?:        string;
    status?:         StageStatus;
    warnings?:       number;
    [property: string]: any;
}

/**
 * Stage status states - status of individual build stages.
 */
export enum StageStatus {
    Error = "error",
    Failed = "failed",
    Pending = "pending",
    Running = "running",
    Skipped = "skipped",
    Success = "success",
    Warning = "warning",
}

/**
 * Information about a package.
 */
export interface PackageInfo {
    description?:   null | string;
    downloads?:     number | null;
    hasUpdate?:     boolean;
    homepage?:      null | string;
    identifier:     string;
    installed?:     boolean;
    installedIn?:   string[];
    keywords?:      string[] | null;
    latestVersion?: null | string;
    license?:       null | string;
    name:           string;
    publisher:      string;
    repository?:    null | string;
    summary?:       null | string;
    version?:       null | string;
    versionCount?:  number | null;
    [property: string]: any;
}

/**
 * Detailed information about a package from the registry.
 */
export interface PackageDetails {
    artifacts?:          PackageArtifact[];
    authors?:            PackageAuthor[];
    builds?:             string[] | null;
    createdAt?:          null | string;
    dependencies?:       PackageDependency[];
    description?:        null | string;
    downloads?:          number | null;
    downloadsThisMonth?: number | null;
    downloadsThisWeek?:  number | null;
    homepage?:           null | string;
    identifier:          string;
    importStatements?:   PackageImportStatement[];
    installed?:          boolean;
    installedIn?:        string[];
    installedVersion?:   null | string;
    layouts?:            PackageLayout[];
    license?:            null | string;
    name:                string;
    publisher:           string;
    readme?:             null | string;
    releasedAt?:         null | string;
    repository?:         null | string;
    summary?:            null | string;
    version:             string;
    versionCount?:       number;
    versions?:           VersionElement[];
    [property: string]: any;
}

export interface PackageArtifact {
    buildName?: null | string;
    filename:   string;
    hashes:     PackageFileHashes;
    size:       number;
    url:        string;
    [property: string]: any;
}

export interface PackageFileHashes {
    sha256: string;
    [property: string]: any;
}

export interface PackageAuthor {
    email?: null | string;
    name:   string;
    [property: string]: any;
}

/**
 * A package dependency.
 */
export interface PackageDependency {
    identifier: string;
    version?:   null | string;
    [property: string]: any;
}

export interface PackageImportStatement {
    buildName:       string;
    importStatement: string;
    [property: string]: any;
}

export interface PackageLayout {
    buildName: string;
    url:       string;
    [property: string]: any;
}

/**
 * Information about a package version/release.
 */
export interface VersionElement {
    releasedAt?:      null | string;
    requiresAtopile?: null | string;
    size?:            number | null;
    version:          string;
    [property: string]: any;
}

/**
 * Information about a package version/release.
 */
export interface PackageVersion {
    releasedAt?:      null | string;
    requiresAtopile?: null | string;
    size?:            number | null;
    version:          string;
    [property: string]: any;
}

/**
 * A project dependency with version info.
 */
export interface DependencyInfo {
    hasUpdate?:     boolean;
    identifier:     string;
    isDirect?:      boolean;
    latestVersion?: null | string;
    name:           string;
    publisher:      string;
    repository?:    null | string;
    status?:        null | string;
    version:        string;
    via?:           string[] | null;
    [property: string]: any;
}

/**
 * Request to sync packages for a project.
 */
export interface SyncPackagesRequest {
    force?:      boolean;
    projectRoot: string;
    [property: string]: any;
}

/**
 * Response from sync packages action.
 */
export interface SyncPackagesResponse {
    message:           string;
    modifiedPackages?: string[] | null;
    operationId?:      null | string;
    success:           boolean;
    [property: string]: any;
}

/**
 * A problem (error or warning) from a build log.
 */
export interface Problem {
    atoTraceback?: null | string;
    buildName?:    null | string;
    column?:       number | null;
    excInfo?:      null | string;
    file?:         null | string;
    id:            string;
    level:         Level;
    line?:         number | null;
    logger?:       null | string;
    message:       string;
    projectName?:  null | string;
    stage?:        null | string;
    timestamp?:    null | string;
    [property: string]: any;
}

export enum Level {
    Error = "error",
    Warning = "warning",
}

/**
 * Filter settings for problems.
 */
export interface ProblemFilter {
    buildNames?: string[];
    levels?:     Level[];
    stageIds?:   string[];
    [property: string]: any;
}

/**
 * A standard library item (module, interface, trait, etc.).
 */
export interface StdLIBItem {
    children?:   ChildElement[];
    description: string;
    id:          string;
    name:        string;
    parameters?: { [key: string]: string }[];
    type:        Type;
    usage?:      null | string;
    [property: string]: any;
}

/**
 * A child field within a standard library item.
 */
export interface ChildElement {
    children?:   ChildElement[];
    enumValues?: string[];
    itemType:    Type;
    name:        string;
    type:        string;
    [property: string]: any;
}

/**
 * Type of standard library item.
 */
export enum Type {
    Component = "component",
    Interface = "interface",
    Module = "module",
    Parameter = "parameter",
    Trait = "trait",
}

/**
 * A child field within a standard library item.
 */
export interface StdLIBChild {
    children?:   StdLIBChild[];
    enumValues?: string[];
    itemType:    Type;
    name:        string;
    type:        string;
    [property: string]: any;
}

/**
 * Bill of Materials data.
 */
export interface BOMData {
    components?: ComponentElement[];
    version?:    string;
    [property: string]: any;
}

/**
 * BOM component.
 */
export interface ComponentElement {
    description?:  null | string;
    id:            string;
    isBasic?:      boolean | null;
    isPreferred?:  boolean | null;
    lcsc?:         null | string;
    manufacturer?: null | string;
    mpn?:          null | string;
    package:       string;
    parameters?:   ComponentParameter[];
    quantity?:     number;
    source?:       string;
    stock?:        number | null;
    type:          string;
    unitCost?:     number | null;
    usages?:       ComponentUsage[];
    value:         string;
    [property: string]: any;
}

/**
 * BOM component parameter.
 */
export interface ComponentParameter {
    name:  string;
    unit?: null | string;
    value: string;
    [property: string]: any;
}

/**
 * BOM component usage location.
 */
export interface ComponentUsage {
    address:    string;
    designator: string;
    [property: string]: any;
}

/**
 * BOM component.
 */
export interface BOMComponent {
    description?:  null | string;
    id:            string;
    isBasic?:      boolean | null;
    isPreferred?:  boolean | null;
    lcsc?:         null | string;
    manufacturer?: null | string;
    mpn?:          null | string;
    package:       string;
    parameters?:   BOMComponentParameter[];
    quantity?:     number;
    source?:       string;
    stock?:        number | null;
    type:          string;
    unitCost?:     number | null;
    usages?:       BOMComponentUsage[];
    value:         string;
    [property: string]: any;
}

/**
 * BOM component parameter.
 */
export interface BOMComponentParameter {
    name:  string;
    unit?: null | string;
    value: string;
    [property: string]: any;
}

/**
 * BOM component usage location.
 */
export interface BOMComponentUsage {
    address:    string;
    designator: string;
    [property: string]: any;
}

/**
 * BOM component parameter.
 */
export interface BOMParameter {
    name:  string;
    unit?: null | string;
    value: string;
    [property: string]: any;
}

/**
 * BOM component usage location.
 */
export interface BOMUsage {
    address:    string;
    designator: string;
    [property: string]: any;
}

/**
 * Variables data for a build target.
 */
export interface VariablesData {
    nodes?:   NodeElement[];
    version?: string;
    [property: string]: any;
}

/**
 * A node in the variable tree.
 */
export interface NodeElement {
    children?:  NodeElement[] | null;
    name:       string;
    path:       string;
    type:       NodeType;
    typeName?:  null | string;
    variables?: PurpleVariable[] | null;
    [property: string]: any;
}

export enum NodeType {
    Component = "component",
    Interface = "interface",
    Module = "module",
}

/**
 * A variable in the design.
 */
export interface PurpleVariable {
    actual?:          null | string;
    actualTolerance?: null | string;
    meetsSpec?:       boolean | null;
    name:             string;
    source?:          null | string;
    spec?:            null | string;
    specTolerance?:   null | string;
    type?:            string;
    unit?:            null | string;
    [property: string]: any;
}

/**
 * A node in the variable tree.
 */
export interface VariableNode {
    children?:  VariableNode[] | null;
    name:       string;
    path:       string;
    type:       NodeType;
    typeName?:  null | string;
    variables?: FluffyVariable[] | null;
    [property: string]: any;
}

/**
 * A variable in the design.
 */
export interface FluffyVariable {
    actual?:          null | string;
    actualTolerance?: null | string;
    meetsSpec?:       boolean | null;
    name:             string;
    source?:          null | string;
    spec?:            null | string;
    specTolerance?:   null | string;
    type?:            string;
    unit?:            null | string;
    [property: string]: any;
}

/**
 * A variable in the design.
 */
export interface Variable {
    actual?:          null | string;
    actualTolerance?: null | string;
    meetsSpec?:       boolean | null;
    name:             string;
    source?:          null | string;
    spec?:            null | string;
    specTolerance?:   null | string;
    type?:            string;
    unit?:            null | string;
    [property: string]: any;
}

/**
 * A module/interface/component definition from an .ato file.
 */
export interface ModuleDefinition {
    children?:  ChildObject[];
    entry:      string;
    file:       string;
    line?:      number | null;
    name:       string;
    superType?: null | string;
    type:       NodeType;
    [property: string]: any;
}

/**
 * A child field within a module (interface, parameter, nested module, etc.).
 */
export interface ChildObject {
    children?: ChildObject[];
    itemType:  Type;
    name:      string;
    spec?:     null | string;
    typeName:  string;
    [property: string]: any;
}

/**
 * A child field within a module (interface, parameter, nested module, etc.).
 */
export interface ModuleChild {
    children?: ModuleChild[];
    itemType:  Type;
    name:      string;
    spec?:     null | string;
    typeName:  string;
    [property: string]: any;
}

/**
 * atopile configuration state.
 */
export interface AtopileConfig {
    availableBranches?:     string[];
    availableVersions?:     string[];
    branch?:                null | string;
    currentVersion?:        string;
    detectedInstallations?: DetectedInstallationElement[];
    error?:                 null | string;
    installProgress?:       null | InstallProgressObject;
    isInstalling?:          boolean;
    localPath?:             null | string;
    source?:                AtopileConfigSource;
    [property: string]: any;
}

/**
 * A detected atopile installation.
 */
export interface DetectedInstallationElement {
    path:     string;
    source?:  DetectedInstallationSource;
    version?: null | string;
    [property: string]: any;
}

export enum DetectedInstallationSource {
    Manual = "manual",
    Path = "path",
    Venv = "venv",
}

/**
 * Installation progress info.
 */
export interface InstallProgressObject {
    message:  string;
    percent?: number | null;
    [property: string]: any;
}

export enum AtopileConfigSource {
    Branch = "branch",
    Local = "local",
    Release = "release",
}

/**
 * A detected atopile installation.
 */
export interface DetectedInstallation {
    path:     string;
    source?:  DetectedInstallationSource;
    version?: null | string;
    [property: string]: any;
}

/**
 * Installation progress info.
 */
export interface InstallProgress {
    message:  string;
    percent?: number | null;
    [property: string]: any;
}

/**
 * WebSocket event message payload.
 */
export interface EventMessage {
    data?: { [key: string]: any } | null;
    event: EventType;
    type?: EventMessageType;
    [property: string]: any;
}

/**
 * Event types emitted to WebSocket clients.
 */
export enum EventType {
    AtopileConfigChanged = "atopile_config_changed",
    BOMChanged = "bom_changed",
    BuildsChanged = "builds_changed",
    LogViewCurrentIDChanged = "log_view_current_id_changed",
    Open3D = "open_3d",
    OpenKicad = "open_kicad",
    OpenLayout = "open_layout",
    PackageModified = "package_modified",
    PackagesChanged = "packages_changed",
    PackagesDownloadsUpdated = "packages_downloads_updated",
    PartsChanged = "parts_changed",
    ProblemsChanged = "problems_changed",
    ProjectDependenciesChanged = "project_dependencies_changed",
    ProjectFilesChanged = "project_files_changed",
    ProjectModulesChanged = "project_modules_changed",
    ProjectsChanged = "projects_changed",
    StdlibChanged = "stdlib_changed",
    VariablesChanged = "variables_changed",
}

export enum EventMessageType {
    Event = "event",
}
