import { Files } from "lucide-react";
import { EmptyState } from "../shared/components";

export function FilesPanel() {
  return (
    <EmptyState
      icon={<Files size={24} />}
      title="File explorer coming soon"
    />
  );
}
