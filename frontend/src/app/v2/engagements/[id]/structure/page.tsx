"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Plus, Sparkles, Check, TreeDeciduous, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";
import { Chip, Dot, Logo } from "@/lib/v2/primitives";

// ────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────

type SubStatus = "done" | "active" | "gap" | "pending";

type SubQuestion = {
  q: string;
  slides: number[];
  status: SubStatus;
};

type Branch = {
  id: string;
  q: string;
  subs: SubQuestion[];
  status: SubStatus;
  sources: number;
};

type RawBranch = {
  question?: string;
  evidence?: string;
  evidence_needed?: string;
  so_what?: string;
  sub_questions?: string[];
};

// ────────────────────────────────────────────────────────────────
// Default placeholder branches (shown if Stage 2 hasn't run yet)
// ────────────────────────────────────────────────────────────────

const PLACEHOLDER_BRANCHES: Branch[] = [
  {
    id: "A",
    q: "Is the opportunity attractive?",
    subs: [
      { q: "Size & growth", slides: [], status: "pending" },
      { q: "Demand drivers", slides: [], status: "pending" },
      { q: "Macro tailwinds", slides: [], status: "pending" },
    ],
    status: "pending",
    sources: 0,
  },
  {
    id: "B",
    q: "Can we win?",
    subs: [
      { q: "Competitive landscape", slides: [], status: "pending" },
      { q: "Our advantage", slides: [], status: "pending" },
      { q: "Capability gaps", slides: [], status: "pending" },
    ],
    status: "pending",
    sources: 0,
  },
  {
    id: "C",
    q: "Is it worth the investment?",
    subs: [
      { q: "ROI & payback", slides: [], status: "pending" },
      { q: "Timeline", slides: [], status: "pending" },
      { q: "Downside risk", slides: [], status: "pending" },
    ],
    status: "pending",
    sources: 0,
  },
];

// ────────────────────────────────────────────────────────────────
// MECE structure page
// ────────────────────────────────────────────────────────────────

export default function StructurePage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [centralQuestion, setCentralQuestion] = useState<string>(
    "What is the central question this engagement answers?",
  );
  const [branches, setBranches] = useState<Branch[]>(PLACEHOLDER_BRANCHES);
  const [loading, setLoading] = useState(true);
  const [autoResolving, setAutoResolving] = useState(false);
  /** Path of the q being edited inline. "branch:<idx>" or "sub:<branchIdx>:<subIdx>". */
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editingDraft, setEditingDraft] = useState<string>("");

  function startEditingBranch(branchIdx: number) {
    setEditingDraft(branches[branchIdx]?.q ?? "");
    setEditingKey(`branch:${branchIdx}`);
  }
  function startEditingSub(branchIdx: number, subIdx: number) {
    setEditingDraft(branches[branchIdx]?.subs?.[subIdx]?.q ?? "");
    setEditingKey(`sub:${branchIdx}:${subIdx}`);
  }
  function commitEditing() {
    if (!editingKey) return;
    const text = editingDraft.trim();
    if (editingKey.startsWith("branch:")) {
      const idx = Number(editingKey.split(":")[1]);
      setBranches((prev) =>
        prev.map((b, i) => (i === idx ? { ...b, q: text || b.q } : b)),
      );
    } else if (editingKey.startsWith("sub:")) {
      const [, bIdx, sIdx] = editingKey.split(":");
      const branchIdx = Number(bIdx);
      const subIdx = Number(sIdx);
      setBranches((prev) =>
        prev.map((b, i) => {
          if (i !== branchIdx) return b;
          const newSubs = b.subs.map((s, j) =>
            j === subIdx ? { ...s, q: text || s.q } : s,
          );
          return { ...b, subs: newSubs };
        }),
      );
    }
    setEditingKey(null);
    setEditingDraft("");
  }
  function cancelEditing() {
    setEditingKey(null);
    setEditingDraft("");
  }

  useEffect(() => {
    if (!projectId) return;
    Promise.all([
      api.projects.get(projectId),
      api.sessions.getOrCreate(projectId),
    ])
      .then(([proj, session]) => {
        setProject(proj);
        const data = (session.stage_data ?? {}) as Record<string, unknown>;
        if (typeof data.central_question === "string") {
          setCentralQuestion(data.central_question);
        }
        // Parse branches from stage_data (set during Stage 2)
        let branchData: RawBranch[] | string = (data.branches as RawBranch[] | string) ?? "";
        if (typeof branchData === "string" && branchData) {
          try {
            branchData = JSON.parse(branchData) as RawBranch[];
          } catch {
            branchData = [];
          }
        }
        if (Array.isArray(branchData) && branchData.length > 0) {
          const built = buildBranches(branchData);
          setBranches(built);
        }
      })
      .catch((err) => toast.error("Failed to load structure: " + err.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  const goBack = () => router.push(`/v2/engagements/${projectId}`);
  const goNext = () => router.push(`/v2/engagements/${projectId}`);

  /**
   * Validate MECE — count gaps locally and surface a toast with the result.
   * Does NOT call the backend validator (that one validates slides, not the tree).
   */
  function handleValidate() {
    const gaps = countGaps(branches);
    const totalSubs = branches.reduce((acc, b) => acc + b.subs.length, 0);
    if (gaps === 0 && totalSubs > 0) {
      toast.success(`Tree is MECE-clean · ${totalSubs} sub-questions ready for the research prompt`);
    } else if (gaps === 0) {
      toast.info("Structure looks MECE-clean — add a few sub-questions to enrich the brief.");
    } else {
      toast.warning(
        `${gaps} gap(s) detected. Use Auto-resolve to ask the AI for help.`,
      );
    }
  }

  /**
   * Add branch — append a new empty branch to the local tree. Persistence
   * happens later when the user advances to Stage 03 (the AI re-reads the
   * tree from `stage_data.branches`).
   */
  function handleAddBranch() {
    if (branches.length >= 5) {
      toast.error("Max 5 branches in a MECE tree (otherwise readability suffers)");
      return;
    }
    const id = String.fromCharCode(65 + branches.length); // D, E…
    const newBranch: Branch = {
      id,
      q: "",
      subs: [{ q: "", slides: [], status: "pending" }],
      status: "pending",
      sources: 0,
    };
    setBranches((prev) => {
      const next = [...prev, newBranch];
      // Drop the user straight into the input for the new branch's question
      const newIdx = next.length - 1;
      setEditingKey(`branch:${newIdx}`);
      setEditingDraft("");
      return next;
    });
    toast.success(`Branch ${id} added · type your question`);
  }

  /**
   * Add a sub-question to a specific branch — appends a placeholder row that the
   * user can edit, or that Stage 03 will draft a slide for. Local-only until the
   * tree is sent to the AI (auto-resolve / advance).
   */
  function handleAddSubQuestion(branchIdx: number) {
    let newSubIdx = -1;
    setBranches((prev) => {
      const next = [...prev];
      const target = next[branchIdx];
      if (!target) return prev;
      // Cap at 6 — beyond that the branch is no longer collectively exhaustive at a useful level.
      if (target.subs.length >= 6) {
        toast.error("Max 6 sub-questions per branch — split the branch instead");
        return prev;
      }
      newSubIdx = target.subs.length;
      next[branchIdx] = {
        ...target,
        subs: [...target.subs, { q: "", slides: [], status: "pending" }],
      };
      return next;
    });
    if (newSubIdx >= 0) {
      // Drop straight into the inline editor for the new row
      setEditingKey(`sub:${branchIdx}:${newSubIdx}`);
      setEditingDraft("");
    }
  }

  /**
   * Auto-resolve — when there are gaps, send a synthesized message to the
   * AI chat asking it to draft slides for the missing sub-questions. After
   * sending, route to Workspace where the conversation streams progress.
   * When 0 gaps, the button is disabled (handled in the JSX below).
   */
  async function handleAutoResolve() {
    const gaps = countGaps(branches);
    if (gaps === 0) {
      toast.info("Nothing to resolve — tree is clean.");
      return;
    }
    const gappy = branches
      .map((b) => ({
        branch: `${b.id}. ${b.q}`,
        missing: b.subs.filter((s) => s.status === "gap" || s.status === "pending").map((s) => s.q),
      }))
      .filter((b) => b.missing.length > 0);

    const summary = [
      "Auto-resolve MECE gaps. The following sub-questions have no slide coverage:",
      ...gappy.map(
        (b) =>
          `\nBranch ${b.branch}:\n` + b.missing.map((m) => `  - ${m}`).join("\n"),
      ),
      "\nFor each gap, either draft a slide that covers it, or move the sub-question into a sibling branch where it fits naturally. Output the updated structure as JSON.",
    ].join("\n");

    setAutoResolving(true);
    try {
      const session = await api.sessions.getOrCreate(projectId);
      // Fire-and-route: drain SSE in the workspace, not here
      api.sessions
        .sendMessage(session.id, summary, {
          use_web_search: false,
          research_depth: "standard",
          auto_refine: false,
        })
        .then(async (response) => {
          if (response.body) {
            const reader = response.body.getReader();
            while (true) {
              const { done } = await reader.read();
              if (done) break;
            }
          }
        })
        .catch(() => {
          /* errors surface in the chat panel */
        });
      toast.success("Sent to AI · opening workspace to track progress");
      router.push(`/v2/engagements/${projectId}`);
    } catch (err) {
      toast.error("Auto-resolve failed: " + (err instanceof Error ? err.message : "?"));
    } finally {
      setAutoResolving(false);
    }
  }

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden">
      {/* ── Top bar ─────────────────────────────────────── */}
      <header
        className="flex shrink-0 items-center justify-between border-b"
        style={{
          padding: "12px 24px",
          borderColor: "var(--line)",
          background: "var(--paper)",
        }}
      >
        <div className="flex items-center gap-3">
          <button onClick={goBack} className="v2-ghost-btn">
            <ArrowLeft className="h-[13px] w-[13px]" strokeWidth={1.5} />
            Workspace
          </button>
          <Logo size={14} />
          <span style={{ color: "var(--ink-4)" }}>/</span>
          <span style={{ fontSize: 13, fontFamily: "var(--serif)" }}>
            {project?.name ?? "Engagement"} · MECE issue tree
          </span>
        </div>
        <div className="flex gap-1.5">
          <button onClick={handleValidate} className="v2-ghost-btn">Validate MECE</button>
          <button onClick={handleAddBranch} className="v2-outline-btn inline-flex items-center gap-1.5">
            <Plus className="h-[13px] w-[13px]" strokeWidth={1.5} />
            Add branch
          </button>
          <button onClick={goNext} className="v2-default-btn inline-flex items-center gap-1.5">
            Save & continue
            <ArrowRight className="h-[13px] w-[13px]" strokeWidth={1.5} />
          </button>
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────── */}
      <div
        className="flex-1 overflow-auto"
        style={{
          padding: "40px 48px",
          background:
            "radial-gradient(circle at 12% 0%, color-mix(in oklch, var(--accent) 4%, transparent), transparent 50%), var(--bg)",
        }}
      >
        {loading ? (
          <div className="flex items-center justify-center py-20" style={{ color: "var(--ink-3)" }}>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            <span style={{ fontSize: 13 }}>Loading structure…</span>
          </div>
        ) : (
          <>
            {/* ── Root central question ─────────────── */}
            <div className="mb-7 flex justify-center">
              <div
                style={{
                  maxWidth: 620,
                  padding: "16px 22px",
                  background: "var(--ink)",
                  color: "var(--paper)",
                  borderRadius: 10,
                }}
              >
                <div
                  className="mb-1.5"
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 10,
                    letterSpacing: 1.2,
                    color: "rgba(255,255,255,0.55)",
                  }}
                >
                  CENTRAL QUESTION
                </div>
                <div
                  style={{
                    fontFamily: "var(--serif)",
                    fontSize: 19,
                    lineHeight: 1.25,
                    letterSpacing: -0.2,
                  }}
                >
                  {centralQuestion}
                </div>
              </div>
            </div>

            {/* ── SVG connector lines ─────────────── */}
            <svg
              width="100%"
              height="40"
              style={{ display: "block", marginBottom: -1 }}
              preserveAspectRatio="none"
              viewBox="0 0 600 40"
            >
              <path
                d="M300 0 L300 18 L100 18 L100 40 M300 18 L500 18 L500 40 M300 18 L300 40"
                fill="none"
                stroke="var(--line-2)"
                strokeWidth="1"
              />
            </svg>

            {/* ── Branches grid ───────────────────── */}
            <div className="grid gap-4.5" style={{ gridTemplateColumns: "repeat(3, 1fr)", gap: 18 }}>
              {branches.map((b, branchIdx) => (
                <div key={b.id}>
                  {/* Branch header */}
                  <div
                    style={{
                      background:
                        b.status === "active" ? "var(--accent-soft)" : "var(--paper)",
                      border:
                        "1px solid " +
                        (b.status === "active" ? "var(--accent)" : "var(--line-2)"),
                      borderRadius: 10,
                      padding: "16px 18px",
                      marginBottom: 14,
                    }}
                  >
                    <div className="mb-2 flex items-center justify-between">
                      <Chip
                        size="xs"
                        tone={
                          b.status === "done"
                            ? "success"
                            : b.status === "active"
                              ? "accent"
                              : "ghost"
                        }
                      >
                        BRANCH {b.id}
                      </Chip>
                      <span
                        style={{
                          fontFamily: "var(--mono)",
                          fontSize: 10,
                          color: "var(--ink-3)",
                        }}
                      >
                        {b.sources} sources
                      </span>
                    </div>
                    {editingKey === `branch:${branchIdx}` ? (
                      <textarea
                        autoFocus
                        value={editingDraft}
                        onChange={(e) => setEditingDraft(e.target.value)}
                        onBlur={commitEditing}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            commitEditing();
                          } else if (e.key === "Escape") {
                            e.preventDefault();
                            cancelEditing();
                          }
                        }}
                        placeholder="Type the branch question…"
                        rows={2}
                        className="w-full"
                        style={{
                          fontFamily: "var(--serif)",
                          fontSize: 19,
                          lineHeight: 1.2,
                          letterSpacing: -0.2,
                          color: "var(--ink)",
                          background: "var(--paper)",
                          border: "1px solid var(--accent)",
                          borderRadius: 6,
                          padding: "6px 8px",
                          resize: "vertical",
                          minHeight: 52,
                          outline: "none",
                        }}
                      />
                    ) : (
                      <div
                        onClick={() => startEditingBranch(branchIdx)}
                        title="Click to edit"
                        className="cursor-text transition-colors hover:bg-black/[.02]"
                        style={{
                          fontFamily: "var(--serif)",
                          fontSize: 19,
                          lineHeight: 1.2,
                          letterSpacing: -0.2,
                          color: b.q ? "var(--ink)" : "var(--ink-4)",
                          padding: "6px 8px",
                          borderRadius: 6,
                          fontStyle: b.q ? "normal" : "italic",
                        }}
                      >
                        {b.q || "Click to write the branch question…"}
                      </div>
                    )}
                  </div>

                  {/* Sub-questions */}
                  <div
                    className="flex flex-col gap-2"
                    style={{
                      paddingLeft: 16,
                      borderLeft: "1px dashed var(--line-2)",
                    }}
                  >
                    {b.subs.map((s, i) => (
                      <div
                        key={i}
                        style={{
                          background: "var(--paper)",
                          border:
                            "1px solid " +
                            (s.status === "gap" ? "var(--warn)" : "var(--line)"),
                          borderRadius: 6,
                          padding: "10px 12px",
                        }}
                      >
                        <div className="flex items-center gap-2">
                          {s.status === "done" && (
                            <Check
                              className="h-[11px] w-[11px]"
                              strokeWidth={2.5}
                              style={{ color: "var(--success)" }}
                            />
                          )}
                          {s.status === "active" && <Dot color="var(--accent)" size={6} />}
                          {s.status === "gap" && <Dot color="var(--warn)" size={6} />}
                          {s.status === "pending" && <Dot color="var(--ink-4)" size={6} />}
                          {editingKey === `sub:${branchIdx}:${i}` ? (
                            <input
                              autoFocus
                              value={editingDraft}
                              onChange={(e) => setEditingDraft(e.target.value)}
                              onBlur={commitEditing}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                  e.preventDefault();
                                  commitEditing();
                                } else if (e.key === "Escape") {
                                  e.preventDefault();
                                  cancelEditing();
                                }
                              }}
                              placeholder="Type the sub-question…"
                              style={{
                                flex: 1,
                                fontSize: 13,
                                color: "var(--ink)",
                                background: "var(--paper)",
                                border: "1px solid var(--accent)",
                                borderRadius: 4,
                                padding: "3px 6px",
                                outline: "none",
                                fontFamily: "var(--sans)",
                              }}
                            />
                          ) : (
                            <span
                              onClick={() => startEditingSub(branchIdx, i)}
                              title="Click to edit"
                              className="cursor-text transition-colors hover:bg-black/[.02]"
                              style={{
                                fontSize: 13,
                                color: s.q ? "var(--ink)" : "var(--ink-4)",
                                flex: 1,
                                padding: "3px 6px",
                                borderRadius: 4,
                                fontStyle: s.q ? "normal" : "italic",
                              }}
                            >
                              {s.q || "Click to write the sub-question…"}
                            </span>
                          )}
                        </div>
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {s.slides.length > 0 ? (
                            s.slides.map((n) => (
                              <span
                                key={n}
                                style={{
                                  fontFamily: "var(--mono)",
                                  fontSize: 10,
                                  padding: "1px 6px",
                                  border: "1px solid var(--line)",
                                  borderRadius: 3,
                                  color: "var(--ink-3)",
                                }}
                              >
                                slide {n}
                              </span>
                            ))
                          ) : (
                            <span
                              className="italic"
                              style={{
                                fontSize: 11,
                                color:
                                  s.status === "gap"
                                    ? "var(--warn)"
                                    : "var(--ink-4)",
                              }}
                            >
                              {s.status === "gap"
                                ? "no coverage — gap"
                                : "not yet covered"}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                    <button
                      onClick={() => handleAddSubQuestion(branchIdx)}
                      className="cursor-pointer transition-opacity hover:opacity-70"
                      style={{
                        padding: "6px 12px",
                        background: "transparent",
                        border: "1px dashed var(--line-2)",
                        borderRadius: 6,
                        color: "var(--ink-3)",
                        fontSize: 11.5,
                        fontFamily: "var(--sans)",
                      }}
                    >
                      + Add sub-question
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* ── Validation strip ──────────────────── */}
            <div
              className="mt-8 flex items-center gap-3.5"
              style={{
                padding: "14px 18px",
                background: "var(--paper)",
                border: "1px solid var(--line)",
                borderRadius: 8,
              }}
            >
              <TreeDeciduous
                className="h-[18px] w-[18px]"
                strokeWidth={1.5}
                style={{ color: "var(--accent)" }}
              />
              <div className="flex-1">
                <div style={{ fontSize: 13, color: "var(--ink)", fontWeight: 500 }}>
                  MECE check · {countGaps(branches)} {countGaps(branches) === 1 ? "issue" : "issues"}
                </div>
                <div className="mt-0.5" style={{ fontSize: 12, color: "var(--ink-3)" }}>
                  {countGaps(branches) === 0
                    ? "All branches have slide coverage. Tree looks clean."
                    : `${countGaps(branches)} sub-question(s) have no slide coverage. Either add slides or move into a sibling branch.`}
                </div>
              </div>
              <button
                onClick={handleAutoResolve}
                disabled={autoResolving || countGaps(branches) === 0}
                className="v2-default-btn inline-flex items-center gap-1.5"
                title={
                  countGaps(branches) === 0
                    ? "Tree is clean — nothing to resolve"
                    : "Send the gaps to the AI to draft missing slides"
                }
              >
                {autoResolving ? (
                  <Loader2 className="h-[13px] w-[13px] animate-spin" />
                ) : (
                  <Sparkles className="h-[13px] w-[13px]" strokeWidth={1.5} />
                )}
                {autoResolving ? "Sending…" : "Auto-resolve"}
              </button>
            </div>

            <div className="mt-3 text-center" style={{ fontSize: 11, color: "var(--ink-4)" }}>
              When the tree feels right, head back to the workspace and click <em>Research Prompt</em>.
            </div>
          </>
        )}
      </div>

      {/* Inline button styles (scoped to .v2-theme) */}
      <style jsx>{`
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
        :global(.v2-theme .v2-ghost-btn:hover) {
          opacity: 0.7;
        }
        :global(.v2-theme .v2-outline-btn) {
          background: transparent;
          color: var(--ink);
          border: 1px solid var(--line-2);
          border-radius: 6px;
          padding: 5px 10px;
          font-size: 12px;
          font-weight: 500;
          font-family: var(--sans);
          cursor: pointer;
          transition: background 0.15s ease;
        }
        :global(.v2-theme .v2-outline-btn:hover) {
          background: rgba(0, 0, 0, 0.03);
        }
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
        }
        :global(.v2-theme .v2-default-btn:hover) {
          opacity: 0.9;
        }
        :global(.v2-theme .v2-default-btn:disabled) {
          background: var(--line-2);
          color: var(--ink-4);
          border-color: var(--line-2);
          opacity: 1;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// Build branches from session.stage_data + slide list
// ────────────────────────────────────────────────────────────────

function buildBranches(rawBranches: RawBranch[]): Branch[] {
  return rawBranches.slice(0, 3).map((b, idx) => {
    const id = String.fromCharCode(65 + idx); // A, B, C
    const title = b.question || `Branch ${id}`;
    // Map sub-questions if backend included them, otherwise synthesize from evidence text
    const subQs: string[] =
      b.sub_questions && b.sub_questions.length > 0
        ? b.sub_questions
        : (b.evidence || b.evidence_needed || "")
            .split(/[,;]\s*/)
            .filter(Boolean)
            .slice(0, 3);

    const subs: SubQuestion[] = (subQs.length > 0 ? subQs : ["Pending sub-question"]).map((q) => ({
      q,
      slides: [],
      status: "pending" as SubStatus,
    }));

    const status: SubStatus = "pending";

    return {
      id,
      q: title,
      subs,
      status,
      sources: 0,
    };
  });
}

function countGaps(branches: Branch[]): number {
  return branches.reduce(
    (acc, b) => acc + b.subs.filter((s) => s.status === "gap").length,
    0,
  );
}
