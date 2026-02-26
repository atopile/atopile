import { ClipboardList } from "lucide-react";
import { EmptyState } from "../shared/components";

export function BOMPanel() {
  return (
    <EmptyState
      icon={<ClipboardList size={24} />}
      title="Bill of materials coming soon"
    />
  );
}
