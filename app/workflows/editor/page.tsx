import { redirect } from 'next/navigation';

// The full editor lives at /workflows/new (it opens a saved workflow via ?id=).
// This route used to render an unfinished prototype canvas, so old links are forwarded.
export default async function WorkflowEditorRedirect({ searchParams }: { searchParams: Promise<{ id?: string }> }) {
  const { id } = await searchParams;
  redirect(id ? `/workflows/new?id=${encodeURIComponent(id)}` : '/workflows/new');
}
