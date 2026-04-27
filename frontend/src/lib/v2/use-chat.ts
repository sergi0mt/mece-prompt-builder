/**
 * useV2Chat — SSE streaming chat hook for the MECE Prompt Builder.
 *
 * Encapsulates the SSE protocol used by the chat router:
 *  - `data: {"type":"text", "content":"..."}` — token chunks for the assistant
 *  - `event: research` + `data: {...}` — research-agent progress events
 *    (plan_start, step_done, synthesize_done, …)
 *  - The trailing assistant message may contain a hidden
 *    `<!-- OPTIONS_JSON: [...] -->` block. We strip it and surface the array
 *    as `interactiveOptions` for the option pills UI.
 *
 * The hook owns no UI — it just exposes state + a `sendMessage()` callback.
 */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { Message, Session } from "@/lib/types";

export type ChatStatus =
  | "idle"
  | "sending"
  | "streaming"
  | "researching";

export type ResearchProgress = {
  label: string;
  pct: number;
};

export type SendOptions = {
  use_web_search?: boolean;
  research_depth?: string;
  auto_refine?: boolean;
  output_tone?: string;
  output_audience?: string;
  output_language?: string;
};

/** Strip `<!-- OPTIONS_JSON: [...] -->` block from text and return both. */
export function extractOptions(text: string): [string, string[]] {
  const match = text.match(/<!--\s*OPTIONS_JSON:\s*(\[[\s\S]*?\])\s*-->/);
  if (!match) return [text, []];
  try {
    const options = JSON.parse(match[1]);
    if (Array.isArray(options) && options.every((o: unknown) => typeof o === "string")) {
      const clean = text.replace(match[0], "").trimEnd();
      return [clean, options];
    }
  } catch {
    /* fall through */
  }
  return [text, []];
}

const STAGE_NAMES = ["", "Define Problem", "MECE Structure"];

export function useV2Chat(projectId: string | undefined) {
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);

  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<ChatStatus>("idle");

  const [streamText, setStreamText] = useState("");
  const [interactiveOptions, setInteractiveOptions] = useState<string[]>([]);
  const [researchProgress, setResearchProgress] = useState<ResearchProgress | null>(null);

  // ── Initial load ──────────────────────────────────────────────
  useEffect(() => {
    if (!projectId) return;
    api.sessions
      .getOrCreate(projectId)
      .then(async (sess) => {
        setSession(sess);
        const msgs = await api.sessions.getMessages(sess.id);
        setMessages(msgs);
      })
      .catch((err) =>
        toast.error("Failed to load chat: " + (err instanceof Error ? err.message : "?")),
      )
      .finally(() => setLoading(false));
  }, [projectId]);

  // ── Send message with SSE ─────────────────────────────────────
  const sendMessage = useCallback(
    async (content: string, options: SendOptions = {}) => {
      if (!session || !content.trim() || status !== "idle") return;
      setStatus("sending");
      setStreamText("");
      setInteractiveOptions([]);
      setResearchProgress(null);

      const userMsg: Message = {
        id: crypto.randomUUID(),
        session_id: session.id,
        role: "user",
        content,
        stage: session.current_stage,
        metadata: {},
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      try {
        const response = await api.sessions.sendMessage(session.id, content, {
          use_web_search: options.use_web_search ?? false,
          research_depth: options.research_depth ?? "detailed",
          auto_refine: options.auto_refine ?? false,
          output_tone: options.output_tone,
          output_audience: options.output_audience,
          output_language: options.output_language,
        });
        if (!response.body) {
          setStatus("idle");
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = "";
        let buffer = "";
        let researchStepCount = 0;
        setStatus("streaming");

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (let li = 0; li < lines.length; li++) {
            const line = lines[li];

            // ── Research events ─────────────────────────────
            if (line.startsWith("event: research") && li + 1 < lines.length && lines[li + 1].startsWith("data: ")) {
              try {
                const data = JSON.parse(lines[li + 1].slice(6));
                setStatus("researching");
                if (data.type === "plan_start") {
                  setResearchProgress({ label: "Planning research…", pct: 5 });
                } else if (data.type === "plan_done") {
                  setResearchProgress({ label: `Plan ready: ${data.num_steps ?? "?"} sub-questions`, pct: 15 });
                } else if (data.type === "step_start") {
                  researchStepCount++;
                  setResearchProgress({
                    label: `Searching: ${(data.sub_question || "").slice(0, 60)}…`,
                    pct: 15 + Math.min(70, researchStepCount * 10),
                  });
                } else if (data.type === "step_done") {
                  setResearchProgress({
                    label: `Step ${data.step_id} done — ${data.result_count ?? 0} results`,
                    pct: 15 + Math.min(70, researchStepCount * 10),
                  });
                } else if (data.type === "synthesize_start") {
                  setResearchProgress({ label: "Synthesizing findings…", pct: 90 });
                } else if (data.type === "research_complete") {
                  setResearchProgress({
                    label: `Research complete · ${data.total_sources ?? 0} sources`,
                    pct: 100,
                  });
                  window.setTimeout(() => setResearchProgress(null), 2500);
                  setStatus("streaming");
                }
                li++;
              } catch {
                /* skip */
              }
              continue;
            }

            // ── Plain `data:` text chunks ─────────────────────
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.type === "text") {
                  fullText += data.content;
                  setStreamText(fullText);
                } else if (data.type === "error") {
                  fullText += `\n\nError: ${data.content}`;
                  setStreamText(fullText);
                }
              } catch {
                /* skip */
              }
            }
          }
        }

        // ── Finalize: append assistant message with options stripped ──
        if (fullText) {
          const [cleanText, options] = extractOptions(fullText);
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              session_id: session.id,
              role: "assistant",
              content: cleanText,
              stage: session.current_stage,
              metadata: {},
              created_at: new Date().toISOString(),
            },
          ]);
          setInteractiveOptions(options);
        }

        // Re-fetch session — stage may have advanced
        const newSession = await api.sessions.getOrCreate(projectId!);
        setSession(newSession);

        if (newSession.current_stage !== session.current_stage) {
          toast.success(`Advanced to Stage ${newSession.current_stage}: ${STAGE_NAMES[newSession.current_stage] ?? ""}`);
        }
      } catch (err) {
        toast.error("Chat error: " + (err instanceof Error ? err.message : "Unknown"));
      } finally {
        setStatus("idle");
        setStreamText("");
      }
    },
    [session, status, projectId],
  );

  // ── Auto-send queued option ─────────────────────────────────
  const pendingOptionRef = useRef<string | null>(null);

  const selectOption = useCallback(
    (option: string, options: SendOptions = {}) => {
      if (status !== "idle") return;
      setInteractiveOptions([]);
      pendingOptionRef.current = option;
      Promise.resolve().then(() => {
        if (pendingOptionRef.current) {
          const opt = pendingOptionRef.current;
          pendingOptionRef.current = null;
          sendMessage(opt, options);
        }
      });
    },
    [status, sendMessage],
  );

  return {
    session,
    messages,
    loading,
    status,
    streamText,
    interactiveOptions,
    researchProgress,
    sendMessage,
    selectOption,
    setSession,
  };
}
