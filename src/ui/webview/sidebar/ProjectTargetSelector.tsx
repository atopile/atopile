import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  Check,
  ChevronDown,
  FolderOpen,
  Pencil,
  Plus,
  Target,
  Trash2,
  X,
} from "lucide-react";
import type {
  ModuleDefinition,
  Project,
  ResolvedBuildTarget,
  UiEntryCheckData,
} from "../../shared/generated-types";
import { WebviewRpcClient, rpcClient } from "../shared/rpcClient";
import "./ProjectTargetSelector.css";

interface ProjectTargetSelectorProps {
  projects: Project[];
  modules: ModuleDefinition[];
  selectedProject: string | null;
  onSelectProject: (root: string) => void;
  selectedTarget: string | null;
  onSelectTarget: (target: string) => void;
}

interface NewProjectData {
  name: string;
  parentDirectory: string;
  license?: string;
  description?: string;
}

interface NewTargetData {
  name: string;
  entry: string;
}

interface EntryStatus {
  fileExists: boolean;
  moduleExists: boolean;
  targetExists: boolean;
}

function formatPath(path: string): string {
  if (!path) return "";
  const parts = path.split("/");
  return parts.slice(-2).join("/");
}

function fuzzyMatch(text: string, query: string): boolean {
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();

  if (lowerText.includes(lowerQuery)) return true;

  let queryIdx = 0;
  for (const char of lowerText) {
    if (char === lowerQuery[queryIdx]) {
      queryIdx += 1;
      if (queryIdx === lowerQuery.length) return true;
    }
  }
  return false;
}

function ProjectSelector({
  projects,
  activeProject,
  onSelectProject,
  onCreateProject,
}: {
  projects: Project[];
  activeProject: Project | null;
  onSelectProject: (projectRoot: string) => void;
  onCreateProject: () => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const comboboxRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const filteredProjects = useMemo(() => {
    if (!searchQuery.trim()) return projects;
    return projects.filter(
      (project) =>
        fuzzyMatch(project.name, searchQuery) || fuzzyMatch(project.root, searchQuery),
    );
  }, [projects, searchQuery]);

  useEffect(() => {
    setHighlightedIndex(0);
  }, [filteredProjects.length]);

  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (comboboxRef.current?.contains(event.target as Node)) {
        return;
      }
      setIsOpen(false);
      setSearchQuery("");
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
        setSearchQuery("");
        inputRef.current?.blur();
        return;
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        if (!isOpen) {
          setIsOpen(true);
          return;
        }
        setHighlightedIndex((prev) =>
          prev < filteredProjects.length - 1 ? prev + 1 : prev,
        );
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : 0));
        return;
      }
      if (event.key === "Enter") {
        event.preventDefault();
        const project = filteredProjects[highlightedIndex];
        if (!project) return;
        onSelectProject(project.root);
        setIsOpen(false);
        setSearchQuery("");
        inputRef.current?.blur();
      }
    },
    [filteredProjects, highlightedIndex, isOpen, onSelectProject],
  );

  const displayValue = isOpen ? searchQuery : activeProject?.name ?? "";

  return (
    <div className="project-combobox" ref={comboboxRef}>
      <div className={`combobox-input-wrapper ${isOpen ? "open" : ""}`}>
        <FolderOpen
          size={12}
          className="combobox-icon"
          onClick={() => inputRef.current?.focus()}
        />
        <input
          ref={inputRef}
          type="text"
          className="combobox-input"
          placeholder={activeProject?.name || "Select project..."}
          value={displayValue}
          onChange={(event) => {
            setSearchQuery(event.target.value);
            if (!isOpen) setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          aria-haspopup="listbox"
          aria-expanded={isOpen}
          aria-autocomplete="list"
        />
        <button
          type="button"
          className="combobox-toggle"
          onClick={() => {
            setIsOpen((prev) => !prev);
            if (!isOpen) inputRef.current?.focus();
          }}
          tabIndex={-1}
        >
          <ChevronDown size={14} className={`chevron ${isOpen ? "open" : ""}`} />
        </button>
      </div>

      {isOpen ? (
        <div className="combobox-dropdown">
          <div className="combobox-list" role="listbox">
            {filteredProjects.length === 0 ? (
              <div className="combobox-empty">No matching projects</div>
            ) : (
              filteredProjects.map((project, index) => {
                const isActive = project.root === activeProject?.root;
                const isHighlighted = index === highlightedIndex;
                return (
                  <button
                    key={project.root}
                    className={`combobox-option ${isActive ? "active" : ""} ${isHighlighted ? "highlighted" : ""}`}
                    onClick={() => {
                      onSelectProject(project.root);
                      setIsOpen(false);
                      setSearchQuery("");
                      inputRef.current?.blur();
                    }}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    role="option"
                    aria-selected={isActive}
                  >
                    <FolderOpen size={12} className="option-icon" />
                    <span className="combobox-option-name">{project.name}</span>
                    <span className="combobox-option-path" title={project.root}>
                      {formatPath(project.root)}
                    </span>
                    {isActive ? <Check size={12} className="check-icon" /> : null}
                  </button>
                );
              })
            )}
          </div>

          <div className="combobox-footer">
            <button className="combobox-create-btn" onClick={onCreateProject}>
              <Plus size={12} />
              <span>New Project</span>
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function TargetSelector({
  targets,
  activeTargetName,
  onSelectTarget,
  disabled,
}: {
  targets: ResolvedBuildTarget[];
  activeTargetName: string | null;
  onSelectTarget: (targetName: string) => void;
  disabled?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const comboboxRef = useRef<HTMLDivElement>(null);

  const activeTarget = targets.find((target) => target.name === activeTargetName) ?? targets[0] ?? null;

  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (comboboxRef.current?.contains(event.target as Node)) {
        return;
      }
      setIsOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
        return;
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        if (!isOpen) {
          setIsOpen(true);
          return;
        }
        setHighlightedIndex((prev) => (prev < targets.length - 1 ? prev + 1 : prev));
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : 0));
        return;
      }
      if (event.key === "Enter") {
        event.preventDefault();
        const target = targets[highlightedIndex];
        if (!target) return;
        onSelectTarget(target.name);
        setIsOpen(false);
      }
    },
    [highlightedIndex, isOpen, onSelectTarget, targets],
  );

  if (targets.length === 0 && !activeTargetName) {
    return (
      <div className="target-selector-empty">
        <span>No builds defined</span>
      </div>
    );
  }

  return (
    <div className="target-combobox" ref={comboboxRef}>
      <button
        type="button"
        className={`target-combobox-trigger ${isOpen ? "open" : ""}`}
        onClick={() => {
          if (!disabled) setIsOpen((prev) => !prev);
        }}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <Target size={14} className="target-icon" />
        <span className="target-trigger-name">
          {activeTarget?.name || activeTargetName || "Select build"}
        </span>
        <span className="target-combobox-chevron">
          <ChevronDown size={14} className={`chevron ${isOpen ? "open" : ""}`} />
        </span>
      </button>

      {isOpen ? (
        <div className="target-combobox-dropdown">
          <div className="target-combobox-list" role="listbox">
            {targets.map((target, index) => {
              const isActive = target.name === activeTargetName;
              const isHighlighted = index === highlightedIndex;
              return (
                <button
                  key={target.name}
                  className={`target-option ${isActive ? "active" : ""} ${isHighlighted ? "highlighted" : ""}`}
                  onClick={() => {
                    onSelectTarget(target.name);
                    setIsOpen(false);
                  }}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  role="option"
                  aria-selected={isActive}
                >
                  <Target size={12} className="option-icon" />
                  <span className="target-option-name">{target.name}</span>
                  {target.entry ? (
                    <span className="target-option-entry">{target.entry.split(":").pop()}</span>
                  ) : null}
                  {isActive ? <Check size={12} className="check-icon" /> : null}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function NewProjectForm({
  initialParentDirectory,
  onSubmit,
  onCancel,
  isCreating,
  error,
}: {
  initialParentDirectory: string;
  onSubmit: (data: NewProjectData) => void;
  onCancel: () => void;
  isCreating: boolean;
  error: string | null;
}) {
  const [name, setName] = useState("");
  const [parentDirectory, setParentDirectory] = useState(initialParentDirectory);
  const [license, setLicense] = useState("");
  const [description, setDescription] = useState("");
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    nameRef.current?.focus();
  }, []);

  const isValid = name.trim().length > 0 && parentDirectory.trim().length > 0;

  return (
    <form
      className="new-project-form"
      onSubmit={(event) => {
        event.preventDefault();
        if (!isValid) return;
        onSubmit({
          name: name.trim(),
          parentDirectory: parentDirectory.trim(),
          license: license || undefined,
          description: description.trim() || undefined,
        });
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") onCancel();
      }}
    >
      <div className="form-header">
        <span className="form-title">Create New Project</span>
        <button
          type="button"
          className="form-close-btn"
          onClick={onCancel}
          disabled={isCreating}
        >
          <X size={14} />
        </button>
      </div>

      {error ? (
        <div className="form-error">
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="form-field">
        <label htmlFor="project-name">
          Name <span className="required">*</span>
        </label>
        <input
          ref={nameRef}
          id="project-name"
          type="text"
          placeholder="my-project"
          value={name}
          onChange={(event) => setName(event.target.value)}
          disabled={isCreating}
          required
        />
      </div>

      <div className="form-field">
        <label htmlFor="project-path">
          Location <span className="required">*</span>
        </label>
        <div className="form-path-input">
          <input
            id="project-path"
            type="text"
            placeholder="/path/to/projects"
            value={parentDirectory}
            onChange={(event) => setParentDirectory(event.target.value)}
            disabled={isCreating}
            title={parentDirectory}
            required
          />
          <button
            type="button"
            className="form-browse-btn"
            onClick={async () => {
              const path = await rpcClient?.requestAction<string | undefined>("vscode.browseFolder");
              if (path) setParentDirectory(path);
            }}
            disabled={isCreating}
            title="Browse..."
          >
            <FolderOpen size={12} />
          </button>
        </div>
      </div>

      <div className="form-field">
        <label htmlFor="project-license">License</label>
        <input
          id="project-license"
          type="text"
          placeholder="MIT"
          value={license}
          onChange={(event) => setLicense(event.target.value)}
          disabled={isCreating}
        />
      </div>

      <div className="form-field">
        <label htmlFor="project-description">Description</label>
        <textarea
          id="project-description"
          placeholder="Project description (optional)"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          disabled={isCreating}
          rows={2}
        />
      </div>

      <div className="form-actions">
        <button
          type="button"
          className="form-btn secondary"
          onClick={onCancel}
          disabled={isCreating}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="form-btn primary"
          disabled={isCreating || !isValid}
        >
          {isCreating ? "Creating..." : "Create"}
        </button>
      </div>
    </form>
  );
}

function NewTargetForm({
  mode = "create",
  projectName,
  projectRoot,
  modules,
  initialName = "",
  initialEntry = "",
  entryCheck,
  onSubmit,
  onCancel,
  isCreating,
  error,
}: {
  mode?: "create" | "edit";
  projectName?: string;
  projectRoot: string;
  modules: ModuleDefinition[];
  initialName?: string;
  initialEntry?: string;
  entryCheck: UiEntryCheckData;
  onSubmit: (data: NewTargetData) => void;
  onCancel: () => void;
  isCreating: boolean;
  error: string | null;
}) {
  const [name, setName] = useState(initialName);
  const [entry, setEntry] = useState(initialEntry);
  const [entryStatus, setEntryStatus] = useState<EntryStatus | null>(null);
  const [isCheckingEntry, setIsCheckingEntry] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const nameRef = useRef<HTMLInputElement>(null);
  const entryRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    nameRef.current?.focus();
  }, []);

  useEffect(() => {
    setName(initialName);
    setEntry(initialEntry);
  }, [initialEntry, initialName]);

  const suggestions = useMemo(() => {
    if (!modules.length || !entry) return [];
    const lowerEntry = entry.toLowerCase();
    return modules
      .filter(
        (module) =>
          module.entry.toLowerCase().includes(lowerEntry) ||
          module.name.toLowerCase().includes(lowerEntry),
      )
      .slice(0, 8);
  }, [entry, modules]);

  useEffect(() => {
    setHighlightedIndex(0);
  }, [suggestions.length]);

  useEffect(() => {
    if (!showSuggestions) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (suggestionsRef.current?.contains(event.target as Node)) {
        return;
      }
      if (entryRef.current?.contains(event.target as Node)) {
        return;
      }
      setShowSuggestions(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showSuggestions]);

  useEffect(() => {
    if (!projectRoot || !entry.trim()) {
      setEntryStatus(null);
      setIsCheckingEntry(false);
      return;
    }
    const timer = window.setTimeout(() => {
      setIsCheckingEntry(true);
      rpcClient?.sendAction("checkEntry", {
        projectRoot,
        entry: entry.trim(),
      });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [entry, projectRoot]);

  useEffect(() => {
    if (entryCheck.projectRoot !== projectRoot || entryCheck.entry !== entry.trim()) {
      return;
    }
    setEntryStatus({
      fileExists: entryCheck.fileExists,
      moduleExists: entryCheck.moduleExists,
      targetExists: entryCheck.targetExists,
    });
    setIsCheckingEntry(entryCheck.loading);
  }, [entry, entryCheck, projectRoot]);

  const isValidEntryFormat = (value: string): boolean =>
    /\.ato:(.+)$/.test(value.trim());

  const entryFormatError =
    entry.trim() && !isValidEntryFormat(entry)
      ? "Entry must be in format: file.ato:ModuleName"
      : null;

  const entryStatusMessage = (() => {
    if (entryFormatError) return entryFormatError;
    if (isCheckingEntry) return "Checking...";
    if (!entryStatus) return "Format: file.ato:ModuleName";
    if (entryStatus.targetExists && entry.trim() !== initialEntry.trim()) {
      return "Entry already used as build target";
    }
    if (entryStatus.moduleExists) return "Module exists";
    if (entryStatus.fileExists) return "Module not found in file";
    return "Entry does not exist";
  })();

  const entryStatusClass = (() => {
    if (
      entryFormatError ||
      (entryStatus?.targetExists && entry.trim() !== initialEntry.trim())
    ) {
      return "status-error";
    }
    if (entryStatus?.moduleExists) return "status-exists";
    if (entryStatus?.fileExists === false || entryStatus?.moduleExists === false) {
      return "status-create";
    }
    return "";
  })();

  const canSubmit =
    !!name.trim() &&
    !!entry.trim() &&
    isValidEntryFormat(entry) &&
    !(entryStatus?.targetExists && entry.trim() !== initialEntry.trim());

  return (
    <form
      className="new-target-form"
      onSubmit={(event) => {
        event.preventDefault();
        if (!canSubmit) return;
        onSubmit({ name: name.trim(), entry: entry.trim() });
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape" && !showSuggestions) onCancel();
      }}
    >
      <div className="form-header">
        <span className="form-title">
          {mode === "edit" ? "Edit Build" : "New Build"}
          {projectName ? ` in ${projectName}` : ""}
        </span>
        <button
          type="button"
          className="form-close-btn"
          onClick={onCancel}
          disabled={isCreating}
        >
          <X size={14} />
        </button>
      </div>

      {error ? (
        <div className="form-error">
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="form-field">
        <label htmlFor="target-name">Name</label>
        <input
          ref={nameRef}
          id="target-name"
          type="text"
          placeholder="e.g., sensor_board"
          value={name}
          onChange={(event) => setName(event.target.value)}
          disabled={isCreating}
          required
        />
      </div>

      <div className="form-field entry-field">
        <label htmlFor="target-entry">Entry Point</label>
        <div className="entry-input-wrapper">
          <input
            ref={entryRef}
            id="target-entry"
            type="text"
            placeholder="e.g., main.ato:App"
            value={entry}
            onChange={(event) => {
              setEntry(event.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onKeyDown={(event) => {
              if (!showSuggestions || suggestions.length === 0) {
                if (event.key === "Escape") onCancel();
                return;
              }
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setHighlightedIndex((prev) => Math.min(prev + 1, suggestions.length - 1));
                return;
              }
              if (event.key === "ArrowUp") {
                event.preventDefault();
                setHighlightedIndex((prev) => Math.max(prev - 1, 0));
                return;
              }
              if (event.key === "Enter" && suggestions[highlightedIndex]) {
                event.preventDefault();
                setEntry(suggestions[highlightedIndex].entry);
                setShowSuggestions(false);
                return;
              }
              if (event.key === "Escape") {
                setShowSuggestions(false);
              }
            }}
            disabled={isCreating}
            autoComplete="off"
            required
          />
          {showSuggestions && suggestions.length > 0 ? (
            <div className="entry-suggestions" ref={suggestionsRef}>
              {suggestions.map((module, index) => (
                <button
                  key={module.entry}
                  type="button"
                  className={`entry-suggestion ${index === highlightedIndex ? "highlighted" : ""}`}
                  onClick={() => {
                    setEntry(module.entry);
                    setShowSuggestions(false);
                  }}
                  onMouseEnter={() => setHighlightedIndex(index)}
                >
                  <span className="suggestion-name">{module.name}</span>
                  <span className="suggestion-file">{module.file}</span>
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <span className={`form-hint ${entryStatusClass}`}>{entryStatusMessage}</span>
      </div>

      <div className="form-actions">
        <button
          type="button"
          className="form-btn secondary"
          onClick={onCancel}
          disabled={isCreating}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="form-btn primary"
          disabled={isCreating || !canSubmit}
        >
          {isCreating
            ? mode === "edit"
              ? "Saving..."
              : "Creating..."
            : mode === "edit"
              ? "Save"
              : "Create"}
        </button>
      </div>
    </form>
  );
}

export function ProjectTargetSelector({
  projects,
  modules,
  selectedProject,
  onSelectProject,
  selectedTarget,
  onSelectTarget,
}: ProjectTargetSelectorProps) {
  const entryCheck = WebviewRpcClient.useSubscribe("entryCheck");
  const [showNewProjectForm, setShowNewProjectForm] = useState(false);
  const [showNewTargetForm, setShowNewTargetForm] = useState(false);
  const [showEditTargetForm, setShowEditTargetForm] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [isCreatingTarget, setIsCreatingTarget] = useState(false);
  const [isUpdatingTarget, setIsUpdatingTarget] = useState(false);
  const [isDeletingTarget, setIsDeletingTarget] = useState(false);
  const [createProjectError, setCreateProjectError] = useState<string | null>(null);
  const [createTargetError, setCreateTargetError] = useState<string | null>(null);
  const [editTargetError, setEditTargetError] = useState<string | null>(null);

  useEffect(() => {
    if (showNewProjectForm) setCreateProjectError(null);
  }, [showNewProjectForm]);

  useEffect(() => {
    if (showNewTargetForm) setCreateTargetError(null);
  }, [showNewTargetForm]);

  useEffect(() => {
    if (showEditTargetForm) setEditTargetError(null);
  }, [showEditTargetForm]);

  const activeProject = useMemo(
    () => projects.find((project) => project.root === selectedProject) ?? null,
    [projects, selectedProject],
  );

  const activeTargetName = useMemo(
    () => selectedTarget || activeProject?.targets[0]?.name || null,
    [activeProject, selectedTarget],
  );

  const activeTarget = useMemo(
    () =>
      activeProject?.targets.find((target) => target.name === activeTargetName) ??
      activeProject?.targets[0] ??
      null,
    [activeProject, activeTargetName],
  );

  const defaultParentDirectory = useMemo(() => {
    if (activeProject) {
      const parts = activeProject.root.split("/");
      return parts.slice(0, -1).join("/") || activeProject.root;
    }
    const firstProject = projects[0];
    if (!firstProject) return "";
    const parts = firstProject.root.split("/");
    return parts.slice(0, -1).join("/") || firstProject.root;
  }, [activeProject, projects]);

  return (
    <div className="projects-panel-v2">
      {showNewProjectForm ? (
        <NewProjectForm
          initialParentDirectory={defaultParentDirectory}
          onSubmit={(data) => {
            setIsCreatingProject(true);
            setCreateProjectError(null);
            rpcClient?.sendAction("createProject", {
              name: data.name,
              parentDirectory: data.parentDirectory,
              license: data.license,
              description: data.description,
            });
            setShowNewProjectForm(false);
            setIsCreatingProject(false);
          }}
          onCancel={() => setShowNewProjectForm(false)}
          isCreating={isCreatingProject}
          error={createProjectError}
        />
      ) : null}

      {showNewTargetForm && activeProject ? (
        <NewTargetForm
          projectName={activeProject.name}
          projectRoot={activeProject.root}
          modules={modules}
          entryCheck={entryCheck}
          onSubmit={(data) => {
            setIsCreatingTarget(true);
            setCreateTargetError(null);
            rpcClient?.sendAction("addBuildTarget", {
              projectRoot: activeProject.root,
              name: data.name,
              entry: data.entry,
            });
            setShowNewTargetForm(false);
            setIsCreatingTarget(false);
          }}
          onCancel={() => setShowNewTargetForm(false)}
          isCreating={isCreatingTarget}
          error={createTargetError}
        />
      ) : null}

      {showEditTargetForm && activeProject && activeTarget ? (
        <NewTargetForm
          mode="edit"
          projectName={activeProject.name}
          projectRoot={activeProject.root}
          modules={modules}
          initialName={activeTarget.name}
          initialEntry={activeTarget.entry}
          entryCheck={entryCheck}
          onSubmit={(data) => {
            setIsUpdatingTarget(true);
            setEditTargetError(null);
            rpcClient?.sendAction("updateBuildTarget", {
              projectRoot: activeProject.root,
              oldName: activeTarget.name,
              newName: data.name,
              newEntry: data.entry,
            });
            setShowEditTargetForm(false);
            setIsUpdatingTarget(false);
          }}
          onCancel={() => setShowEditTargetForm(false)}
          isCreating={isUpdatingTarget}
          error={editTargetError}
        />
      ) : null}

      <div className="project-section">
        <div className="project-selector-row">
          <span className="section-label">Project</span>
          <ProjectSelector
            projects={projects}
            activeProject={activeProject}
            onSelectProject={onSelectProject}
            onCreateProject={() => setShowNewProjectForm(true)}
          />
          <button
            className="new-project-btn"
            onClick={() => setShowNewProjectForm(true)}
            title="Create new project"
          >
            <Plus size={14} />
          </button>
        </div>
      </div>

      <div className="builds-section">
        <div className="build-targets">
          <span className="section-label">Build</span>
          <TargetSelector
            targets={activeProject?.targets || []}
            activeTargetName={activeTargetName}
            onSelectTarget={onSelectTarget}
            disabled={!activeProject}
          />
          <div className="target-actions">
            <button
              className="icon-action-btn"
              onClick={() => setShowNewTargetForm(true)}
              title="Create new build"
              disabled={!activeProject}
            >
              <Plus size={14} />
            </button>
            <button
              className="icon-action-btn"
              onClick={() => setShowEditTargetForm(true)}
              title="Edit selected build"
              disabled={!activeProject || !activeTarget}
            >
              <Pencil size={13} />
            </button>
            <button
              className="icon-action-btn danger"
              onClick={async () => {
                if (!activeProject || !activeTarget || isDeletingTarget) return;
                if (!window.confirm(`Delete build "${activeTarget.name}"?`)) return;
                setIsDeletingTarget(true);
                setCreateTargetError(null);
                setEditTargetError(null);
                rpcClient?.sendAction("deleteBuildTarget", {
                  projectRoot: activeProject.root,
                  name: activeTarget.name,
                });
                setShowEditTargetForm(false);
                setIsDeletingTarget(false);
              }}
              title="Delete selected build"
              disabled={!activeProject || !activeTarget || isDeletingTarget}
            >
              <Trash2 size={13} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
