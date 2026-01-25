/**
 * ProjectDropdown - Reusable project selector dropdown.
 * Used across BOM, Variables, and Problems panels.
 */

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, ChevronRight, Layers, Search, Check } from 'lucide-react';

export interface ProjectOption {
  id: string;
  name: string;
  root: string;
  targets?: { name: string }[];
  badge?: string;       // Optional badge text (e.g., "no BOM")
  badgeMuted?: boolean; // Whether badge should be muted style
}

interface ProjectDropdownProps {
  projects: ProjectOption[];
  selectedProjectRoot?: string | null;
  selectedTargetName?: string | null;
  onSelectProject: (projectRoot: string | null) => void;
  onSelectTarget?: (projectRoot: string, targetName: string) => void;
  placeholder?: string;
  showAllOption?: boolean;
  allOptionLabel?: string;
  disabled?: boolean;
}

export function ProjectDropdown({
  projects,
  selectedProjectRoot,
  selectedTargetName,
  onSelectProject,
  onSelectTarget,
  placeholder = 'Select project',
  showAllOption = true,
  allOptionLabel = 'All projects',
  disabled = false,
}: ProjectDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setSearchQuery('');
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Auto-focus search input when dropdown opens
  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      setTimeout(() => searchInputRef.current?.focus(), 0);
    }
  }, [isOpen]);

  // Filter projects by search query
  const filteredProjects = searchQuery.trim()
    ? projects.filter(p => p.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : projects;

  const selectedProject = projects.find(p => p.root === selectedProjectRoot);
  const hasProjects = projects.length > 0;
  const selectedLabel = selectedProject
    ? selectedTargetName
      ? `${selectedProject.name} • ${selectedTargetName}`
      : selectedProject.name
    : placeholder;

  const handleSelect = (projectRoot: string | null) => {
    onSelectProject(projectRoot);
    setIsOpen(false);
    setSearchQuery('');
    setExpandedProjects(new Set());
  };

  const toggleOpen = () => {
    if (!disabled && hasProjects) {
      setIsOpen(prev => !prev);
    }
  };

  const toggleProjectTargets = (projectRoot: string) => {
    setExpandedProjects(prev => {
      const next = new Set(prev);
      if (next.has(projectRoot)) {
        next.delete(projectRoot);
      } else {
        next.add(projectRoot);
      }
      return next;
    });
  };

  useEffect(() => {
    if (!selectedProjectRoot) return;
    setExpandedProjects(prev => {
      if (prev.has(selectedProjectRoot)) return prev;
      const next = new Set(prev);
      next.add(selectedProjectRoot);
      return next;
    });
  }, [selectedProjectRoot]);

  useEffect(() => {
    if (!searchQuery) return;
    setExpandedProjects(new Set(filteredProjects.map(p => p.root)));
  }, [searchQuery, filteredProjects]);

  return (
    <div className="install-dropdown project-dropdown" ref={dropdownRef}>
      <button
        className="install-btn"
        onClick={toggleOpen}
        title={selectedLabel}
        disabled={disabled || !hasProjects}
      >
        <Layers size={12} />
        <span>{selectedProject ? selectedLabel : (hasProjects ? (showAllOption ? 'All' : placeholder) : 'No projects')}</span>
      </button>
      <button
        className="install-dropdown-toggle"
        onClick={(e) => {
          e.stopPropagation();
          toggleOpen();
        }}
        title="Change project"
        disabled={disabled || !hasProjects}
      >
        <ChevronDown size={12} />
      </button>
      {isOpen && hasProjects && (
        <div className="install-dropdown-menu project-dropdown-menu">
          <div className="dropdown-header">Select project:</div>
          <div className="dropdown-search">
            <Search size={10} />
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Filter projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          <div className="dropdown-items">
            {/* All option */}
            {showAllOption && (
              <button
                className={`dropdown-item ${!selectedProjectRoot ? 'selected' : ''}`}
                onClick={(e) => {
                  e.stopPropagation();
                  handleSelect(null);
                }}
              >
                <Layers size={12} />
                <span>{allOptionLabel}</span>
                {!selectedProjectRoot && <Check size={12} className="selected-check" />}
              </button>
            )}
            {filteredProjects.map((project) => {
              const hasTargets = Boolean(project.targets && project.targets.length > 0);
              const isExpanded = expandedProjects.has(project.root);
              return (
              <div key={project.root}>
                <button
                  className={`dropdown-item ${project.root === selectedProjectRoot ? 'selected' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectProject(project.root);
                    if (hasTargets && onSelectTarget) {
                      toggleProjectTargets(project.root);
                    } else {
                      setIsOpen(false);
                      setSearchQuery('');
                    }
                  }}
                >
                  {hasTargets && onSelectTarget ? (
                    <span
                      className="project-target-toggle"
                      onClick={(event) => {
                        event.stopPropagation();
                        toggleProjectTargets(project.root);
                      }}
                    >
                      {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    </span>
                  ) : (
                    <span className="project-target-toggle-spacer" />
                  )}
                  <Layers size={12} />
                  <span>{project.name}</span>
                  {project.badge && (
                    <span className={`status-badge ${project.badgeMuted ? 'muted' : ''}`}>
                      {project.badge}
                    </span>
                  )}
                  {project.root === selectedProjectRoot && (
                    <Check size={12} className="selected-check" />
                  )}
                </button>
                {onSelectTarget && hasTargets && isExpanded ? (
                  <div className="project-targets">
                    {project.targets?.map((target) => (
                      <button
                        key={`${project.root}-${target.name}`}
                        className={`dropdown-item target-item ${
                          project.root === selectedProjectRoot &&
                          target.name === selectedTargetName
                            ? 'selected'
                            : ''
                        }`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectTarget(project.root, target.name);
                          setIsOpen(false);
                          setSearchQuery('');
                          setExpandedProjects(new Set());
                        }}
                      >
                        <span>{target.name}</span>
                        {project.root === selectedProjectRoot &&
                          target.name === selectedTargetName && (
                            <Check size={12} className="selected-check" />
                          )}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            )})}
            {filteredProjects.length === 0 && searchQuery && (
              <div className="dropdown-empty">
                No projects match "{searchQuery}"
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
