import { redirect } from 'next/navigation';

// /workflows/<id> was a placeholder page; open the workflow in the real editor instead.
export default async function WorkflowRedirect({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  redirect(`/workflows/new?id=${encodeURIComponent(id)}`);
}
