import { TOKEN_KEY } from "./api";

export interface RealtimeEvent {
  type: string;
  [k: string]: unknown;
}

/** Connect an authenticated WebSocket with automatic reconnect. */
export function connectRealtime(caseId: string | null, onEvent: (e: RealtimeEvent) => void): () => void {
  let ws: WebSocket | null = null;
  let closed = false;
  let retry = 0;

  const open = () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return;
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    const cq = caseId ? `&case_id=${encodeURIComponent(caseId)}` : "";
    ws = new WebSocket(`${scheme}://${location.host}/api/v1/ws?token=${encodeURIComponent(token)}${cq}`);
    ws.onmessage = (m) => {
      try { onEvent(JSON.parse(m.data as string)); } catch { /* ignore */ }
    };
    ws.onclose = () => {
      if (closed) return;
      retry = Math.min(retry + 1, 6);
      setTimeout(open, 500 * retry);
    };
    ws.onopen = () => { retry = 0; };
  };
  open();

  return () => { closed = true; ws?.close(); };
}
