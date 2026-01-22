/**
 * Name validation utilities for projects and builds.
 *
 * Valid names:
 * - Lowercase letters, numbers, hyphens, underscores
 * - Must start with a letter
 * - No spaces or special characters
 * - Prefer hyphen format (project-name) over underscore (project_name)
 */

export interface ValidationResult {
  isValid: boolean;
  error?: string;
  suggestion?: string;
}

// Pattern: lowercase letters, numbers, hyphens, underscores. Must start with a letter.
const VALID_NAME_PATTERN = /^[a-z][a-z0-9_-]*$/;

/**
 * Validate a project or build name.
 */
export function validateName(name: string): ValidationResult {
  if (!name || name.trim() === '') {
    return {
      isValid: false,
      error: 'Name cannot be empty',
      suggestion: undefined
    };
  }

  const trimmed = name.trim();

  // Check if already valid
  if (VALID_NAME_PATTERN.test(trimmed)) {
    return { isValid: true };
  }

  // Generate suggestion
  const suggestion = sanitizeName(trimmed);

  // Determine error message
  let error = 'Invalid name';

  if (/\s/.test(trimmed)) {
    error = 'Name cannot contain spaces';
  } else if (/^[0-9]/.test(trimmed)) {
    error = 'Name must start with a letter';
  } else if (/[A-Z]/.test(trimmed)) {
    error = 'Name must be lowercase';
  } else if (/[^a-z0-9_-]/.test(trimmed)) {
    error = 'Name contains invalid characters';
  }

  return {
    isValid: false,
    error,
    suggestion: suggestion !== trimmed ? suggestion : undefined
  };
}

/**
 * Sanitize a name to meet naming standards.
 * Converts to lowercase, replaces spaces and invalid chars with hyphens,
 * ensures it starts with a letter.
 */
export function sanitizeName(name: string): string {
  let sanitized = name
    // Convert to lowercase
    .toLowerCase()
    // Replace spaces and underscores with hyphens (prefer hyphen format)
    .replace(/[\s_]+/g, '-')
    // Remove any characters that aren't lowercase letters, numbers, or hyphens
    .replace(/[^a-z0-9-]/g, '')
    // Replace multiple consecutive hyphens with single hyphen
    .replace(/-+/g, '-')
    // Remove leading/trailing hyphens
    .replace(/^-+|-+$/g, '');

  // If name starts with a number, prefix with 'project-' or similar
  if (/^[0-9]/.test(sanitized)) {
    sanitized = 'project-' + sanitized;
  }

  // If empty after sanitization, provide a default
  if (!sanitized) {
    sanitized = 'new-project';
  }

  return sanitized;
}

/**
 * Check if a name is valid without generating suggestions.
 */
export function isValidName(name: string): boolean {
  return VALID_NAME_PATTERN.test(name.trim());
}
