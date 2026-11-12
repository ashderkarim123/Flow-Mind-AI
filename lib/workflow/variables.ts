/** Workflow variables: values every step can read as {{$vars.name}} (saved with the workflow). */

const NAME = /^[A-Za-z_][A-Za-z0-9_]*$/;

/** Why a variable name cannot be used, or null if it is fine. `others` are the names already taken. */
export function variableNameProblem(name: string, others: string[]): string | null {
  if (!name.trim()) return 'Give the variable a name';
  if (!NAME.test(name)) return 'Use letters, numbers and underscores, and do not start with a number';
  if (others.includes(name)) return 'Another variable already has this name';
  return null;
}

/** Text typed into the value box -> the value stored: true/false, numbers and JSON keep their type, anything else stays text. */
export function parseVariableValue(text: string): string | number | boolean | object {
  const t = text.trim();
  if (t === 'true') return true;
  if (t === 'false') return false;
  if (t !== '' && Number.isFinite(Number(t))) return Number(t);
  if ((t.startsWith('{') && t.endsWith('}')) || (t.startsWith('[') && t.endsWith(']'))) {
    try {
      return JSON.parse(t);
    } catch {
      /* not JSON after all: keep the text */
    }
  }
  return text;
}

/** A stored value -> the text shown in the value box. */
export function variableValueText(value: unknown): string {
  return typeof value === 'string' ? value : JSON.stringify(value);
}

/** The shape the server stores a variable in: a type and a string, number or boolean value (JSON travels as text). */
export type BackendVariable = { type: 'string' | 'number' | 'boolean' | 'json'; value: string | number | boolean };

/** Plain variables ({ name: value }) -> what the server accepts. */
export function toBackendVariables(plain: Record<string, any>): Record<string, BackendVariable> {
  const out: Record<string, BackendVariable> = {};
  for (const [name, v] of Object.entries(plain || {})) {
    if (typeof v === 'number') out[name] = { type: 'number', value: v };
    else if (typeof v === 'boolean') out[name] = { type: 'boolean', value: v };
    else if (v !== null && typeof v === 'object') out[name] = { type: 'json', value: JSON.stringify(v) };
    else out[name] = { type: 'string', value: v == null ? '' : String(v) };
  }
  return out;
}

/** What the server returns -> plain variables. Values saved in the plain form before are accepted too; secrets are not shown. */
export function fromBackendVariables(typed: Record<string, any> | null | undefined): Record<string, any> {
  const out: Record<string, any> = {};
  for (const [name, item] of Object.entries(typed || {})) {
    if (item !== null && typeof item === 'object' && !Array.isArray(item) && 'type' in item && Object.keys(item).every((k) => ['type', 'value', 'secretRef', 'secret_ref', 'description'].includes(k))) {
      if (item.type === 'secret') continue;
      if (item.type === 'json' && typeof item.value === 'string') {
        try { out[name] = JSON.parse(item.value); continue; } catch { /* keep the text */ }
      }
      out[name] = item.value;
    } else {
      out[name] = item;
    }
  }
  return out;
}
