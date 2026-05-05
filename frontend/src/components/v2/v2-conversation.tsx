/**
 * V2Conversation — full chat surface for the V2 redesign.
 *
 * Designed to fit inside Workspace B's right rail (or as a standalone overlay).
 * Renders:
 *  - Message history (user + assistant bubbles, paper/ink palette)
 *  - Streaming token cursor while AI responds
 *  - Research-agent live progress strip (when use_web_search + detailed depth)
 *  - Self-refine progress strip (when auto_refine enabled)
 *  - Interactive option pills (when AI ends with OPTIONS_JSON block)
 *  - Bottom composer with Web Search / Auto-refine / Depth selector + textarea
 *
 * The component is self-contained — pass `projectId` and it manages everything
 * via the `useV2Chat` hook.
 */
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Send,
  Globe,
  RefreshCw,
  Zap,
  Loader2,
  Sparkles,
  CheckCircle2,
  Search as SearchIcon,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import { Chip, Dot } from "@/lib/v2/primitives";
import { useV2Chat, type ChatStatus } from "@/lib/v2/use-chat";

// ────────────────────────────────────────────────────────────────
// Markdown components for assistant messages — V2 styling
// ────────────────────────────────────────────────────────────────

const MD_COMPONENTS: Components = {
  p: ({ children }) => (
    <p style={{ margin: "0 0 8px", lineHeight: 1.55, fontSize: 13.5 }}>{children}</p>
  ),
  strong: ({ children }) => (
    <strong style={{ fontWeight: 600, color: "var(--ink)" }}>{children}</strong>
  ),
  em: ({ children }) => <em style={{ fontStyle: "italic" }}>{children}</em>,
  ul: ({ children }) => (
    <ul style={{ margin: "0 0 8px", paddingLeft: 18, lineHeight: 1.55, fontSize: 13.5 }}>
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol style={{ margin: "0 0 8px", paddingLeft: 18, lineHeight: 1.55, fontSize: 13.5 }}>
      {children}
    </ol>
  ),
  li: ({ children }) => <li style={{ marginBottom: 2 }}>{children}</li>,
  code: ({ children }) => (
    <code
      style={{
        fontFamily: "var(--mono)",
        fontSize: 11.5,
        background: "rgba(0,0,0,0.04)",
        padding: "1px 5px",
        borderRadius: 3,
      }}
    >
      {children}
    </code>
  ),
  pre: ({ children }) => (
    <pre
      style={{
        fontFamily: "var(--mono)",
        fontSize: 11,
        background: "var(--bg)",
        border: "1px solid var(--line)",
        borderRadius: 6,
        padding: "10px 12px",
        margin: "6px 0",
        overflowX: "auto",
        lineHeight: 1.4,
      }}
    >
      {children}
    </pre>
  ),
  h1: ({ children }) => (
    <h1
      style={{
        fontFamily: "var(--serif)",
        fontSize: 18,
        letterSpacing: -0.3,
        margin: "8px 0 6px",
        fontWeight: 400,
      }}
    >
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2
      style={{
        fontFamily: "var(--serif)",
        fontSize: 16,
        letterSpacing: -0.2,
        margin: "8px 0 6px",
        fontWeight: 400,
      }}
    >
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3
      style={{
        fontFamily: "var(--sans)",
        fontSize: 13,
        fontWeight: 600,
        margin: "6px 0 4px",
        color: "var(--ink)",
      }}
    >
      {children}
    </h3>
  ),
  hr: () => (
    <hr style={{ border: "none", borderTop: "1px solid var(--line)", margin: "10px 0" }} />
  ),
};

// ────────────────────────────────────────────────────────────────
// V2Conversation
// ────────────────────────────────────────────────────────────────

export function V2Conversation({
  projectId,
  modelLabel,
  /** When true, shows the composer controls collapsed (web search + depth hidden until expanded). */
  compactControls = false,
}: {
  projectId: string;
  /** If omitted, the latest model is read from /api/v1/costs and re-fetched after each turn. */
  modelLabel?: string;
  compactControls?: boolean;
}) {
  const chat = useV2Chat(projectId);
  const [input, setInput] = useState("");
  // Default OFF: this app builds structure, not data. The deep-research run
  // downstream is much better at fetching evidence. Toggle is opt-in for
  // edge cases (the user wants the AI to verify a market exists, etc.).
  const [useWebSearch, setUseWebSearch] = useState(false);
  const [autoRefine, setAutoRefine] = useState(false);
  const [depth, setDepth] = useState("standard");
  const [latestModel, setLatestModel] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch the most recent model name from the cost tracker. Re-runs whenever
  // the chat goes idle (i.e. after a turn finishes) so the chip stays current.
  useEffect(() => {
    if (chat.status !== "idle") return;
    let cancelled = false;
    fetch("/api/v1/costs")
      .then((r) => (r.ok ? r.json() : null))
      .then((data: { calls?: { model?: string }[] } | null) => {
        if (cancelled || !data?.calls?.length) return;
        const last = data.calls[data.calls.length - 1];
        if (last?.model) setLatestModel(last.model);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [chat.status]);

  // Resolved model label: explicit prop > latest from cost tracker > fallback.
  const resolvedModel = modelLabel ?? latestModel ?? "model";

  // Auto-scroll — also fires when interactive option pills appear, so they're
  // always in view without needing to scroll manually.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [
    chat.messages,
    chat.streamText,
    chat.researchProgress,
    chat.interactiveOptions.length,
  ]);

  // Strip OPTIONS_JSON from historical assistant messages too
  const visibleMessages = useMemo(
    () =>
      chat.messages.map((m) => {
        if (m.role !== "assistant") return m;
        const match = m.content.match(/<!--\s*OPTIONS_JSON:\s*\[[\s\S]*?\]\s*-->/);
        return match ? { ...m, content: m.content.replace(match[0], "").trimEnd() } : m;
      }),
    [chat.messages],
  );

  function handleSend() {
    if (!input.trim() || chat.status !== "idle") return;
    chat.sendMessage(input.trim(), {
      use_web_search: useWebSearch,
      research_depth: depth,
      auto_refine: autoRefine,
    });
    setInput("");
  }

  return (
    <div className="flex h-full min-h-0 flex-col" style={{ background: "var(--paper)" }}>
      {/* ── Header ─────────────────────────────────────── */}
      <div
        className="flex shrink-0 items-center gap-2.5 border-b"
        style={{ padding: "14px 18px", borderColor: "var(--line)" }}
      >
        <Sparkles
          className="h-[14px] w-[14px]"
          strokeWidth={1.5}
          style={{ color: "var(--accent)" }}
        />
        <span className="v2-kicker" style={{ fontSize: 11, letterSpacing: 1 }}>
          Conversation
        </span>
        <div className="flex-1" />
        {chat.session && (
          <Chip size="xs" tone="ghost">
            stage {chat.session.current_stage}
          </Chip>
        )}
        <Chip size="xs" tone="ghost">
          {resolvedModel}
        </Chip>
      </div>

      {/* ── Message history ────────────────────────────── */}
      <div
        className="flex flex-1 flex-col overflow-y-auto"
        style={{ minHeight: 0 }}
      >
        <div className="flex flex-col gap-3" style={{ padding: "16px 18px" }}>
          {chat.loading ? (
            <div
              className="flex items-center justify-center py-10"
              style={{ color: "var(--ink-3)" }}
            >
              <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
              <span style={{ fontSize: 12 }}>Loading conversation…</span>
            </div>
          ) : visibleMessages.length === 0 ? (
            <div
              className="text-center"
              style={{
                padding: "28px 16px",
                border: "1px dashed var(--line-2)",
                borderRadius: 8,
                background: "var(--bg)",
                color: "var(--ink-3)",
                fontSize: 12.5,
                lineHeight: 1.5,
              }}
            >
              Ask a question, request a refinement, or describe the deck you need. The
              AI will guide you stage by stage.
            </div>
          ) : (
            visibleMessages.map((m) => <MessageBubble key={m.id} role={m.role} content={m.content} />)
          )}

          {/* Streaming bubble */}
          {chat.status !== "idle" && (
            <StreamingBubble status={chat.status} text={chat.streamText} />
          )}

          {/* Research progress strip (sticky-ish below stream) */}
          {chat.researchProgress && (
            <ProgressStrip
              icon={<SearchIcon className="h-3 w-3" strokeWidth={1.5} />}
              label={chat.researchProgress.label}
              pct={chat.researchProgress.pct}
              tone="accent"
            />
          )}

          {/* Interactive options */}
          {chat.interactiveOptions.length > 0 && chat.status === "idle" && (
            <InteractiveOptions
              options={chat.interactiveOptions}
              onSelect={(opt) =>
                chat.selectOption(opt, {
                  use_web_search: useWebSearch,
                  research_depth: depth,
                  auto_refine: autoRefine,
                })
              }
            />
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* ── Composer ───────────────────────────────────── */}
      <div
        className="shrink-0 border-t"
        style={{ borderColor: "var(--line)", padding: "12px 18px" }}
      >
        {!compactControls && (
          <div className="mb-2 flex items-center gap-3" style={{ fontSize: 11, color: "var(--ink-3)" }}>
            <label
              className="flex cursor-pointer items-center gap-1.5"
              title="Off por default: este step define ESTRUCTURA. La investigación profunda con datos reales la hace deepresearch después. Solo activá esto si necesitás que el AI verifique algo puntual (ej. confirmar que un mercado existe)."
            >
              <input
                type="checkbox"
                checked={useWebSearch}
                onChange={(e) => setUseWebSearch(e.target.checked)}
                className="cursor-pointer"
              />
              <Globe className="h-3 w-3" strokeWidth={1.5} />
              Web Search
              {useWebSearch && (
                <span style={{ fontSize: 10, color: "var(--warn)", marginLeft: 4 }}>
                  ⚠ better in deepresearch
                </span>
              )}
            </label>
            <label className="flex cursor-pointer items-center gap-1.5">
              <input
                type="checkbox"
                checked={autoRefine}
                onChange={(e) => setAutoRefine(e.target.checked)}
                className="cursor-pointer"
              />
              <RefreshCw className="h-3 w-3" strokeWidth={1.5} />
              Auto-refine
            </label>
            <div className="flex items-center gap-1">
              <Zap className="h-3 w-3" strokeWidth={1.5} />
              <select
                value={depth}
                onChange={(e) => setDepth(e.target.value)}
                className="cursor-pointer outline-none"
                style={{
                  background: "transparent",
                  border: "none",
                  fontSize: 11,
                  fontFamily: "var(--sans)",
                  color: "var(--ink-3)",
                }}
              >
                <option value="quick">Quick</option>
                <option value="standard">Standard</option>
                <option value="detailed">Detailed</option>
                <option value="comprehensive">Comprehensive</option>
              </select>
            </div>
          </div>
        )}

        <div
          className="flex items-end gap-2"
          style={{
            background: "var(--bg)",
            border: "1px solid var(--line-2)",
            borderRadius: 8,
            padding: "8px 10px",
          }}
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Refine, ask, or send a command…"
            disabled={chat.status !== "idle"}
            className="flex-1 resize-none outline-none"
            style={{
              minHeight: 38,
              maxHeight: 140,
              background: "transparent",
              border: "none",
              fontSize: 13,
              fontFamily: "var(--sans)",
              color: "var(--ink)",
              lineHeight: 1.45,
            }}
            rows={1}
          />
          <button
            onClick={handleSend}
            disabled={chat.status !== "idle" || !input.trim()}
            className="shrink-0 transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
            style={{
              height: 30,
              width: 30,
              borderRadius: 5,
              background: input.trim() && chat.status === "idle" ? "var(--ink)" : "var(--line-2)",
              color: "var(--paper)",
              border: "none",
              cursor: input.trim() && chat.status === "idle" ? "pointer" : "not-allowed",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {chat.status !== "idle" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.5} />
            ) : (
              <Send className="h-3.5 w-3.5" strokeWidth={1.5} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// MessageBubble
// ────────────────────────────────────────────────────────────────

function MessageBubble({ role, content }: { role: string; content: string }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className="max-w-[88%]"
        style={{
          padding: isUser ? "9px 13px" : "10px 14px",
          borderRadius: 10,
          background: isUser ? "var(--ink)" : "var(--bg)",
          color: isUser ? "var(--paper)" : "var(--ink)",
          border: isUser ? "none" : "1px solid var(--line)",
          fontSize: 13.5,
          lineHeight: 1.5,
        }}
      >
        {isUser ? (
          <span style={{ whiteSpace: "pre-wrap" }}>{content}</span>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
            {content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// StreamingBubble — assistant token stream + status indicator
// ────────────────────────────────────────────────────────────────

function StreamingBubble({ status, text }: { status: ChatStatus; text: string }) {
  return (
    <div className="flex justify-start">
      <div
        className="max-w-[88%]"
        style={{
          padding: "10px 14px",
          borderRadius: 10,
          background: "var(--bg)",
          border: "1px solid var(--line)",
          color: "var(--ink)",
          fontSize: 13.5,
          lineHeight: 1.5,
        }}
      >
        {text ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
            {text}
          </ReactMarkdown>
        ) : (
          <div
            className="flex items-center gap-2"
            style={{ color: "var(--ink-3)", fontSize: 12.5 }}
          >
            <Loader2 className="h-3 w-3 animate-spin" strokeWidth={1.5} />
            {status === "researching"
              ? "Running research agent…"
              : status === "sending"
                ? "Sending…"
                : "Thinking…"}
          </div>
        )}
        {text && (
          <span
            className="ml-0.5 inline-block animate-pulse rounded-sm"
            style={{ width: 6, height: 14, background: "var(--accent)" }}
          />
        )}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// ProgressStrip — research / refine live progress
// ────────────────────────────────────────────────────────────────

function ProgressStrip({
  icon,
  label,
  pct,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  pct: number;
  tone: "accent" | "success" | "warn";
}) {
  const color =
    tone === "success" ? "var(--success)" : tone === "warn" ? "var(--warn)" : "var(--accent)";
  return (
    <div
      style={{
        background: "var(--bg)",
        border: "1px solid var(--line)",
        borderRadius: 6,
        padding: "8px 12px",
      }}
    >
      <div className="mb-1.5 flex items-center gap-2" style={{ color: color, fontSize: 11.5 }}>
        {icon}
        <span style={{ flex: 1, color: "var(--ink-2)" }}>{label}</span>
        {pct === 100 && (
          <CheckCircle2
            className="h-3 w-3"
            strokeWidth={2}
            style={{ color: "var(--success)" }}
          />
        )}
      </div>
      <div
        className="overflow-hidden"
        style={{ height: 3, background: "var(--line)", borderRadius: 2 }}
      >
        <div
          style={{
            height: "100%",
            width: `${Math.max(2, Math.min(100, pct))}%`,
            background: color,
            transition: "width 0.3s ease",
          }}
        />
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// InteractiveOptions — 10 pills + custom write-in
// ────────────────────────────────────────────────────────────────

function InteractiveOptions({
  options,
  onSelect,
}: {
  options: string[];
  onSelect: (opt: string) => void;
}) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[92%]">
        <p
          className="mb-1.5 uppercase"
          style={{
            fontSize: 10,
            color: "var(--ink-3)",
            fontFamily: "var(--mono)",
            letterSpacing: 1.2,
          }}
        >
          Pick a quick reply
        </p>
        <div className="flex flex-col gap-1.5">
          {options.map((opt, i) => (
            <button
              key={i}
              onClick={() => onSelect(opt)}
              className="cursor-pointer transition-colors"
              title={opt}
              style={{
                fontSize: 11.5,
                padding: "7px 14px",
                border: "1px solid var(--line)",
                borderRadius: 14,
                background: "var(--paper)",
                color: "var(--ink-2)",
                fontFamily: "var(--sans)",
                lineHeight: 1.4,
                width: "100%",
                whiteSpace: "normal",
                wordBreak: "break-word",
                textAlign: "left",
                display: "flex",
                alignItems: "flex-start",
                gap: 8,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--ink)";
                e.currentTarget.style.color = "var(--paper)";
                e.currentTarget.style.borderColor = "var(--ink)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "var(--paper)";
                e.currentTarget.style.color = "var(--ink-2)";
                e.currentTarget.style.borderColor = "var(--line)";
              }}
            >
              <Dot color="var(--accent)" size={5} />
              {`${i + 1}. ${opt}`}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
