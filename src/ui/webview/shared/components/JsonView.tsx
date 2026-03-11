import { useState } from "react";
import "./JsonView.css";

function isExpandable(value: unknown): boolean {
  if (Array.isArray(value)) return value.length > 0;
  if (value !== null && typeof value === "object") return Object.keys(value).length > 0;
  return false;
}

function Primitive({ value }: { value: unknown }) {
  if (value === null || value === undefined)
    return <span className="json-null">{String(value)}</span>;
  if (typeof value === "boolean")
    return <span className="json-bool">{String(value)}</span>;
  if (typeof value === "number")
    return <span className="json-number">{value}</span>;
  if (typeof value === "string")
    return <span className="json-string">"{value}"</span>;
  if (Array.isArray(value) && value.length === 0)
    return <span className="json-bracket">[]</span>;
  if (typeof value === "object")
    return <span className="json-bracket">{"{}"}</span>;
  return <span>{String(value)}</span>;
}

function Entry({ name, value }: { name: string; value: unknown }) {
  const [open, setOpen] = useState(false);
  const expandable = isExpandable(value);

  return (
    <li className="json-entry">
      {expandable
        ? <span className="json-chevron" onClick={() => setOpen(!open)}>{open ? "\u25BE" : "\u25B8"}</span>
        : <span className="json-chevron-spacer" />}
      <span className="json-key">{name}</span>:{" "}
      {expandable
        ? <Expandable value={value!} open={open} />
        : <Primitive value={value} />}
    </li>
  );
}

function Expandable({ value, open }: { value: object; open: boolean }) {
  const isArray = Array.isArray(value);
  const entries: [string, unknown][] = isArray
    ? value.map((v, i) => [String(i), v])
    : Object.entries(value);
  const [ob, cb] = isArray ? ["[", "]"] : ["{", "}"];

  if (!open) {
    return (
      <span>
        <span className="json-bracket">{ob}</span>{" "}
        <span className="json-ellipsis">{entries.length} items</span>{" "}
        <span className="json-bracket">{cb}</span>
      </span>
    );
  }

  return (
    <span>
      <span className="json-bracket">{ob}</span>
      <ul className="json-entries">
        {entries.map(([key, val]) => (
          <Entry key={key} name={key} value={val} />
        ))}
      </ul>
      <span className="json-bracket">{cb}</span>
    </span>
  );
}

export function JsonView({ value, defaultOpen = false }: { value: unknown; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);

  if (!isExpandable(value)) return <Primitive value={value} />;

  const isArray = Array.isArray(value);
  const entries: [string, unknown][] = isArray
    ? value.map((v, i) => [String(i), v])
    : Object.entries(value!);
  const [ob, cb] = isArray ? ["[", "]"] : ["{", "}"];

  return (
    <span className="json-tree">
      <span className="json-chevron" onClick={() => setOpen(!open)}>{open ? "\u25BE" : "\u25B8"}</span>
      {open ? (
        <>
          <span className="json-bracket">{ob}</span>
          <ul className="json-entries">
            {entries.map(([key, val]) => (
              <Entry key={key} name={key} value={val} />
            ))}
          </ul>
          <span className="json-bracket">{cb}</span>
        </>
      ) : (
        <span>
          <span className="json-bracket">{ob}</span>{" "}
          <span className="json-ellipsis">{entries.length} items</span>{" "}
          <span className="json-bracket">{cb}</span>
        </span>
      )}
    </span>
  );
}
