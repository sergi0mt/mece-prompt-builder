"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { Chip, Logo } from "@/lib/v2/primitives";

// ────────────────────────────────────────────────────────────────
// Templates — mirror of design_handoff/src/deeper-views.jsx + backend
//
// IDs map to the backend's engagement_templates.py (where applicable).
// "blank" creates a project without a template.
// ────────────────────────────────────────────────────────────────

type Template = {
  id: string;
  name: string;
  desc: string;
  count: number | null;
  branches: string[];
  featured?: boolean;
  blank?: boolean;
  /** ID to send to backend on project creation (undefined = blank). */
  backendId?: string;
};

const TEMPLATES: Template[] = [
  {
    id: "market_entry",
    backendId: "market_entry",
    name: "Market Entry",
    desc: "Should we enter market X?",
    count: 14,
    branches: ["Attractiveness", "Right to win", "Investment case"],
    featured: true,
  },
  {
    id: "diagnostic",
    backendId: "performance_improvement",
    name: "Diagnostic",
    desc: "Why is performance off plan?",
    count: 12,
    branches: ["Symptoms", "Root causes", "Path to fix"],
  },
  {
    id: "cost_reduction",
    backendId: "performance_improvement",
    name: "Cost Reduction",
    desc: "Where can we take out 20%?",
    count: 16,
    branches: ["Cost baseline", "Levers by category", "Implementation"],
  },
  {
    id: "growth_strategy",
    backendId: "strategic_assessment",
    name: "Growth Strategy",
    desc: "How do we double in 3 years?",
    count: 18,
    branches: ["Where to play", "How to win", "How to fund"],
  },
  {
    id: "digital_transformation",
    backendId: "transformation",
    name: "Digital Transformation",
    desc: "What's our 2-yr digital agenda?",
    count: 22,
    branches: ["Capability gaps", "Use cases", "Operating model"],
  },
  {
    id: "due_diligence",
    backendId: "commercial_due_diligence",
    name: "Due Diligence",
    desc: "Should we acquire this target?",
    count: 20,
    branches: ["Commercial", "Operational", "Financial"],
  },
  {
    id: "transformation",
    backendId: "transformation",
    name: "Transformation",
    desc: "Multi-year change program",
    count: 24,
    branches: ["Aspiration", "Initiatives", "Governance"],
  },
  {
    id: "progress_update",
    backendId: "strategic_assessment",
    name: "Progress Update",
    desc: "Where are we on the program?",
    count: 8,
    branches: ["Status", "Risks", "Decisions"],
  },
  {
    id: "implementation",
    backendId: "transformation",
    name: "Implementation",
    desc: "How do we deliver?",
    count: 16,
    branches: ["Workstreams", "Milestones", "Risks"],
  },
  {
    id: "blank",
    name: "Blank engagement",
    desc: "Start from scratch — define your own MECE",
    count: null,
    branches: [],
    blank: true,
  },
];

// ────────────────────────────────────────────────────────────────
// Template Card
// ────────────────────────────────────────────────────────────────

function TemplateCard({
  template,
  onClick,
}: {
  template: Template;
  onClick: () => void;
}) {
  const isFeatured = !!template.featured;
  const isBlank = !!template.blank;

  return (
    <button
      onClick={onClick}
      className="text-left transition-all hover:-translate-y-0.5"
      style={{
        padding: "20px 22px",
        background: isFeatured ? "var(--ink)" : "var(--paper)",
        color: isFeatured ? "var(--paper)" : "var(--ink)",
        border: isFeatured
          ? "1px solid var(--ink)"
          : isBlank
            ? "1px dashed var(--line-2)"
            : "1px solid var(--line)",
        borderRadius: 10,
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        gap: 10,
        minHeight: 180,
        opacity: isBlank ? 0.85 : 1,
      }}
    >
      {/* Top row: ID + recommended chip */}
      <div className="flex items-center justify-between">
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 10,
            letterSpacing: 1.2,
            color: isFeatured
              ? "rgba(255,253,247,0.55)"
              : "var(--ink-3)",
          }}
        >
          {template.id.toUpperCase()}
        </span>
        {isFeatured && (
          <Chip size="xs" tone="accent">
            recommended
          </Chip>
        )}
      </div>

      {/* Name */}
      <div
        style={{
          fontFamily: "var(--serif)",
          fontSize: 22,
          letterSpacing: -0.4,
          lineHeight: 1.15,
          fontWeight: 400,
        }}
      >
        {template.name}
      </div>

      {/* Description (italic example question) */}
      <div
        style={{
          fontSize: 12.5,
          color: isFeatured
            ? "rgba(255,253,247,0.65)"
            : "var(--ink-3)",
          fontStyle: "italic",
        }}
      >
        &ldquo;{template.desc}&rdquo;
      </div>

      {/* Footer: branch list (only for non-blank) */}
      {!isBlank && (
        <div
          className="mt-auto pt-2.5"
          style={{
            borderTop:
              "1px solid " +
              (isFeatured ? "rgba(255,253,247,0.12)" : "var(--line)"),
          }}
        >
          <div
            className="mb-1.5"
            style={{
              fontFamily: "var(--mono)",
              fontSize: 10,
              letterSpacing: 1,
              color: isFeatured
                ? "rgba(255,253,247,0.5)"
                : "var(--ink-4)",
            }}
          >
            3 BRANCHES · ~{template.count} slides
          </div>
          <div
            style={{
              fontSize: 11.5,
              lineHeight: 1.5,
              color: isFeatured
                ? "rgba(255,253,247,0.85)"
                : "var(--ink-2)",
            }}
          >
            {template.branches.join(" · ")}
          </div>
        </div>
      )}
    </button>
  );
}

// ────────────────────────────────────────────────────────────────
// Main page — Templates browser
// ────────────────────────────────────────────────────────────────

export default function V2NewEngagement() {
  const router = useRouter();
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  function handleSelect(template: Template) {
    setSelectedTemplate(template);
    // Suggest a sensible default name based on the template
    if (!name) {
      const today = new Date().toLocaleDateString("en-US", {
        month: "short",
        year: "numeric",
      });
      setName(`${template.name} — ${today}`);
    }
  }

  async function handleCreate() {
    if (!selectedTemplate || !name.trim()) {
      toast.error("Engagement name is required");
      return;
    }
    setCreating(true);
    try {
      const project = await api.projects.create({
        name: name.trim(),
        description: description.trim() || undefined,
        engagement_type: selectedTemplate.backendId,
      });
      toast.success("Engagement created");
      router.push(`/v2/engagements/${project.id}`);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to create engagement",
      );
      setCreating(false);
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
          <button
            onClick={() => router.push("/v2")}
            className="inline-flex items-center gap-1.5 transition-opacity hover:opacity-70"
            style={{
              background: "transparent",
              color: "var(--ink-2)",
              border: "1px solid transparent",
              borderRadius: 6,
              padding: "5px 10px",
              fontSize: 12,
              fontWeight: 500,
              fontFamily: "var(--sans)",
              cursor: "pointer",
            }}
          >
            <ArrowLeft className="h-[13px] w-[13px]" strokeWidth={1.5} />
            Back
          </button>
          <Logo size={14} />
          <span style={{ color: "var(--ink-4)" }}>/</span>
          <span
            style={{
              fontSize: 13,
              fontFamily: "var(--serif)",
            }}
          >
            New engagement · pick a template
          </span>
        </div>
        <button
          onClick={() => handleSelect(TEMPLATES.find((t) => t.id === "blank")!)}
          className="transition-opacity hover:opacity-70"
          style={{
            background: "transparent",
            color: "var(--ink-2)",
            border: "1px solid transparent",
            borderRadius: 6,
            padding: "5px 10px",
            fontSize: 12,
            fontWeight: 500,
            fontFamily: "var(--sans)",
            cursor: "pointer",
          }}
        >
          Skip — blank
        </button>
      </header>

      {/* ── Body ───────────────────────────────────────── */}
      <section
        className="flex-1 overflow-auto"
        style={{ padding: "44px 56px" }}
      >
        <div className="v2-kicker mb-2">
          9 archetypes · calibrated from 37 real decks
        </div>
        <h1 className="v2-h1 m-0 mb-2">
          What kind of engagement is this?
        </h1>
        <p
          className="mb-9 mt-0"
          style={{
            fontSize: 14,
            color: "var(--ink-3)",
            maxWidth: 580,
          }}
        >
          Each template seeds a MECE structure, recommended chart types, and an
          action-title formula tuned to the audience. You can always edit the
          tree.
        </p>

        <div
          className="grid gap-3.5"
          style={{
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          }}
        >
          {TEMPLATES.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              onClick={() => handleSelect(template)}
            />
          ))}
        </div>
      </section>

      {/* ── Name dialog (shown after picking a template) ── */}
      <Dialog
        open={!!selectedTemplate}
        onOpenChange={(open) => !open && !creating && setSelectedTemplate(null)}
      >
        <DialogContent className="v2-theme sm:max-w-md">
          <DialogHeader>
            <DialogTitle
              className="m-0"
              style={{
                fontFamily: "var(--serif)",
                fontSize: 22,
                letterSpacing: -0.3,
                fontWeight: 400,
              }}
            >
              {selectedTemplate?.name}
            </DialogTitle>
            {selectedTemplate && (
              <p
                className="m-0"
                style={{
                  fontSize: 12.5,
                  color: "var(--ink-3)",
                  fontStyle: "italic",
                }}
              >
                &ldquo;{selectedTemplate.desc}&rdquo;
              </p>
            )}
          </DialogHeader>

          <div className="flex flex-col gap-4 py-2">
            <div>
              <label
                className="mb-1.5 block"
                style={{
                  fontSize: 11,
                  letterSpacing: 1.2,
                  textTransform: "uppercase",
                  color: "var(--ink-3)",
                  fontFamily: "var(--mono)",
                }}
              >
                Engagement name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., LatAm Market Entry — Acme Corp"
                autoFocus
                className="w-full"
                style={{
                  fontFamily: "var(--serif)",
                  fontSize: 18,
                  letterSpacing: -0.2,
                }}
              />
            </div>
            <div>
              <label
                className="mb-1.5 block"
                style={{
                  fontSize: 11,
                  letterSpacing: 1.2,
                  textTransform: "uppercase",
                  color: "var(--ink-3)",
                  fontFamily: "var(--mono)",
                }}
              >
                Description (optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief context — client, time horizon, key constraints…"
                rows={3}
                className="w-full"
              />
            </div>
          </div>

          <DialogFooter className="flex justify-between gap-2">
            <button
              onClick={() => setSelectedTemplate(null)}
              disabled={creating}
              className="transition-opacity hover:opacity-70 disabled:opacity-50"
              style={{
                background: "transparent",
                color: "var(--ink-2)",
                border: "1px solid var(--line-2)",
                borderRadius: 6,
                padding: "8px 14px",
                fontSize: 13,
                fontWeight: 500,
                fontFamily: "var(--sans)",
                cursor: creating ? "not-allowed" : "pointer",
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={creating || !name.trim()}
              className="inline-flex items-center gap-2 transition-opacity hover:opacity-90 disabled:opacity-50"
              style={{
                background: "var(--ink)",
                color: "var(--paper)",
                border: "1px solid var(--ink)",
                borderRadius: 6,
                padding: "8px 14px",
                fontSize: 13,
                fontWeight: 500,
                fontFamily: "var(--sans)",
                cursor: creating || !name.trim() ? "not-allowed" : "pointer",
              }}
            >
              {creating ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.5} />
              )}
              Create engagement
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
