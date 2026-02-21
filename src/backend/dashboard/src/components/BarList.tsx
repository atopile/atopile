interface BarItem {
  label: string;
  count: number;
  subtitle?: string;
}

interface BarListProps {
  title: string;
  items: BarItem[];
  emptyLabel: string;
  className?: string;
}

const countFormatter = new Intl.NumberFormat("en-US");

export function BarList({
  title,
  items,
  emptyLabel,
  className
}: BarListProps): JSX.Element {
  const maxCount = Math.max(...items.map((item) => item.count), 1);
  const classes = ["card", "bar-list", className].filter(Boolean).join(" ");

  return (
    <section className={classes} aria-label={title}>
      <h3>{title}</h3>
      {items.length === 0 ? (
        <div className="empty-state">{emptyLabel}</div>
      ) : (
        <ul>
          {items.map((item) => {
            const width = Math.max((item.count / maxCount) * 100, 4);
            return (
              <li key={`${item.label}-${item.subtitle ?? ""}`}>
                <div className="bar-list-header">
                  <span className="bar-label" title={item.label}>
                    {item.label}
                  </span>
                  <span className="bar-count">{countFormatter.format(item.count)}</span>
                </div>
                <div className="bar-track" aria-hidden="true">
                  <div className="bar-fill" style={{ width: `${width}%` }} />
                </div>
                {item.subtitle ? <p className="bar-subtitle">{item.subtitle}</p> : null}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
