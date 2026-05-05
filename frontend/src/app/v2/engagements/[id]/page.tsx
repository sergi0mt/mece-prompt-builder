"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft, Check, Edit3, Loader2, FileSearch, ArrowRight,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { Project, Session } from "@/lib/types";
import { Chip, Dot, Logo, V2_STAGES } from "@/lib/v2/primitives";
import { V2Conversation } from "@/components/v2/v2-conversation";

// ────────────────────────────────────────────────────────────────
// Types for problem + MECE data (from sessions.stage_data)
// ────────────────────────────────────────────────────────────────

type RawBranch = {
  question?: string;
  evidence?: string;
  evidence_needed?: string;
  so_what?: string;
};

type EngagementData = {
  central_question: string;
  audience: string;
  desired_decision: string;
  language: string;
  template: string;
  branches: RawBranch[];
};

// ────────────────────────────────────────────────────────────────
// Workspace — main editor for an engagement (Stage 1 + Stage 2)
// ────────────────────────────────────────────────────────────────

export default function WorkspacePage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [data, setData] = useState<EngagementData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    Promise.all([
      api.projects.get(projectId),
      api.sessions.getOrCreate(projectId),
    ])
      .then(([proj, sess]) => {
        setProject(proj);
        setSession(sess);
        const sd = (sess.stage_data ?? {}) as Record<string, unknown>;
        const branches = parseBranches(sd.branches);
        setData({
          central_question: typeof sd.central_question === "string" ? sd.central_question : "",
          audience: typeof sd.audience === "string" ? sd.audience : proj.audience ?? "",
          desired_decision: typeof sd.desired_decision === "string" ? sd.desired_decision : "",
          language: typeof sd.language === "string" ? sd.language : "English",
          template: proj.engagement_type ?? proj.deck_type ?? "",
          branches,
        });
      })
      .catch((err) => toast.error("Failed to load engagement: " + err.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  const activeStage = Math.max(1, Math.min(2, session?.current_stage ?? 1));
  const meceReady = (data?.branches?.length ?? 0) >= 1;

  // ── Resizable splitter: canvas (left) vs conversation (right) ────
  // Width is the chat panel size in px. Persisted in localStorage.
  const CHAT_MIN = 320;
  const CHAT_MAX = 900;
  const CHAT_DEFAULT = 420;
  const SPLIT_KEY = "mpb:workspace-chat-width";

  const [chatWidth, setChatWidth] = useState<number>(CHAT_DEFAULT);
  const splitRef = useRef<HTMLDivElement | null>(null);
  const draggingRef = useRef(false);

  // Hydrate from localStorage on mount (client only, avoids SSR hydration mismatch)
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(SPLIT_KEY);
      if (raw) {
        const n = parseInt(raw, 10);
        if (Number.isFinite(n)) setChatWidth(clamp(n, CHAT_MIN, CHAT_MAX));
      }
    } catch {
      /* localStorage may be blocked; ignore */
    }
  }, []);

  const onDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    draggingRef.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!draggingRef.current || !splitRef.current) return;
      const rect = splitRef.current.getBoundingClientRect();
      // Chat width = distance from cursor to the right edge of the container
      const next = clamp(rect.right - e.clientX, CHAT_MIN, CHAT_MAX);
      setChatWidth(next);
    };
    const onUp = () => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      try {
        window.localStorage.setItem(SPLIT_KEY, String(chatWidth));
      } catch {
        /* ignore */
      }
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [chatWidth]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center" style={{ color: "var(--ink-3)" }}>
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        <span style={{ fontSize: 13 }}>Loading engagement…</span>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden">
      {/* ── Top bar ─────────────────────────────────────── */}
      <header
        className="flex shrink-0 items-center justify-between border-b"
        style={{ padding: "12px 24px", borderColor: "var(--line)", background: "var(--paper)" }}
      >
        <div className="flex items-center gap-3.5">
          <button
            onClick={() => router.push("/v2")}
            className="inline-flex items-center transition-opacity hover:opacity-70"
            style={{ background: "transparent", border: "none", padding: 4, cursor: "pointer" }}
          >
            <ArrowLeft className="h-[14px] w-[14px]" strokeWidth={1.5} style={{ color: "var(--ink-2)" }} />
          </button>
          <Logo size={14} />
          <span style={{ color: "var(--ink-4)" }}>/</span>
          <span style={{ fontFamily: "var(--serif)", fontSize: 14 }}>{project?.name ?? "Engagement"}</span>
          {data?.audience && (
            <Chip size="xs" tone="ghost">
              {data.audience}
            </Chip>
          )}
        </div>
        <div className="flex gap-1.5">
          <button
            onClick={() => router.push(`/v2/engagements/${projectId}/research-handoff`)}
            disabled={!meceReady}
            className="v2-default-btn"
            title={meceReady ? "Generate the deepresearch prompt" : "Complete Stage 2 first"}
          >
            <FileSearch className="h-[13px] w-[13px]" strokeWidth={1.5} />
            Research Prompt
          </button>
        </div>
      </header>

      {/* ── Big stage stepper (2 stages) ─────────────────── */}
      <BigStepper active={activeStage} projectId={projectId} />

      {/* ── 2-column body: canvas + draggable splitter + assistant ── */}
      <div
        ref={splitRef}
        className="grid flex-1 overflow-hidden"
        style={{
          // Three-column grid: canvas | 6px handle | chat panel
          gridTemplateColumns: `minmax(0, 1fr) 6px ${chatWidth}px`,
          minHeight: 0,
        }}
      >
        <StoryCanvas
          data={data}
          activeStage={activeStage}
          projectId={projectId}
          meceReady={meceReady}
        />

        {/* Drag handle */}
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize conversation panel"
          onMouseDown={onDragStart}
          onDoubleClick={() => {
            setChatWidth(CHAT_DEFAULT);
            try { window.localStorage.setItem(SPLIT_KEY, String(CHAT_DEFAULT)); } catch {}
          }}
          title="Drag to resize · double-click to reset"
          className="v2-split-handle"
        />

        <div className="flex min-h-0 flex-col" style={{ borderLeft: "1px solid var(--line)" }}>
          <V2Conversation projectId={projectId} />
        </div>
      </div>

      {/* Inline button styles (scoped to .v2-theme) */}
      <style jsx>{`
        :global(.v2-theme .v2-split-handle) {
          cursor: col-resize;
          background: transparent;
          position: relative;
          transition: background 0.15s ease;
        }
        :global(.v2-theme .v2-split-handle::before) {
          /* Thin vertical line in the middle of the handle */
          content: "";
          position: absolute;
          left: 50%;
          top: 0;
          bottom: 0;
          width: 1px;
          transform: translateX(-50%);
          background: var(--line);
        }
        :global(.v2-theme .v2-split-handle:hover) {
          background: color-mix(in oklch, var(--accent) 15%, transparent);
        }
        :global(.v2-theme .v2-split-handle:hover::before) {
          background: var(--accent);
          width: 2px;
        }
        :global(.v2-theme .v2-ghost-btn) {
          background: transparent;
          color: var(--ink-2);
          border: 1px solid transparent;
          border-radius: 6px;
          padding: 5px 10px;
          font-size: 12px;
          font-weight: 500;
          font-family: var(--sans);
          cursor: pointer;
          transition: opacity 0.15s ease;
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }
        :global(.v2-theme .v2-ghost-btn:hover) { opacity: 0.7; }
        :global(.v2-theme .v2-default-btn) {
          background: var(--ink);
          color: var(--paper);
          border: 1px solid var(--ink);
          border-radius: 6px;
          padding: 5px 10px;
          font-size: 12px;
          font-weight: 500;
          font-family: var(--sans);
          cursor: pointer;
          transition: opacity 0.15s ease;
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }
        :global(.v2-theme .v2-default-btn:hover) { opacity: 0.9; }
        :global(.v2-theme .v2-default-btn:disabled) {
          background: var(--line-2); color: var(--ink-4); border-color: var(--line-2);
          opacity: 1; cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// Big stepper — 2 stage cards across the top
// ────────────────────────────────────────────────────────────────

function BigStepper({ active, projectId }: { active: number; projectId: string }) {
  const router = useRouter();

  const handleStageClick = (n: number) => {
    // Stage 1 is the chat itself (right panel) — clicking the card is a no-op.
    if (n === 2) router.push(`/v2/engagements/${projectId}/structure`);
  };

  return (
    <div
      className="shrink-0 border-b"
      style={{
        padding: "24px 24px 18px",
        borderColor: "var(--line)",
        background: "var(--paper)",
      }}
    >
      <div className="grid grid-cols-2 gap-3.5">
        {V2_STAGES.map((s) => {
          const stageNum = s.n;
          const state =
            active === stageNum ? "active" : active > stageNum ? "done" : "pending";
          return (
            <button
              key={s.n}
              onClick={() => handleStageClick(stageNum)}
              className="text-left transition-all hover:-translate-y-0.5"
              style={{
                position: "relative",
                padding: "14px 16px 16px",
                background: state === "active" ? "var(--bg)" : "transparent",
                border:
                  "1px solid " +
                  (state === "active"
                    ? "var(--ink)"
                    : state === "done"
                      ? "var(--line-2)"
                      : "var(--line)"),
                borderRadius: 8,
                opacity: state === "pending" ? 0.55 : 1,
                cursor: "pointer",
              }}
            >
              <div className="mb-1.5 flex items-center gap-2">
                <span
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 10,
                    color: "var(--ink-3)",
                    letterSpacing: 1,
                  }}
                >
                  STAGE {String(stageNum).padStart(2, "0")}
                </span>
                {state === "done" && (
                  <Check
                    className="h-[12px] w-[12px]"
                    strokeWidth={2.5}
                    style={{ color: "var(--success)" }}
                  />
                )}
                {state === "active" && <Dot color="var(--accent)" size={7} />}
              </div>
              <div
                style={{
                  fontFamily: "var(--serif)",
                  fontSize: 22,
                  letterSpacing: -0.4,
                  lineHeight: 1.1,
                  color: "var(--ink)",
                }}
              >
                {s.name}
              </div>
              <div className="mt-1" style={{ fontSize: 12, color: "var(--ink-3)" }}>
                {s.sub}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// StoryCanvas — main left zone (central question, meta cells, MECE issue tree)
// ────────────────────────────────────────────────────────────────

function StoryCanvas({
  data,
  activeStage,
  projectId,
  meceReady,
}: {
  data: EngagementData | null;
  activeStage: number;
  projectId: string;
  meceReady: boolean;
}) {
  const router = useRouter();

  return (
    <div className="overflow-auto" style={{ padding: "36px 44px" }}>
      {/* ── Central question ──────────────────────── */}
      <div className="v2-kicker mb-2">CENTRAL QUESTION</div>
      <h1
        className="m-0 mb-5"
        style={{
          fontFamily: "var(--serif)",
          fontSize: 36,
          letterSpacing: -0.8,
          lineHeight: 1.1,
          fontWeight: 400,
          color: "var(--ink)",
        }}
      >
        {data?.central_question || "Define the central question to unlock the engagement"}
      </h1>

      {/* ── Meta cells ────────────────────────────── */}
      <div className="mb-9 flex gap-3" style={{ fontSize: 12 }}>
        <MetaCell label="Audience" value={prettifyValue(data?.audience) || "—"} />
        <MetaCell label="Decision" value={data?.desired_decision || "—"} />
        <MetaCell label="Template" value={prettifyValue(data?.template) || "—"} />
      </div>

      {/* ── Stage 02: MECE ──────────────────────────── */}
      <SectionTitle
        n="02"
        name="MECE Structure"
        active={activeStage === 2}
        onEdit={() => router.push(`/v2/engagements/${projectId}/structure`)}
      />
      <IssueTree branches={data?.branches ?? []} activeIdx={activeStage === 2 ? 1 : -1} />

      {/* ── Handoff CTA when MECE is ready ──────────── */}
      {meceReady && (
        <div style={{ marginTop: 32 }}>
          <button
            onClick={() => router.push(`/v2/engagements/${projectId}/research-handoff`)}
            className="inline-flex items-center gap-2 transition-opacity hover:opacity-90"
            style={{
              background: "var(--ink)",
              color: "var(--paper)",
              border: "1px solid var(--ink)",
              borderRadius: 6,
              padding: "10px 18px",
              fontSize: 14,
              fontWeight: 500,
              fontFamily: "var(--sans)",
              cursor: "pointer",
            }}
          >
            <FileSearch className="h-[15px] w-[15px]" strokeWidth={1.5} />
            Generate Research Prompt
            <ArrowRight className="h-[15px] w-[15px]" strokeWidth={1.5} />
          </button>
          <div className="mt-2" style={{ fontSize: 12, color: "var(--ink-3)" }}>
            Format the MECE as a markdown brief ready to drop into deepresearch.
          </div>
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// Meta cell
// ────────────────────────────────────────────────────────────────

function MetaCell({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="flex-1"
      style={{
        padding: "10px 14px",
        border: "1px solid var(--line)",
        borderRadius: 6,
        background: "var(--paper)",
      }}
    >
      <div
        style={{
          fontFamily: "var(--mono)",
          fontSize: 9,
          letterSpacing: 1.3,
          color: "var(--ink-3)",
          textTransform: "uppercase",
        }}
      >
        {label}
      </div>
      <div className="mt-0.5" style={{ fontSize: 13, color: "var(--ink)" }}>
        {value}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// Section title
// ────────────────────────────────────────────────────────────────

function SectionTitle({
  n,
  name,
  active,
  onEdit,
}: {
  n: string;
  name: string;
  active?: boolean;
  onEdit?: () => void;
}) {
  return (
    <div
      className="mb-4 flex items-baseline gap-3 pb-2.5"
      style={{ borderBottom: "1px solid var(--line)" }}
    >
      <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--ink-3)" }}>{n}</span>
      <span style={{ fontFamily: "var(--serif)", fontSize: 20, letterSpacing: -0.3 }}>{name}</span>
      {active && (
        <Chip size="xs" tone="accent">
          active
        </Chip>
      )}
      <div className="flex-1" />
      {onEdit && (
        <button
          onClick={onEdit}
          className="cursor-pointer transition-opacity hover:opacity-70"
          style={{
            background: "transparent",
            border: "none",
            color: "var(--ink-2)",
            fontSize: 11,
            fontWeight: 500,
            padding: 0,
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          <Edit3 className="h-[11px] w-[11px]" strokeWidth={1.5} />
          edit
        </button>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// Issue tree (mini)
// ────────────────────────────────────────────────────────────────

function IssueTree({ branches, activeIdx }: { branches: RawBranch[]; activeIdx: number }) {
  if (branches.length === 0) {
    return (
      <div
        className="text-center"
        style={{
          padding: "24px",
          border: "1px dashed var(--line-2)",
          borderRadius: 8,
          background: "var(--paper)",
          color: "var(--ink-3)",
          fontSize: 13,
        }}
      >
        Issue tree will appear once Stage 02 generates the MECE branches.
      </div>
    );
  }

  // Auto-fit grid: 3 cols when ≤3 branches, otherwise wrap into 2 cols on wider counts
  const cols = branches.length <= 3 ? "grid-cols-3" : "grid-cols-2 lg:grid-cols-3";

  return (
    <div className={`grid ${cols} gap-3.5`}>
      {branches.map((b, i) => {
        const isActive = i === activeIdx;
        const id = branchLetter(i);
        const subs = (b.evidence || b.evidence_needed || "").split(/[,;]\s*/).filter(Boolean).slice(0, 3);
        return (
          <div
            key={i}
            style={{
              border: "1px solid " + (isActive ? "var(--accent)" : "var(--line)"),
              background: isActive ? "var(--accent-soft)" : "var(--paper)",
              borderRadius: 8,
              padding: "14px 16px",
            }}
          >
            <div className="mb-2.5 flex items-center justify-between">
              <span
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 10,
                  color: "var(--ink-3)",
                  letterSpacing: 1,
                }}
              >
                BRANCH {id}
              </span>
              {isActive && <Dot color="var(--accent)" size={6} />}
            </div>
            <div
              className="mb-3"
              style={{
                fontFamily: "var(--serif)",
                fontSize: 17,
                lineHeight: 1.2,
                letterSpacing: -0.2,
                color: "var(--ink)",
              }}
            >
              {b.question || `Branch ${id}`}
            </div>
            <div className="flex flex-col gap-1">
              {subs.map((s, j) => (
                <div
                  key={j}
                  className="flex gap-2"
                  style={{ fontSize: 12, color: "var(--ink-2)" }}
                >
                  <span style={{ color: "var(--ink-4)" }}>—</span>
                  {s}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────────

/** Clamp a number into [min, max]. Used by the resizable splitter. */
function clamp(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, n));
}

/** A, B, ... Z, AA, AB, ... — same as the backend handoff_builder. */
function branchLetter(idx: number): string {
  let s = "";
  let n = idx;
  while (true) {
    s = String.fromCharCode(65 + (n % 26)) + s;
    n = Math.floor(n / 26) - 1;
    if (n < 0) break;
  }
  return s;
}

function parseBranches(raw: unknown): RawBranch[] {
  if (Array.isArray(raw)) return raw as RawBranch[];
  if (typeof raw === "string" && raw) {
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? (parsed as RawBranch[]) : [];
    } catch {
      return [];
    }
  }
  return [];
}

function prettifyValue(value: string | undefined): string {
  if (!value) return "";
  const KNOWN: Record<string, string> = {
    board: "Board",
    client: "Client",
    working_team: "Working Team",
    steering: "Steering",
    investors: "Investors",
    technical_leads: "Technical Leads",
    strategic: "Strategic",
    diagnostic: "Diagnostic",
    market_entry: "Market Entry",
    due_diligence: "Due Diligence",
    transformation: "Transformation",
    progress_update: "Progress Update",
    implementation: "Implementation",
    strategic_assessment: "Strategic Assessment",
    commercial_due_diligence: "Commercial Due Diligence",
    performance_improvement: "Performance Improvement",
    en: "English",
    es: "Spanish",
    pt: "Portuguese",
    fr: "French",
    de: "German",
  };
  const key = value.toLowerCase();
  if (KNOWN[key]) return KNOWN[key];
  return value
    .split("_")
    .map((w) => (w.length > 0 ? w[0].toUpperCase() + w.slice(1).toLowerCase() : w))
    .join(" ");
}
