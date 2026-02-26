import { useState, useRef, useEffect, useMemo } from "react";
import { FolderOpen, Target, ChevronDown, Check, Plus } from "lucide-react";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "../shared/components/Select";
import { Button } from "../shared/components/Button";
import "./ProjectTargetSelector.css";

interface Project {
  root: string;
  name: string;
  targets: string[];
}

interface ProjectTargetSelectorProps {
  projects: Project[];
  selectedProject: string | null;
  onSelectProject: (root: string) => void;
  targets: string[];
  selectedTarget: string | null;
  onSelectTarget: (target: string) => void;
}

export function ProjectTargetSelector({
  projects,
  selectedProject,
  onSelectProject,
  targets,
  selectedTarget,
  onSelectTarget,
}: ProjectTargetSelectorProps) {
  const targetItems = useMemo(
    () => targets.map((t) => ({ label: t, value: t })),
    [targets],
  );

  const targetDisabled = !selectedProject || targets.length === 0;
  const targetPlaceholder = !selectedProject
    ? "Select a project"
    : targets.length === 0
      ? "No builds defined"
      : "Select target...";

  return (
    <div className="selector-grid">
      <div className="project-section">
        <div className="project-selector-row">
          <span className="section-label">Project</span>
          <ProjectCombobox
            projects={projects}
            selectedProject={selectedProject}
            onSelect={onSelectProject}
          />
          <Button
            variant="ghost"
            size="icon"
            className="new-project-btn"
            title="Create new project"
            onClick={() => console.log("Create project (placeholder)")}
          >
            <Plus size={14} />
          </Button>
        </div>
      </div>

      <div className="builds-section">
        <div className="build-targets">
          <span className="section-label">Build</span>
          <Select
            className="inline-select"
            items={targetItems}
            value={selectedTarget}
            onValueChange={(v) => v && onSelectTarget(v)}
            disabled={targetDisabled}
          >
            <SelectTrigger>
              <Target size={12} className="target-trigger-icon" />
              <SelectValue placeholder={targetPlaceholder} />
            </SelectTrigger>
            <SelectContent>
              {targetItems.map((item) => (
                <SelectItem key={item.value} value={item.value}>
                  <Target size={12} className="target-item-icon" />
                  {item.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
}

/* ---- Project Combobox (standalone, with search) ---- */

function ProjectCombobox({
  projects,
  selectedProject,
  onSelect,
}: {
  projects: Project[];
  selectedProject: string | null;
  onSelect: (root: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = useMemo(() => {
    if (!query) return projects;
    const q = query.toLowerCase();
    return projects.filter(
      (p) => p.name.toLowerCase().includes(q) || p.root.toLowerCase().includes(q),
    );
  }, [projects, query]);

  const selectedName = projects.find((p) => p.root === selectedProject)?.name;

  const close = () => { setOpen(false); setQuery(""); setHighlight(0); };

  // Outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) close();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  });

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open) {
      if (e.key === "ArrowDown" || e.key === "Enter") { e.preventDefault(); setOpen(true); }
      return;
    }
    switch (e.key) {
      case "ArrowDown": e.preventDefault(); setHighlight((i) => Math.min(i + 1, filtered.length - 1)); break;
      case "ArrowUp":   e.preventDefault(); setHighlight((i) => Math.max(i - 1, 0)); break;
      case "Enter":     e.preventDefault(); if (filtered[highlight]) { onSelect(filtered[highlight].root); close(); } break;
      case "Escape":    e.preventDefault(); close(); break;
    }
  };

  return (
    <div className="project-combobox" ref={rootRef}>
      <div className={`combobox-input-wrapper${open ? " open" : ""}`} onClick={() => { setOpen(true); inputRef.current?.focus(); }}>
        <FolderOpen className="combobox-icon" size={12} />
        <input
          ref={inputRef}
          className="combobox-input"
          value={open ? query : selectedName ?? ""}
          placeholder={projects.length === 0 ? "No projects found" : open ? "Search projects..." : "Select project..."}
          onChange={(e) => { setQuery(e.target.value); setHighlight(0); }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          readOnly={!open}
        />
        <button className="combobox-toggle" onClick={(e) => { e.stopPropagation(); open ? close() : setOpen(true); }} tabIndex={-1}>
          <ChevronDown size={12} className={`chevron${open ? " open" : ""}`} />
        </button>
      </div>

      {open && (
        <div className="combobox-dropdown">
          {filtered.length === 0 ? (
            <div className="combobox-empty">No matching projects</div>
          ) : (
            filtered.map((p, i) => (
              <button
                key={p.root}
                className={`combobox-option${i === highlight ? " highlighted" : ""}${p.root === selectedProject ? " active" : ""}`}
                onClick={() => { onSelect(p.root); close(); }}
                onMouseEnter={() => setHighlight(i)}
              >
                <FolderOpen size={12} className="option-icon" />
                <span className="combobox-option-name">{p.name}</span>
                <span className="combobox-option-path">{p.root}</span>
                {p.root === selectedProject && <Check size={12} className="check-icon" />}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
