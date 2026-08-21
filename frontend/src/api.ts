export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  citations: string[];
  tool_calls: ToolCall[];
  refused: boolean;
  latency_ms: number;
}

export interface DocumentSection {
  heading: string;
  text: string;
}

export interface PolicyDocument {
  doc_id: string;
  title: string;
  sections: DocumentSection[];
}

export async function sendMessage(
  message: string,
  sessionId: string | null,
): Promise<ChatResponse> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request failed (${response.status})`);
  }
  return response.json();
}

export async function fetchDocument(docId: string): Promise<PolicyDocument> {
  const response = await fetch(`/api/documents/${docId}`);
  if (!response.ok) throw new Error(`Could not load document ${docId}`);
  return response.json();
}
