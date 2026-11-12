import type { NodeField } from './NodeDefinitions';

/** Whether a field is shown, given the node's current settings (see NodeField.showWhen). */
export function isFieldShown(field: NodeField, config: Record<string, any>): boolean {
  const rule = field.showWhen;
  if (!rule) return true;
  const current = config[rule.field];
  return rule.in.includes(String(current === undefined || current === null || current === '' ? rule.default ?? '' : current));
}

/** The other settings that choosing `value` on a select fills in (see NodeField.presets). */
export function presetValues(field: NodeField, value: string): Record<string, string | number | boolean> {
  return field.presets?.[value] ?? {};
}
