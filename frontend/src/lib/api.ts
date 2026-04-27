// API client for the MECE Prompt Builder FastAPI backend

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export const api = {
  projects: {
    list: () => request<import("./types").Project[]>("/projects"),
    get: (id: string) => request<import("./types").Project>(`/projects/${id}`),
    create: (data: { name: string; description?: string; audience?: string; deck_type?: string; engagement_type?: string }) =>
      request<import("./types").Project>("/projects", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Record<string, string>) =>
      request<import("./types").Project>(`/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: string) => fetch(`${BASE_URL}/projects/${id}`, { method: "DELETE" }),
  },

  uploads: {
    list: (projectId: string) => request<import("./types").Upload[]>(`/projects/${projectId}/uploads`),
    upload: async (projectId: string, file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${BASE_URL}/projects/${projectId}/uploads`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      return res.json() as Promise<import("./types").Upload>;
    },
    getContent: (uploadId: string) =>
      request<{ filename: string; text: string; has_text: boolean }>(`/uploads/${uploadId}/content`),
    delete: (uploadId: string) => fetch(`${BASE_URL}/uploads/${uploadId}`, { method: "DELETE" }),
  },

  sessions: {
    getOrCreate: (projectId: string) =>
      request<import("./types").Session>(`/projects/${projectId}/session`),
    getMessages: (sessionId: string) =>
      request<import("./types").Message[]>(`/sessions/${sessionId}/messages`),
    sendMessage: (sessionId: string, content: string, opts?: {
      use_web_search?: boolean; research_depth?: string; auto_refine?: boolean;
      output_tone?: string; output_audience?: string; output_language?: string;
    }) =>
      fetch(`${BASE_URL}/sessions/${sessionId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content,
          use_web_search: opts?.use_web_search ?? false,
          research_depth: opts?.research_depth ?? "standard",
          auto_refine: opts?.auto_refine ?? false,
          output_tone: opts?.output_tone ?? "professional",
          output_audience: opts?.output_audience ?? "",
          output_language: opts?.output_language ?? "",
        }),
      }),
    advanceStage: (sessionId: string) =>
      request<import("./types").Session>(`/sessions/${sessionId}/stage/advance`, { method: "POST" }),
    setStage: (sessionId: string, stage: number) =>
      request<import("./types").Session>(`/sessions/${sessionId}/stage/set/${stage}`, { method: "POST" }),
  },

  templates: {
    list: () => request<import("./types").EngagementTemplate[]>("/templates"),
    get: (id: string) => request<import("./types").EngagementTemplate>(`/templates/${id}`),
  },

  handoff: {
    get: (projectId: string) =>
      request<import("./types").HandoffResponse>(`/projects/${projectId}/handoff`),
  },
};
