import { useEffect, useRef, useState } from "react";
import {
  ChatResponse,
  PolicyDocument,
  ToolCall,
  fetchDocument,
  sendMessage,
} from "./api";

interface Message {
  role: "user" | "assistant";
  text: string;
  citations?: string[];
  toolCalls?: ToolCall[];
  refused?: boolean;
  latencyMs?: number;
  error?: boolean;
}

const SUGGESTIONS = [
  "Can a customer return an opened laptop?",
  "What is the status of order NM-10077?",
  "Does the employee discount stack with a price match?",
];

const TOOL_LABELS: Record<string, string> = {
  search_knowledge_base: "searched documentation",
  get_order_status: "checked order system",
};

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [openDoc, setOpenDoc] = useState<PolicyDocument | null>(null);
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  async function submit(text: string) {
    const question = text.trim();
    if (!question || busy) return;
    setInput("");
    setBusy(true);
    setMessages((prior) => [...prior, { role: "user", text: question }]);
    try {
      const reply: ChatResponse = await sendMessage(question, sessionId);
      setSessionId(reply.session_id);
      setMessages((prior) => [
        ...prior,
        {
          role: "assistant",
          text: reply.answer,
          citations: reply.citations,
          toolCalls: reply.tool_calls,
          refused: reply.refused,
          latencyMs: reply.latency_ms,
        },
      ]);
    } catch (error) {
      setMessages((prior) => [
        ...prior,
        {
          role: "assistant",
          text: error instanceof Error ? error.message : "Something went wrong.",
          error: true,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function showDocument(docId: string) {
    try {
      setOpenDoc(await fetchDocument(docId));
    } catch {
      // The chip is best effort; the citation text itself already names the source.
    }
  }

  function reset() {
    setMessages([]);
    setSessionId(null);
    setOpenDoc(null);
  }

  return (
    <div className="shell">
      <header>
        <div>
          <h1>NovaMart Assistant</h1>
          <p className="subtitle">Internal support for store employees</p>
        </div>
        <button className="ghost" onClick={reset} disabled={messages.length === 0}>
          New conversation
        </button>
      </header>

      <div className="thread" ref={threadRef}>
        {messages.length === 0 && (
          <div className="empty">
            <p>Ask about NovaMart policy, or look up an order by its NM number.</p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => submit(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((message, index) => (
          <div
            key={index}
            className={[
              "message",
              message.role,
              message.refused ? "refused" : "",
              message.error ? "error" : "",
            ].join(" ")}
          >
            <div className="bubble">{message.text}</div>
            {message.role === "assistant" && !message.error && (
              <div className="meta">
                {(message.toolCalls ?? []).map((call, i) => (
                  <span key={i} className="badge tool">
                    {TOOL_LABELS[call.name] ?? call.name}
                  </span>
                ))}
                {(message.citations ?? []).map((docId) => (
                  <button key={docId} className="badge source" onClick={() => showDocument(docId)}>
                    {docId}
                  </button>
                ))}
                {message.refused && <span className="badge warn">escalate to duty manager</span>}
                {message.latencyMs !== undefined && (
                  <span className="latency">{(message.latencyMs / 1000).toFixed(1)}s</span>
                )}
              </div>
            )}
          </div>
        ))}
        {busy && <div className="message assistant thinking">Checking...</div>}
      </div>

      {openDoc && (
        <aside className="doc-panel">
          <div className="doc-header">
            <h2>{openDoc.title}</h2>
            <button className="ghost" onClick={() => setOpenDoc(null)}>
              Close
            </button>
          </div>
          {openDoc.sections.map((section) => (
            <section key={section.heading}>
              <h3>{section.heading}</h3>
              <p>{section.text}</p>
            </section>
          ))}
        </aside>
      )}

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void submit(input);
        }}
      >
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask about policy or an order number..."
          disabled={busy}
        />
        <button type="submit" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
