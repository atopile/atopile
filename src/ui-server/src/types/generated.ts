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
 * THE SINGLE APP STATE - All state lives here.
 *
 * Python server owns this state and pushes it to all connected clients
 * via WebSocket on every change.
 */
export interface AppState {
    atopile?:                 AtopileObject;
    bomData?:                 null | BOMDataObject;
    bomError?:                null | string;
    builds?:                  BuildElement[];
    currentVariablesData?:    null | VariablesDataObject;
    developerMode?:           boolean;
    expandedTargets?:         string[];
    installError?:            null | string;
    installingPackageIds?:    string[];
    isConnected?:             boolean;
    isLoadingBom?:            boolean;
    isLoadingDependencies?:   boolean;
    isLoadingFiles?:          boolean;
    isLoadingModules?:        boolean;
    isLoadingPackageDetails?: boolean;
    isLoadingPackages?:       boolean;
    isLoadingProblems?:       boolean;
    isLoadingProjects?:       boolean;
    isLoadingStdlib?:         boolean;
    isLoadingVariables?:      boolean;
    open3D?:                  null | string;
    openFile?:                null | string;
    openFileColumn?:          number | null;
    openFileLine?:            number | null;
    openKicad?:               null | string;
    openLayout?:              null | string;
    packageDetailsError?:     null | string;
    packages?:                PackageElement[];
    packagesError?:           null | string;
    problemFilter?:           ProblemFilterObject;
    problems?:                ProblemElement[];
    projectDependencies?:     { [key: string]: ProjectDependencyElement[] };
    projectFiles?:            { [key: string]: ProjectFileElement[] };
    projectModules?:          { [key: string]: ProjectModuleElement[] };
    projects?:                ProjectElement[];
    projectsError?:           null | string;
    queuedBuilds?:            BuildElement[];
    selectedBuildName?:       null | string;
    selectedPackageDetails?:  null | PackageDetailsObject;
    selectedProjectName?:     null | string;
    selectedProjectRoot?:     null | string;
    selectedTargetNames?:     string[];
    stdlibItems?:             StdlibItemElement[];
    variablesError?:          null | string;
    version?:                 string;
    [property: string]: any;
}

/**
 * Atopile configuration state.
 */
export interface AtopileObject {
    availableBranches?:     string[];
    availableVersions?:     string[];
    branch?:                null | string;
    currentVersion?:        string;
    detectedInstallations?: AtopileDetectedInstallation[];
    error?:                 null | string;
    installProgress?:       null | AtopileInstallProgress;
    isInstalling?:          boolean;
    localPath?:             null | string;
    source?:                AtopileSource;
    [property: string]: any;
}

/**
 * A detected atopile installation.
 */
export interface AtopileDetectedInstallation {
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
export interface AtopileInstallProgress {
    message:  string;
    percent?: number | null;
    [property: string]: any;
}

export enum AtopileSource {
    Branch = "branch",
    Local = "local",
    Release = "release",
}

/**
 * Bill of Materials data.
 */
export interface BOMDataObject {
    components?: PurpleBOMComponent[];
    version?:    string;
    [property: string]: any;
}

/**
 * BOM component.
 */
export interface PurpleBOMComponent {
    description?:  null | string;
    id:            string;
    isBasic?:      boolean | null;
    isPreferred?:  boolean | null;
    lcsc?:         null | string;
    manufacturer?: null | string;
    mpn?:          null | string;
    package:       string;
    parameters?:   PurpleBOMParameter[];
    quantity?:     number;
    source?:       string;
    stock?:        number | null;
    type:          string;
    unitCost?:     number | null;
    usages?:       PurpleBOMUsage[];
    value:         string;
    [property: string]: any;
}

/**
 * BOM component parameter.
 */
export interface PurpleBOMParameter {
    name:  string;
    unit?: null | string;
    value: string;
    [property: string]: any;
}

/**
 * BOM component usage location.
 */
export interface PurpleBOMUsage {
    address:    string;
    designator: string;
    [property: string]: any;
}

/**
 * A build (active, queued, or completed).
 */
export interface BuildElement {
    buildId?:        null | string;
    displayName:     string;
    elapsedSeconds?: number;
    entry?:          null | string;
    error?:          null | string;
    errors?:         number;
    logDir?:         null | string;
    logFile?:        null | string;
    name:            string;
    projectName?:    null | string;
    projectRoot?:    null | string;
    queuePosition?:  number | null;
    returnCode?:     number | null;
    stages?:         PurpleBuildStage[] | null;
    startedAt?:      number | null;
    status?:         BuildStatus;
    target?:         null | string;
    totalStages?:    number;
    warnings?:       number;
    [property: string]: any;
}

/**
 * A stage within a build.
 */
export interface PurpleBuildStage {
    alerts?:         number;
    displayName?:    null | string;
    elapsedSeconds?: number;
    errors?:         number;
    infos?:          number;
    name:            string;
    stageId:         string;
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
 * Variables data for a build target.
 */
export interface VariablesDataObject {
    nodes?:   PurpleVariableNode[];
    version?: string;
    [property: string]: any;
}

/**
 * A node in the variable tree.
 */
export interface PurpleVariableNode {
    children?:  PurpleVariableNode[] | null;
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
 * Information about a package.
 */
export interface PackageElement {
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
 * Filter settings for problems.
 */
export interface ProblemFilterObject {
    buildNames?: string[];
    levels?:     Level[];
    stageIds?:   string[];
    [property: string]: any;
}

export enum Level {
    Error = "error",
    Warning = "warning",
}

/**
 * A problem (error or warning) from a build log.
 */
export interface ProblemElement {
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

/**
 * A project dependency with version info.
 */
export interface ProjectDependencyElement {
    hasUpdate?:     boolean;
    identifier:     string;
    isDirect?:      boolean;
    latestVersion?: null | string;
    name:           string;
    publisher:      string;
    repository?:    null | string;
    version:        string;
    via?:           string[] | null;
    [property: string]: any;
}

/**
 * A node in the file tree (either a file or folder).
 */
export interface ProjectFileElement {
    children?:  ProjectFileElement[] | null;
    extension?: null | string;
    name:       string;
    path:       string;
    type:       ProjectFileType;
    [property: string]: any;
}

export enum ProjectFileType {
    File = "file",
    Folder = "folder",
}

/**
 * A module/interface/component definition from an .ato file.
 */
export interface ProjectModuleElement {
    children?:  ProjectModuleChild[];
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
export interface ProjectModuleChild {
    children?: ProjectModuleChild[];
    itemType:  Type;
    name:      string;
    spec?:     null | string;
    typeName:  string;
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
 * A project discovered from ato.yaml.
 */
export interface ProjectElement {
    name:    string;
    root:    string;
    targets: ProjectTarget[];
    [property: string]: any;
}

/**
 * A build target from ato.yaml.
 */
export interface ProjectTarget {
    entry:      string;
    lastBuild?: null | PurpleBuildTargetStatus;
    name:       string;
    root:       string;
    [property: string]: any;
}

/**
 * Persisted status from last build of a target.
 */
export interface PurpleBuildTargetStatus {
    elapsedSeconds?: number | null;
    errors?:         number;
    stages?:         { [key: string]: any }[] | null;
    status:          BuildStatus;
    timestamp:       string;
    warnings?:       number;
    [property: string]: any;
}

/**
 * Detailed information about a package from the registry.
 */
export interface PackageDetailsObject {
    dependencies?:       PurplePackageDependency[];
    description?:        null | string;
    downloads?:          number | null;
    downloadsThisMonth?: number | null;
    downloadsThisWeek?:  number | null;
    homepage?:           null | string;
    identifier:          string;
    installed?:          boolean;
    installedIn?:        string[];
    installedVersion?:   null | string;
    license?:            null | string;
    name:                string;
    publisher:           string;
    repository?:         null | string;
    summary?:            null | string;
    version:             string;
    versionCount?:       number;
    versions?:           PurplePackageVersion[];
    [property: string]: any;
}

/**
 * A package dependency.
 */
export interface PurplePackageDependency {
    identifier: string;
    version?:   null | string;
    [property: string]: any;
}

/**
 * Information about a package version/release.
 */
export interface PurplePackageVersion {
    releasedAt?:      null | string;
    requiresAtopile?: null | string;
    size?:            number | null;
    version:          string;
    [property: string]: any;
}

/**
 * A standard library item (module, interface, trait, etc.).
 */
export interface StdlibItemElement {
    children?:   StdlibItemChild[];
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
export interface StdlibItemChild {
    children?:   StdlibItemChild[];
    enumValues?: string[];
    itemType:    Type;
    name:        string;
    type:        string;
    [property: string]: any;
}

/**
 * A project discovered from ato.yaml.
 */
export interface Project {
    name:    string;
    root:    string;
    targets: ProjectTargetObject[];
    [property: string]: any;
}

/**
 * A build target from ato.yaml.
 */
export interface ProjectTargetObject {
    entry:      string;
    lastBuild?: null | FluffyBuildTargetStatus;
    name:       string;
    root:       string;
    [property: string]: any;
}

/**
 * Persisted status from last build of a target.
 */
export interface FluffyBuildTargetStatus {
    elapsedSeconds?: number | null;
    errors?:         number;
    stages?:         { [key: string]: any }[] | null;
    status:          BuildStatus;
    timestamp:       string;
    warnings?:       number;
    [property: string]: any;
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
    logDir?:         null | string;
    logFile?:        null | string;
    name:            string;
    projectName?:    null | string;
    projectRoot?:    null | string;
    queuePosition?:  number | null;
    returnCode?:     number | null;
    stages?:         FluffyBuildStage[] | null;
    startedAt?:      number | null;
    status?:         BuildStatus;
    target?:         null | string;
    totalStages?:    number;
    warnings?:       number;
    [property: string]: any;
}

/**
 * A stage within a build.
 */
export interface FluffyBuildStage {
    alerts?:         number;
    displayName?:    null | string;
    elapsedSeconds?: number;
    errors?:         number;
    infos?:          number;
    name:            string;
    stageId:         string;
    status?:         StageStatus;
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
    stageId:         string;
    status?:         StageStatus;
    warnings?:       number;
    [property: string]: any;
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
    dependencies?:       FluffyPackageDependency[];
    description?:        null | string;
    downloads?:          number | null;
    downloadsThisMonth?: number | null;
    downloadsThisWeek?:  number | null;
    homepage?:           null | string;
    identifier:          string;
    installed?:          boolean;
    installedIn?:        string[];
    installedVersion?:   null | string;
    license?:            null | string;
    name:                string;
    publisher:           string;
    repository?:         null | string;
    summary?:            null | string;
    version:             string;
    versionCount?:       number;
    versions?:           FluffyPackageVersion[];
    [property: string]: any;
}

/**
 * A package dependency.
 */
export interface FluffyPackageDependency {
    identifier: string;
    version?:   null | string;
    [property: string]: any;
}

/**
 * Information about a package version/release.
 */
export interface FluffyPackageVersion {
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
    children?:   StdLIBItemChild[];
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
export interface StdLIBItemChild {
    children?:   StdLIBItemChild[];
    enumValues?: string[];
    itemType:    Type;
    name:        string;
    type:        string;
    [property: string]: any;
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
    components?: FluffyBOMComponent[];
    version?:    string;
    [property: string]: any;
}

/**
 * BOM component.
 */
export interface FluffyBOMComponent {
    description?:  null | string;
    id:            string;
    isBasic?:      boolean | null;
    isPreferred?:  boolean | null;
    lcsc?:         null | string;
    manufacturer?: null | string;
    mpn?:          null | string;
    package:       string;
    parameters?:   FluffyBOMParameter[];
    quantity?:     number;
    source?:       string;
    stock?:        number | null;
    type:          string;
    unitCost?:     number | null;
    usages?:       FluffyBOMUsage[];
    value:         string;
    [property: string]: any;
}

/**
 * BOM component parameter.
 */
export interface FluffyBOMParameter {
    name:  string;
    unit?: null | string;
    value: string;
    [property: string]: any;
}

/**
 * BOM component usage location.
 */
export interface FluffyBOMUsage {
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
    nodes?:   FluffyVariableNode[];
    version?: string;
    [property: string]: any;
}

/**
 * A node in the variable tree.
 */
export interface FluffyVariableNode {
    children?:  FluffyVariableNode[] | null;
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
 * A node in the variable tree.
 */
export interface VariableNode {
    children?:  VariableNode[] | null;
    name:       string;
    path:       string;
    type:       NodeType;
    typeName?:  null | string;
    variables?: TentacledVariable[] | null;
    [property: string]: any;
}

/**
 * A variable in the design.
 */
export interface TentacledVariable {
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
    children?:  ModuleDefinitionChild[];
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
export interface ModuleDefinitionChild {
    children?: ModuleDefinitionChild[];
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
 * A node in the file tree (either a file or folder).
 */
export interface FileTreeNode {
    children?:  FileTreeNode[] | null;
    extension?: null | string;
    name:       string;
    path:       string;
    type:       ProjectFileType;
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
    version:        string;
    via?:           string[] | null;
    [property: string]: any;
}

/**
 * Atopile configuration state.
 */
export interface AtopileConfig {
    availableBranches?:     string[];
    availableVersions?:     string[];
    branch?:                null | string;
    currentVersion?:        string;
    detectedInstallations?: AtopileConfigDetectedInstallation[];
    error?:                 null | string;
    installProgress?:       null | AtopileConfigInstallProgress;
    isInstalling?:          boolean;
    localPath?:             null | string;
    source?:                AtopileSource;
    [property: string]: any;
}

/**
 * A detected atopile installation.
 */
export interface AtopileConfigDetectedInstallation {
    path:     string;
    source?:  DetectedInstallationSource;
    version?: null | string;
    [property: string]: any;
}

/**
 * Installation progress info.
 */
export interface AtopileConfigInstallProgress {
    message:  string;
    percent?: number | null;
    [property: string]: any;
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
