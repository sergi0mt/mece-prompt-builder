"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Plus, FileText, LayoutGrid, List, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";
import { Chip, Dot, Logo, ProgressBars, V2_STAGES } from "@/lib/v2/primitives";

function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay === 1) return "yesterday";
  if (diffDay < 7) return `${diffDay}d ago`;
  return `${Math.floor(diffDay / 7)}w ago`;
}

function getProjectStatus(project: Project): "active" | "done" | "archived" {
  if (project.current_stage >= 2) return "done";
  if (project.current_stage === 0) return "archived";
  return "active";
}

function EngagementCard({
  project,
  featured = false,
  onClick,
}: {
  project: Project;
  featured?: boolean;
  onClick: () => void;
}) {
  const status = getProjectStatus(project);
  const stage = Math.max(1, Math.min(2, project.current_stage || 1));
  const stageName = V2_STAGES[stage - 1]?.name ?? "Define Problem";

  const statusTone =
    status === "active" ? "accent" : status === "done" ? "success" : "ghost";

  return (
    <button
      onClick={onClick}
      className="text-left transition-all hover:-translate-y-0.5"
      style={{
        background: "var(--paper)",
        border: "1px solid var(--line)",
        borderRadius: 8,
        padding: 20,
        display: "flex",
        flexDirection: "column",
        gap: 14,
        cursor: "pointer",
        outline: featured
          ? `2px solid color-mix(in oklch, var(--accent) 40%, transparent)`
          : "none",
        outlineOffset: featured ? -2 : 0,
      }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Chip size="xs" tone={statusTone}>
            <Dot color="currentColor" />
            {status}
          </Chip>
          <span style={{ fontSize: 11, color: "var(--ink-3)" }}>
            Updated {formatRelativeTime(project.updated_at)}
          </span>
        </div>
      </div>

      <h3 className="v2-h3 m-0" style={{ minHeight: "2.4em" }}>
        {project.name}
      </h3>

      <div className="flex flex-col gap-1.5">
        <ProgressBars stage={stage} />
        <div
          className="flex items-center justify-between"
          style={{ fontSize: 12, color: "var(--ink-3)" }}
        >
          <span>
            Stage {stage} of 2 — {stageName}
          </span>
          {status === "done" && (
            <span style={{ color: "var(--success)", fontSize: 11 }}>✓ Ready for research</span>
          )}
        </div>
      </div>
    </button>
  );
}

export default function V2Landing() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"grid" | "list">("grid");

  useEffect(() => {
    api.projects
      .list()
      .then((data) => setProjects(data))
      .catch(() => setProjects([]))
      .finally(() => setLoading(false));
  }, []);

  const goToNew = () => router.push("/v2/new");
  const openProject = (id: string) => router.push(`/v2/engagements/${id}`);

  return (
    <div className="flex h-screen w-full flex-col">
      <header
        className="flex shrink-0 items-center justify-between border-b"
        style={{
          padding: "18px 32px",
          borderColor: "var(--line)",
        }}
      >
        <Logo size={18} />
        <div className="flex items-center gap-2.5">
          <div style={{ fontSize: 12, color: "var(--ink-3)" }}>sergio@acme.com</div>
          <div
            className="grid place-items-center"
            style={{
              width: 28,
              height: 28,
              borderRadius: 999,
              background: "var(--ink)",
              color: "var(--paper)",
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            SM
          </div>
        </div>
      </header>

      <section
        className="border-b"
        style={{
          padding: "56px 72px 36px",
          borderColor: "var(--line)",
        }}
      >
        <div className="v2-kicker mb-4">
          Define the problem, structure the MECE, then hand off to deepresearch
        </div>
        <h1
          className="v2-display m-0"
          style={{ maxWidth: 820 }}
        >
          Turn a central question into a MECE research prompt —{" "}
          <em style={{ color: "var(--accent)", fontStyle: "italic" }}>
            ready to drop into deepresearch
          </em>
          .
        </h1>
        <div className="mt-7 flex gap-2.5">
          <button
            onClick={goToNew}
            className="inline-flex items-center gap-2 transition-all hover:opacity-90"
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
            <Plus className="h-[15px] w-[15px]" strokeWidth={1.5} />
            New engagement
          </button>
          <button
            onClick={goToNew}
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
            <FileText className="h-[15px] w-[15px]" strokeWidth={1.5} />
            Import from template
          </button>
          <div className="flex-1" />
          <button
            className="inline-flex items-center gap-2 transition-colors hover:opacity-80"
            style={{
              background: "transparent",
              color: "var(--ink-2)",
              border: "1px solid transparent",
              borderRadius: 6,
              padding: "10px 18px",
              fontSize: 14,
              fontWeight: 500,
              fontFamily: "var(--sans)",
              cursor: "pointer",
            }}
          >
            How it works
            <ArrowRight className="h-[15px] w-[15px]" strokeWidth={1.5} />
          </button>
        </div>
      </section>

      <section
        className="flex-1 overflow-auto"
        style={{ padding: "32px 72px" }}
      >
        <div className="mb-5 flex items-baseline justify-between">
          <div className="flex items-baseline gap-2.5">
            <h2 className="v2-h2 m-0">Engagements</h2>
            <span style={{ fontSize: 13, color: "var(--ink-3)" }}>
              {loading ? "" : `${projects.length} ${projects.length === 1 ? "engagement" : "engagements"}`}
            </span>
          </div>
          <div className="flex gap-1.5">
            <button
              onClick={() => setView("grid")}
              className="inline-flex items-center gap-1.5 transition-colors hover:bg-black/[.03]"
              style={{
                fontSize: 12,
                fontWeight: 500,
                color: view === "grid" ? "var(--ink)" : "var(--ink-3)",
                padding: "5px 10px",
                borderRadius: 6,
                border: "1px solid transparent",
                background: view === "grid" ? "rgba(0,0,0,0.04)" : "transparent",
                cursor: "pointer",
                fontFamily: "var(--sans)",
              }}
            >
              <LayoutGrid className="h-[13px] w-[13px]" strokeWidth={1.5} />
              Grid
            </button>
            <button
              onClick={() => setView("list")}
              className="inline-flex items-center gap-1.5 transition-colors hover:bg-black/[.03]"
              style={{
                fontSize: 12,
                fontWeight: 500,
                color: view === "list" ? "var(--ink)" : "var(--ink-3)",
                padding: "5px 10px",
                borderRadius: 6,
                border: "1px solid transparent",
                background: view === "list" ? "rgba(0,0,0,0.04)" : "transparent",
                cursor: "pointer",
                fontFamily: "var(--sans)",
              }}
            >
              <List className="h-[13px] w-[13px]" strokeWidth={1.5} />
              List
            </button>
          </div>
        </div>

        {loading ? (
          <div
            className="flex items-center justify-center py-20"
            style={{ color: "var(--ink-3)" }}
          >
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            <span style={{ fontSize: 13 }}>Loading engagements…</span>
          </div>
        ) : projects.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center py-20"
            style={{
              border: "1px dashed var(--line-2)",
              borderRadius: 10,
              background: "var(--paper)",
            }}
          >
            <div className="v2-h3 mb-2">No engagements yet</div>
            <p className="mb-5" style={{ fontSize: 13, color: "var(--ink-3)", maxWidth: 420, textAlign: "center" }}>
              Start your first engagement and the AI will guide you through defining the problem and building the MECE structure.
            </p>
            <Button onClick={goToNew} variant="default" size="default" className="rounded-md">
              <Plus className="mr-1.5 h-4 w-4" strokeWidth={1.5} />
              New engagement
            </Button>
          </div>
        ) : (
          <div
            className={
              view === "grid"
                ? "grid grid-cols-1 gap-4 md:grid-cols-2"
                : "flex flex-col gap-2"
            }
          >
            {projects.map((p, i) => (
              <EngagementCard
                key={p.id}
                project={p}
                featured={i === 0 && view === "grid"}
                onClick={() => openProject(p.id)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
