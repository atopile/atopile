import { Library } from "lucide-react";
import { EmptyState } from "../shared/components";

export function LibraryPanel() {
  return (
    <EmptyState
      icon={<Library size={24} />}
      title="Standard library coming soon"
    />
  );
}
