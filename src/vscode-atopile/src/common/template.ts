export function renderTemplate(template: string, values: Record<string, string>): string {
  return template.replace(/\{\{([a-zA-Z0-9_]+)\}\}/g, (_match, key) => values[key] ?? '');
}

export function serializeJsonForHtml(value: unknown): string {
  return JSON.stringify(value).replace(/</g, '\\u003c');
}
