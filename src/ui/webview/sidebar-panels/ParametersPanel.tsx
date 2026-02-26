import { SlidersHorizontal } from "lucide-react";
import { EmptyState } from "../shared/components";

export function ParametersPanel() {
  return (
    <EmptyState
      icon={<SlidersHorizontal size={24} />}
      title="Parameters coming soon"
    />
  );
}
