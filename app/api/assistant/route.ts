import { NextRequest, NextResponse } from "next/server";

const apiKey = process.env.OPENROUTER_API_KEY;
const OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";
// Using a capable, fast model available on OpenRouter
const ASSISTANT_MODEL = "google/gemini-2.5-flash";
const BACKEND_API = process.env.NEXT_PUBLIC_BACKEND_API_URL || "http://localhost:8000";

// Cache the node catalog for 5 minutes so we don't hit the backend on every message
let _nodeCatalogCache: { data: any; ts: number } = { data: null, ts: 0 };
const CATALOG_TTL_MS = 5 * 60 * 1000;

async function getNodeCatalog(): Promise<string> {
  const now = Date.now();
  if (_nodeCatalogCache.data && now - _nodeCatalogCache.ts < CATALOG_TTL_MS) {
    return _nodeCatalogCache.data;
  }
  try {
    const res = await fetch(`${BACKEND_API}/api/v1/nodes`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`nodes API ${res.status}`);
    const nodes: any[] = await res.json();

    // Build a compact, LLM-readable summary of every node's inputs and outputs
    const summary = nodes.map((n: any) => {
      const params = (n.parameters || [])
        .map((p: any) => `    - ${p.name} (${p.type}${p.required ? ", required" : ""}): ${p.description || ""}`)
        .join("\n");
      const outputs = (n.outputs || [])
        .map((o: any) => `    - {{$node.<nodeId>.${o.name}}} → ${o.display_name} (${o.type}): ${o.description || ""}`)
        .join("\n");
      return [
        `## ${n.type} [${n.category}]`,
        `${n.description}`,
        params ? `  Inputs:\n${params}` : "  Inputs: none",
        outputs ? `  Outputs (use these in variable references):\n${outputs}` : "  Outputs: none",
      ].join("\n");
    }).join("\n\n");

    const catalog = `NEXAGENT NODE CATALOG (authoritative — always use these exact output field names in {{$node.X.field}} references):\n\n${summary}`;
    _nodeCatalogCache = { data: catalog, ts: now };
    return catalog;
  } catch {
    // Backend not reachable — return empty string, don't fail the chat
    return "";
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const userQuestion: string = body.question || "";
    const sessionId: string = body.session_id || "";
    const currentState: any = body.current_state || null;

    // Enrich system prompt with live node catalog
    const catalog = await getNodeCatalog();

    const systemPrompt = [
      "You are FlowMind AI Workflow Assistant — an expert at designing automation workflows.",
      "Help users build workflows using nodes, edges, and triggers.",
      "When suggesting variable references, always use the exact output field names from the node catalog below.",
      "Keep answers concise, practical, and actionable. Use bullet points where helpful.",
      catalog ? `\n${catalog}` : "",
      currentState ? `\nCurrent workflow canvas state:\n${JSON.stringify(currentState, null, 2)}` : "",
    ].filter(Boolean).join("\n");

    const response = await fetch(`${OPENROUTER_BASE_URL}/chat/completions`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "HTTP-Referer": process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
        "X-Title": "FlowMind AI Workflow Assistant",
      },
      body: JSON.stringify({
        model: ASSISTANT_MODEL,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userQuestion },
        ],
        temperature: 0.7,
        max_tokens: 1024,
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      console.error("OpenRouter error:", response.status, errText);
      return NextResponse.json(
        { error: "OpenRouter API error", detail: errText },
        { status: response.status }
      );
    }

    const data = await response.json();
    const answer = data.choices?.[0]?.message?.content ?? "I couldn't generate a response. Please try again.";

    return NextResponse.json({ answer, sources: [] });
  } catch (err: any) {
    console.error("Assistant route error:", err);
    return NextResponse.json(
      { error: "Failed to reach assistant service", detail: err?.message },
      { status: 502 }
    );
  }
}
