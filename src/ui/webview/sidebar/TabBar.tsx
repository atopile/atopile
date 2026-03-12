import { useRef, useEffect, useState } from "react";
import {
  Files,
  Package,
  Cpu,
  Library,
  GitBranch,
  SlidersHorizontal,
  ClipboardList,
} from "lucide-react";
import "./TabBar.css";

export type TabId =
  | "files"
  | "packages"
  | "parts"
  | "library"
  | "structure"
  | "parameters"
  | "bom";

interface Tab {
  id: TabId;
  label: string;
  tooltip: string;
  icon: React.ReactNode;
}

const TABS: Tab[] = [
  { id: "files", label: "Files", tooltip: "Files", icon: <Files size={14} /> },
  { id: "packages", label: "Packages", tooltip: "Packages", icon: <Package size={14} /> },
  { id: "parts", label: "Parts", tooltip: "Parts", icon: <Cpu size={14} /> },
  { id: "library", label: "Lib", tooltip: "Standard Library", icon: <Library size={14} /> },
  { id: "structure", label: "Struct", tooltip: "Structure", icon: <GitBranch size={14} /> },
  { id: "parameters", label: "Params", tooltip: "Parameters", icon: <SlidersHorizontal size={14} /> },
  { id: "bom", label: "BOM", tooltip: "Bill of Materials", icon: <ClipboardList size={14} /> },
];

interface TabBarProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

export function TabBar({ activeTab, onTabChange }: TabBarProps) {
  const barRef = useRef<HTMLDivElement>(null);
  const [compact, setCompact] = useState(false);

  useEffect(() => {
    const el = barRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setCompact(entry.contentRect.width < 450);
      }
    });

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={barRef} className={`tab-bar${compact ? " compact" : ""}`}>
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={`tab-button${activeTab === tab.id ? " active" : ""}`}
          data-tooltip={tab.tooltip}
          onClick={() => onTabChange(tab.id)}
        >
          {tab.icon}
          <span className="tab-label">{tab.label}</span>
        </button>
      ))}
    </div>
  );
}
