import { Cpu } from "lucide-react";
import { EmptyState } from "../shared/components";

export function PartsPanel() {
  return (
    <EmptyState
      icon={<Cpu size={24} />}
      title="Parts search coming soon"
    />
  );
}
