interface StatCardProps {
  title: string;
  value: string;
  caption: string;
  tone?: "default" | "success" | "warning";
}

export function StatCard({
  title,
  value,
  caption,
  tone = "default"
}: StatCardProps): JSX.Element {
  return (
    <article className={`stat-card card tone-${tone}`}>
      <p className="stat-title">{title}</p>
      <p className="stat-value">{value}</p>
      <p className="stat-caption">{caption}</p>
    </article>
  );
}
