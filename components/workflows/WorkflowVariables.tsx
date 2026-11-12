'use client';

import { useEffect, useState } from 'react';
import { Braces, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { parseVariableValue, variableNameProblem, variableValueText } from '@/lib/workflow/variables';

interface Row { name: string; text: string }

const toRows = (value: Record<string, any>): Row[] => Object.entries(value).map(([name, v]) => ({ name, text: variableValueText(v) }));

/** Define values once and use them in any step as {{$vars.name}} (saved with the workflow). */
export default function WorkflowVariables({ open, value, onSave, onClose }: {
  open: boolean;
  value: Record<string, any>;
  onSave: (variables: Record<string, any>) => void;
  onClose: () => void;
}) {
  const [rows, setRows] = useState<Row[]>([]);
  useEffect(() => { if (open) setRows(toRows(value)); }, [open, value]);

  const problems = rows.map((r, i) => variableNameProblem(r.name, rows.filter((_, j) => j !== i).map((o) => o.name)));
  const valid = rows.every((r, i) => r.name === '' && r.text === '' ? true : !problems[i]);
  const update = (i: number, patch: Partial<Row>) => setRows((prev) => prev.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  const save = () => {
    const variables: Record<string, any> = {};
    for (const r of rows) if (r.name.trim()) variables[r.name.trim()] = parseVariableValue(r.text);
    onSave(variables);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-xl border-slate-700 bg-[#120d09] text-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Braces className="h-5 w-5 text-[#1D4ED8]" />Workflow variables</DialogTitle>
          <DialogDescription className="text-gray-400">
            Set a value once and use it in any step as <code className="text-gray-200">{'{{$vars.name}}'}</code>. Numbers, true/false and JSON keep their type.
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[50vh] space-y-3 overflow-y-auto py-2">
          {rows.length === 0 && <p className="text-sm text-gray-500">No variables yet. Add one, for example <code>customer_name</code> = <code>Acme Ltd</code>.</p>}
          {rows.map((r, i) => (
            <div key={i}>
              <div className="flex items-center gap-2">
                <Input value={r.name} placeholder="name" onChange={(e) => update(i, { name: e.target.value })}
                  className="w-2/5 border-slate-700 bg-slate-800 font-mono text-white" aria-label={`Variable ${i + 1} name`} />
                <Input value={r.text} placeholder="value" onChange={(e) => update(i, { text: e.target.value })}
                  className="flex-1 border-slate-700 bg-slate-800 text-white" aria-label={`Variable ${i + 1} value`} />
                <Button type="button" variant="ghost" size="sm" onClick={() => setRows((prev) => prev.filter((_, j) => j !== i))}
                  className="text-gray-400 hover:text-red-400" aria-label={`Remove variable ${i + 1}`}><Trash2 className="h-4 w-4" /></Button>
              </div>
              {problems[i] && (r.name !== '' || r.text !== '') && <p className="mt-1 text-xs text-red-400">{problems[i]}</p>}
            </div>
          ))}
        </div>

        <Button type="button" variant="outline" onClick={() => setRows((prev) => [...prev, { name: '', text: '' }])}
          className="w-full border-slate-700 text-gray-300 hover:bg-slate-800"><Plus className="mr-2 h-4 w-4" />Add variable</Button>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} className="border-slate-700 text-gray-300 hover:bg-slate-800">Cancel</Button>
          <Button onClick={save} disabled={!valid} className="bg-[#1D4ED8] text-white hover:bg-[#1E40AF]">Save variables</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
