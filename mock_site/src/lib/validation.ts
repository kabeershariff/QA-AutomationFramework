import type {
  ScenarioMeta,
  SubmissionFileMetadata,
  SubmissionValidationResult,
} from '../types/scenario';

const FILE_FIELDS = new Set(['resume', 'coverLetter']);
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MAX_EMAIL_LENGTH = 254;
const MAX_EMAIL_LOCAL_PART_LENGTH = 64;

function isValidEmail(value: string): boolean {
  const email = value.trim();
  if (email.length > MAX_EMAIL_LENGTH) return false;
  if (!EMAIL_PATTERN.test(email)) return false;
  return email.split('@')[0].length <= MAX_EMAIL_LOCAL_PART_LENGTH;
}

export function isFileField(fieldName: string): boolean {
  return FILE_FIELDS.has(fieldName);
}

export interface ValidationInput {
  fields: Record<string, string>;
  files: SubmissionFileMetadata[];
}

export function validateRequired(
  meta: ScenarioMeta,
  input: ValidationInput,
): SubmissionValidationResult {
  const missing: string[] = [];
  const warnings: string[] = [];

  for (const expected of meta.expectedFields) {
    if (!expected.required) continue;

    if (isFileField(expected.name)) {
      const has = input.files.some((f) => f.field === expected.name);
      if (!has) missing.push(expected.name);
      continue;
    }

    const value = input.fields[expected.name];
    if (value === undefined || value === null || `${value}`.trim() === '') {
      missing.push(expected.name);
    } else if (expected.name === 'email' && !isValidEmail(`${value}`)) {
      missing.push(expected.name);
    }
  }

  return {
    passed: missing.length === 0,
    missingRequiredFields: missing,
    warnings,
  };
}
