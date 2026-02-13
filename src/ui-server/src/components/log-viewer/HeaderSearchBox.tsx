export interface HeaderSearchBoxProps {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  title?: string;
  error?: string;
  caseSensitive?: boolean;
  onToggleCaseSensitive?: () => void;
  regex?: boolean;
  onToggleRegex?: () => void;
  inputClassName?: string;
  wrapperClassName?: string;
}

export function HeaderSearchBox({
  value,
  onChange,
  placeholder,
  title,
  error,
  caseSensitive,
  onToggleCaseSensitive,
  regex,
  onToggleRegex,
  inputClassName = '',
  wrapperClassName = '',
}: HeaderSearchBoxProps) {
  const hasCaseToggle = typeof caseSensitive === 'boolean' && !!onToggleCaseSensitive;
  const hasRegexToggle = typeof regex === 'boolean' && !!onToggleRegex;
  const hasControls = hasCaseToggle || hasRegexToggle;

  if (!hasControls) {
    return (
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={`lv-col-search ${inputClassName}`.trim()}
        title={title ?? error ?? ''}
      />
    );
  }

  return (
    <div
      className={[
        'lv-search-wrapper',
        error ? 'lv-search-error' : '',
        wrapperClassName,
      ].filter(Boolean).join(' ')}
    >
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={`lv-col-search ${inputClassName}`.trim()}
        title={title ?? error ?? ''}
      />
      {hasCaseToggle && (
        <button
          className={`lv-search-toggle ${caseSensitive ? 'active' : ''}`}
          onClick={onToggleCaseSensitive}
          title={caseSensitive ? 'Case sensitive' : 'Case insensitive'}
        >
          Aa
        </button>
      )}
      {hasRegexToggle && (
        <button
          className={`lv-search-toggle lv-search-toggle-last ${regex ? 'active' : ''}`}
          onClick={onToggleRegex}
          title={regex ? 'Regex enabled' : 'Enable regex'}
        >
          .*
        </button>
      )}
    </div>
  );
}
