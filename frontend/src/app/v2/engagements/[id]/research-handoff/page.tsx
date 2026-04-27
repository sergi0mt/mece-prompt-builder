"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Copy, Check, ExternalLink, Loader2, AlertTriangle, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Chip, Logo } from "@/lib/v2/primitives";

const DEEPRESEARCH_URL_KEY = "mece_pb_deepresearch_url";
const DEFAULT_DEEPRESEARCH_URL = "http://localhost:8001";

export default function ResearchHandoffPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [originalPrompt, setOriginalPrompt] = useState("");
  const [prompt, setPrompt] = useState("");
  const [serverTruncated, setServerTruncated] = useState(false);
  const [copied, setCopied] = useState(false);
  const [deepresearchUrl, setDeepresearchUrl] = useState(DEFAULT_DEEPRESEARCH_URL);

  // Load deepresearch URL preference from localStorage
  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = localStorage.getItem(DEEPRESEARCH_URL_KEY);
    if (stored) setDeepresearchUrl(stored);
  }, []);

  // Persist deepresearch URL when changed
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (deepresearchUrl) {
      localStorage.setItem(DEEPRESEARCH_URL_KEY, deepresearchUrl);
    }
  }, [deepresearchUrl]);

  // Fetch the prompt
  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    api.handoff
      .get(projectId)
      .then((res) => {
        setOriginalPrompt(res.prompt);
        setPrompt(res.prompt);
        setServerTruncated(res.truncated);
        setError(null);
      })
      .catch((err: Error) => {
        setError(err.message || "Failed to load prompt");
      })
      .finally(() => setLoading(false));
  }, [projectId]);

  const charCount = prompt.length;
  const overLimit = charCount > 2000;

  const handleCopy = async () => {
    if (!prompt) return;
    try {
      await navigator.clipboard.writeText(prompt);
      setCopied(true);
      toast.success("Prompt copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy — your browser may block clipboard access");
    }
  };

  const handleOpenDeepresearch = () => {
    if (!deepresearchUrl.trim()) {
      toast.error("Set a deepresearch URL first");
      return;
    }
    window.open(deepresearchUrl, "_blank", "noopener,noreferrer");
  };

  const handleReset = () => {
    setPrompt(originalPrompt);
    toast.info("Prompt reset to server-generated version");
  };

  const dirty = useMemo(() => prompt !== originalPrompt, [prompt, originalPrompt]);

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden">
      {/* ── Top bar ─────────────────────────────────────── */}
      <header
        className="flex shrink-0 items-center justify-between border-b"
        style={{ padding: "12px 24px", borderColor: "var(--line)", background: "var(--paper)" }}
      >
        <div className="flex items-center gap-3.5">
          <button
            onClick={() => router.push(`/v2/engagements/${projectId}`)}
            className="inline-flex items-center transition-opacity hover:opacity-70"
            style={{ background: "transparent", border: "none", padding: 4, cursor: "pointer" }}
          >
            <ArrowLeft className="h-[14px] w-[14px]" strokeWidth={1.5} style={{ color: "var(--ink-2)" }} />
          </button>
          <Logo size={14} />
          <span style={{ color: "var(--ink-4)" }}>/</span>
          <span style={{ fontFamily: "var(--serif)", fontSize: 14 }}>Research handoff</span>
        </div>
      </header>

      {/* ── Body ────────────────────────────────────────── */}
      <div className="flex-1 overflow-auto">
        <div style={{ maxWidth: 880, margin: "0 auto", padding: "40px 32px 80px" }}>
          {/* Title */}
          <div className="v2-kicker mb-2">RESEARCH HANDOFF</div>
          <h1
            className="m-0"
            style={{
              fontFamily: "var(--serif)",
              fontSize: 40,
              letterSpacing: -0.8,
              lineHeight: 1.1,
              fontWeight: 400,
              color: "var(--ink)",
            }}
          >
            Drop this prompt into deepresearch
          </h1>
          <p
            className="mt-3"
            style={{
              fontSize: 15,
              color: "var(--ink-3)",
              lineHeight: 1.55,
              maxWidth: 640,
            }}
          >
            We&apos;ve formatted your central question and MECE branches as a markdown brief.
            Tweak it below if you want, then copy and paste it into the deepresearch app.
          </p>

          {/* Loading / Error */}
          {loading && (
            <div className="mt-10 flex items-center" style={{ color: "var(--ink-3)" }}>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              <span style={{ fontSize: 13 }}>Generating prompt…</span>
            </div>
          )}

          {error && !loading && (
            <div
              className="mt-10 flex items-start gap-3"
              style={{
                padding: "16px 18px",
                border: "1px solid color-mix(in oklch, var(--danger) 30%, transparent)",
                borderRadius: 8,
                background: "color-mix(in oklch, var(--danger) 8%, transparent)",
              }}
            >
              <AlertTriangle className="h-[16px] w-[16px] mt-0.5 shrink-0" style={{ color: "var(--danger)" }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, color: "var(--ink)" }}>
                  Could not generate the prompt
                </div>
                <div className="mt-1" style={{ fontSize: 12, color: "var(--ink-3)" }}>
                  {error}
                </div>
                <button
                  onClick={() => router.push(`/v2/engagements/${projectId}`)}
                  className="mt-3 underline"
                  style={{ background: "transparent", border: "none", color: "var(--ink-2)", fontSize: 12, cursor: "pointer", padding: 0 }}
                >
                  ← Back to workspace
                </button>
              </div>
            </div>
          )}

          {/* Editor */}
          {!loading && !error && (
            <>
              {/* Char count + actions row */}
              <div className="mt-8 mb-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Chip size="xs" tone={overLimit ? "warn" : "ghost"}>
                    {charCount} / 2000 chars
                  </Chip>
                  {serverTruncated && (
                    <Chip size="xs" tone="warn">
                      truncated by server
                    </Chip>
                  )}
                  {dirty && (
                    <Chip size="xs" tone="accent">
                      edited
                    </Chip>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {dirty && (
                    <button
                      onClick={handleReset}
                      className="inline-flex items-center gap-1.5 transition-opacity hover:opacity-70"
                      style={{
                        background: "transparent",
                        color: "var(--ink-3)",
                        border: "1px solid var(--line-2)",
                        borderRadius: 6,
                        padding: "6px 12px",
                        fontSize: 12,
                        fontWeight: 500,
                        fontFamily: "var(--sans)",
                        cursor: "pointer",
                      }}
                    >
                      <RotateCcw className="h-[12px] w-[12px]" strokeWidth={1.5} />
                      Reset
                    </button>
                  )}
                </div>
              </div>

              {/* Textarea */}
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                spellCheck={false}
                style={{
                  width: "100%",
                  minHeight: 480,
                  padding: "20px 22px",
                  border: "1px solid var(--line-2)",
                  borderRadius: 8,
                  background: "var(--paper)",
                  color: "var(--ink)",
                  fontFamily: "var(--mono)",
                  fontSize: 13,
                  lineHeight: 1.6,
                  resize: "vertical",
                  outline: "none",
                  letterSpacing: "-0.1px",
                }}
              />

              {/* Action row */}
              <div className="mt-5 flex flex-wrap items-end gap-3">
                <button
                  onClick={handleCopy}
                  className="inline-flex items-center gap-2 transition-opacity hover:opacity-90"
                  style={{
                    background: copied ? "var(--success)" : "var(--ink)",
                    color: "var(--paper)",
                    border: "1px solid " + (copied ? "var(--success)" : "var(--ink)"),
                    borderRadius: 6,
                    padding: "10px 18px",
                    fontSize: 14,
                    fontWeight: 500,
                    fontFamily: "var(--sans)",
                    cursor: "pointer",
                  }}
                >
                  {copied ? (
                    <>
                      <Check className="h-[15px] w-[15px]" strokeWidth={1.5} />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-[15px] w-[15px]" strokeWidth={1.5} />
                      Copy to clipboard
                    </>
                  )}
                </button>

                <div style={{ flex: "1 1 240px", minWidth: 220 }}>
                  <label
                    className="block mb-1"
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 9,
                      letterSpacing: 1.3,
                      color: "var(--ink-3)",
                      textTransform: "uppercase",
                    }}
                  >
                    Deepresearch URL
                  </label>
                  <input
                    type="url"
                    value={deepresearchUrl}
                    onChange={(e) => setDeepresearchUrl(e.target.value)}
                    placeholder="http://localhost:8001"
                    style={{
                      width: "100%",
                      padding: "8px 12px",
                      border: "1px solid var(--line-2)",
                      borderRadius: 6,
                      background: "var(--paper)",
                      color: "var(--ink)",
                      fontFamily: "var(--mono)",
                      fontSize: 12,
                      outline: "none",
                    }}
                  />
                </div>

                <button
                  onClick={handleOpenDeepresearch}
                  className="inline-flex items-center gap-2 transition-all hover:bg-black/[.03]"
                  style={{
                    background: "transparent",
                    color: "var(--ink)",
                    border: "1px solid var(--line-2)",
                    borderRadius: 6,
                    padding: "10px 18px",
                    fontSize: 14,
                    fontWeight: 500,
                    fontFamily: "var(--sans)",
                    cursor: "pointer",
                  }}
                >
                  <ExternalLink className="h-[15px] w-[15px]" strokeWidth={1.5} />
                  Open deepresearch
                </button>
              </div>

              {/* Hint */}
              <div
                className="mt-8"
                style={{
                  padding: "14px 18px",
                  border: "1px solid var(--line)",
                  borderRadius: 8,
                  background: "var(--paper)",
                  fontSize: 12.5,
                  color: "var(--ink-3)",
                  lineHeight: 1.55,
                }}
              >
                <strong style={{ color: "var(--ink-2)" }}>Workflow:</strong>{" "}
                Click <em>Copy</em>, then <em>Open deepresearch</em>, then paste into the
                deepresearch input. Edits you make here are local — they don&apos;t persist
                back to the engagement (use Stage 2 to refine the MECE structure itself).
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
