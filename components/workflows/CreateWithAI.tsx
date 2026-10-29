'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AlertTriangle, ArrowRight, CheckCircle2, ClipboardList, Loader2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { aiToolsApi, AiStatus, GeneratedWorkflow, saveGeneratedWorkflow } from '@/lib/api/aiTools';

const EXAMPLES = [
  'Every morning at 9, summarise the latest news about AI and email it to me',
  'When a webhook arrives, ask AI if the message is urgent and tell me on Telegram if it is',
  'Every hour, fetch a web page and let me know in Slack if it mentions "sale"',
];

// Plain-language names for the technical node types a non-technical person might see
const FRIENDLY_TYPES: Record<string, string> = {
  LocalLLM: 'Local AI', OpenAI: 'AI (OpenAI)', ClaudeAI: 'AI (Claude)', Gemini: 'AI (Gemini)', Groq: 'AI (Groq)',
  MCPTool: 'Connected tool', HttpRequest: 'Web request', SendEmail: 'Email', SlackMessage: 'Slack',
  TelegramSend: 'Telegram', IfCondition: 'Decision', ManualTrigger: 'Run button', Schedule: 'Timer',
  Webhook: 'Incoming webhook', SetVariable: 'Remember a value', DataFormatter: 'Format data', JsonParser: 'Read JSON',
  GoogleSheets: 'Google Sheets', GoogleDrive: 'Google Drive', Delay: 'Wait',
};
const friendlyType = (type: string) => FRIENDLY_TYPES[type] ?? type.replace(/([a-z])([A-Z])/g, '$1 $2');

export function CreateWithAI({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [status, setStatus] = useState<AiStatus | null>(null);
  const [busy, setBusy] = useState<'generating' | 'saving' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<GeneratedWorkflow | null>(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
    aiToolsApi.status().then(setStatus).catch(() => setStatus(null));
  }, [open]);

  const reset = () => {
    setDraft(null);
    setError(null);
    setBusy(null);
  };

  const generate = async () => {
    setBusy('generating');
    setError(null);
    try {
      setDraft(await aiToolsApi.generateWorkflow(prompt));
    } catch (e: any) {
      setError(e.message || 'Something went wrong. Please try again.');
    } finally {
      setBusy(null);
    }
  };

  const create = async () => {
    if (!draft) return;
    setBusy('saving');
    setError(null);
    try {
      const id = await saveGeneratedWorkflow(draft);
      onOpenChange(false);
      router.push(`/workflows/new?id=${encodeURIComponent(id)}`);
    } catch (e: any) {
      setError(e.message || 'Could not save the workflow.');
      setBusy(null);
    }
  };

  const notReady = status && !status.assistant.ready;

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!busy) { onOpenChange(next); if (!next) reset(); } }}>
      <DialogContent className="max-w-2xl bg-[#120d09] border-white/10 text-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <Sparkles className="w-5 h-5 text-blue-400" /> Create a workflow with AI
          </DialogTitle>
          <DialogDescription className="text-white/60">
            Describe what you want in your own words. You&apos;ll see the plan before anything is saved.
          </DialogDescription>
        </DialogHeader>

        {notReady && (
          <div className="flex gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <div>
              {status!.assistant.problem || 'The AI assistant is not ready yet.'}{' '}
              <Link href="/connections" className="underline" onClick={() => onOpenChange(false)}>Open Connections</Link>
            </div>
          </div>
        )}

        {!draft ? (
          <div className="space-y-3">
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={4}
              autoFocus
              disabled={busy !== null}
              placeholder="e.g. Every Monday at 8am, read our sales sheet and send me a summary on Telegram"
              className="bg-white/5 border-white/10 text-white"
            />
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((example) => (
                <button
                  key={example}
                  type="button"
                  disabled={busy !== null}
                  onClick={() => setPrompt(example)}
                  className="text-xs text-left rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-white/60 hover:text-white hover:border-white/25 transition-colors"
                >
                  {example}
                </button>
              ))}
            </div>
            {busy === 'generating' && (
              <p className="flex items-center gap-2 text-sm text-white/60">
                <Loader2 className="w-4 h-4 animate-spin" />
                Designing your workflow… {status?.assistant.provider === 'local' ? 'a local model can take a minute or two.' : ''}
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold">{draft.name}</h3>
              {draft.description && <p className="text-sm text-white/60">{draft.description}</p>}
            </div>

            <ol className="flex flex-wrap items-center gap-2">
              {draft.steps.map((step, index) => (
                <li key={step.id} className="flex items-center gap-2">
                  {index > 0 && <ArrowRight className="w-4 h-4 text-white/30" />}
                  <span className="rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 text-sm">
                    <span className="text-white">{step.name}</span>
                    <span className="ml-2 text-xs text-white/40">{friendlyType(step.type)}</span>
                  </span>
                </li>
              ))}
            </ol>

            {draft.todo.length > 0 && (
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 text-sm">
                <p className="flex items-center gap-2 font-medium text-white"><ClipboardList className="w-4 h-4 text-blue-400" /> Still to fill in after it opens</p>
                <ul className="mt-1 list-disc pl-6 text-white/70">
                  {draft.todo.map((item) => <li key={`${item.nodeId}-${item.field}`}>{item.nodeName}: <em>{item.label}</em></li>)}
                </ul>
              </div>
            )}

            {draft.warnings.length > 0 && (
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
                <p className="flex items-center gap-2 font-medium"><AlertTriangle className="w-4 h-4" /> Please double-check</p>
                <ul className="mt-1 list-disc pl-6">{draft.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
              </div>
            )}

            <p className="flex items-center gap-2 text-xs text-white/40">
              <CheckCircle2 className="w-3.5 h-3.5" /> Drafted by {draft.model}. You can change anything in the editor.
            </p>
          </div>
        )}

        {error && <p className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</p>}

        <DialogFooter className="gap-2">
          {draft ? (
            <>
              <Button variant="ghost" className="text-white/70" onClick={reset} disabled={busy !== null}>Try again</Button>
              <Button className="bg-[#1D4ED8] hover:bg-[#1E40AF] text-white" onClick={create} disabled={busy !== null}>
                {busy === 'saving' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                Create &amp; open in editor
              </Button>
            </>
          ) : (
            <Button className="bg-[#1D4ED8] hover:bg-[#1E40AF] text-white" onClick={generate}
              disabled={busy !== null || prompt.trim().length < 8 || !!notReady}>
              {busy === 'generating' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
              Design my workflow
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default CreateWithAI;
