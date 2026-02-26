import { GitBranch } from "lucide-react";
import { EmptyState } from "../shared/components";

export function StructurePanel() {
  return (
    <EmptyState
      icon={<GitBranch size={24} />}
      title="Structure view coming soon"
    />
  );
}
