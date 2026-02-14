const API_BASE = "http://localhost:8000";
const TIMEOUT_MS = 90_000;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `HTTP ${res.status}`);
    }

    return (await res.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}

// --- Types ---

export interface Session {
  session_id: string;
  greeting: string;
}

export interface SessionInfo {
  session_id: string;
  messages: { role: string; content: string }[];
}

export interface Message {
  role: string;
  content: string;
  metadata?: {
    input_tokens: number;
    output_tokens: number;
    elapsed_time: number;
    model: string;
  };
}

export interface Reframe {
  reframed_entry: string;
  metadata?: {
    input_tokens: number;
    output_tokens: number;
    elapsed_time: number;
    model: string;
  };
}

// --- API functions ---

export function createSession(
  valence: number,
  supportType: number,
  model?: string,
  agent?: string
): Promise<Session> {
  return request("/session", {
    method: "POST",
    body: JSON.stringify({
      valence,
      support_type: supportType,
      model: model ?? "sonnet",
      agent: agent ?? "journal",
    }),
  });
}

export function getSession(sessionId: string): Promise<SessionInfo> {
  return request(`/session/${sessionId}`);
}

export function sendMessage(
  sessionId: string,
  content: string
): Promise<Message> {
  return request(`/session/${sessionId}/message`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function reframe(sessionId: string): Promise<Reframe> {
  return request(`/session/${sessionId}/reframe`, {
    method: "POST",
  });
}
