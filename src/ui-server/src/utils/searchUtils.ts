/**
 * Universal search utilities with regex support
 * Can be reused across different search bars in the application
 */

export interface SearchOptions {
  isRegex: boolean;
  caseSensitive?: boolean;
}

export interface SearchResult {
  matches: boolean;
  error?: string;
}

/**
 * Validates if a string is a valid regex pattern
 */
export function isValidRegex(pattern: string): { valid: boolean; error?: string } {
  if (!pattern.trim()) {
    return { valid: true };
  }
  try {
    new RegExp(pattern);
    return { valid: true };
  } catch (e) {
    return { valid: false, error: (e as Error).message };
  }
}

/**
 * Creates a search function that can match text against a pattern
 * Supports both plain text (case-insensitive substring) and regex modes
 */
export function createSearchMatcher(
  pattern: string,
  options: SearchOptions = { isRegex: false }
): (text: string) => SearchResult {
  const trimmed = pattern.trim();

  if (!trimmed) {
    return () => ({ matches: true });
  }

  if (options.isRegex) {
    try {
      const flags = options.caseSensitive ? 'g' : 'gi';
      const regex = new RegExp(trimmed, flags);
      return (text: string) => ({
        matches: regex.test(text),
      });
    } catch (e) {
      const error = (e as Error).message;
      return () => ({ matches: false, error });
    }
  }

  // Plain text search: case-insensitive substring match
  const lowerPattern = trimmed.toLowerCase();
  return (text: string) => ({
    matches: text.toLowerCase().includes(lowerPattern),
  });
}

/**
 * Highlights search matches in text
 * Returns HTML string with matches wrapped in <mark> tags
 *
 * @param text - The text to search in
 * @param pattern - The search pattern
 * @param options - Search options (isRegex, caseSensitive)
 * @returns HTML string with highlighted matches
 */
export function highlightMatches(
  text: string,
  pattern: string,
  options: SearchOptions = { isRegex: false }
): string {
  const trimmed = pattern.trim();

  if (!trimmed) {
    return text;
  }

  try {
    let regex: RegExp;
    const flags = options.caseSensitive ? 'g' : 'gi';

    if (options.isRegex) {
      // For regex mode, use the pattern directly and wrap matches
      // We use String.replace with a function to avoid issues with special replacement patterns
      regex = new RegExp(trimmed, flags);
      return text.replace(regex, (match) => `<mark class="lv-highlight">${match}</mark>`);
    } else {
      // Escape special regex characters for plain text search
      const escaped = trimmed.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      regex = new RegExp(escaped, flags);
      return text.replace(regex, (match) => `<mark class="lv-highlight">${match}</mark>`);
    }
  } catch {
    // If regex is invalid, return text as-is
    return text;
  }
}

/**
 * Filters an array of items based on a search pattern
 *
 * @param items - Array of items to filter
 * @param pattern - Search pattern
 * @param getText - Function to extract searchable text from an item
 * @param options - Search options
 * @returns Filtered array
 */
export function filterBySearch<T>(
  items: T[],
  pattern: string,
  getText: (item: T) => string,
  options: SearchOptions = { isRegex: false }
): T[] {
  const matcher = createSearchMatcher(pattern, options);
  return items.filter(item => matcher(getText(item)).matches);
}
