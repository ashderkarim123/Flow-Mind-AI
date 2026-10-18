import { NextRequest, NextResponse } from 'next/server';
import { nodeDefinitionsService } from '@/lib/firestore';

// GET /api/admin/nodes — public, read-only node catalog (used by the node config modal).
// Node definitions are managed server-side; Firestore rules deny client writes.
export async function GET(request: NextRequest) {
  try {
    const url = new URL(request.url);
    const category = url.searchParams.get('category');
    const isActive = url.searchParams.get('active');
    const search = url.searchParams.get('search');

    const result = await nodeDefinitionsService.getAll({
      category: category || undefined,
      isActive: isActive !== null ? isActive === 'true' : undefined,
      search: search || undefined
    });

    if (result.success) {
      return NextResponse.json({ success: true, nodes: result.data, total: result.total });
    }
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error fetching nodes:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Failed to fetch nodes',
        details: error instanceof Error ? error.message : String(error)
      },
      { status: 500 }
    );
  }
}
