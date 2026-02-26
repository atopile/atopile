import { Package } from "lucide-react";
import { EmptyState } from "../shared/components";

export function PackagesPanel() {
  return (
    <EmptyState
      icon={<Package size={24} />}
      title="Package browser coming soon"
    />
  );
}
