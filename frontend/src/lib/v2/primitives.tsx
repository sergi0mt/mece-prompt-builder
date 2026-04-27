/**
 * V2 UI primitives — Logo, Chip, Dot, Divider, TierBadge, ProgressBars.
 *
 * Built on the V2 design tokens (CSS variables in globals-v2.css).
 */
"use client";

import { cn } from "@/lib/utils";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

// ────────────────────────────────────────────────────────────────
// Logo
// ────────────────────────────────────────────────────────────────

export function Logo({ size = 16, className }: { size?: number; className?: string }) {
  const fontSize = size + 4;
  return (
    <div className={cn("inline-flex items-center gap-2", className)}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        className="shrink-0"
        style={{ color: "var(--ink)" }}
      >
        <rect x="2" y="2" width="9" height="20" fill="currentColor" />
        <rect x="13" y="2" width="9" height="9" fill="currentColor" opacity="0.55" />
        <rect x="13" y="13" width="9" height="9" fill="currentColor" opacity="0.85" />
      </svg>
      <span
        className="leading-none"
        style={{
          fontFamily: "var(--serif)",
          fontSize: `${fontSize}px`,
          letterSpacing: "-0.3px",
          color: "var(--ink)",
        }}
      >
        MECE<span className="italic"> Prompt Builder</span>
      </span>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// Chip
// ────────────────────────────────────────────────────────────────

type ChipTone = "default" | "accent" | "success" | "warn" | "danger" | "ghost" | "ink";
type ChipSize = "xs" | "sm";

const CHIP_TONE_STYLES: Record<ChipTone, { bg: string; color: string; border: string }> = {
  default: {
    bg: "rgba(0,0,0,0.04)",
    color: "var(--ink-2)",
    border: "1px solid var(--line)",
  },
  accent: {
    bg: "var(--accent-soft)",
    color: "var(--accent)",
    border: "1px solid color-mix(in oklch, var(--accent) 20%, transparent)",
  },
  success: {
    bg: "color-mix(in oklch, var(--success) 12%, transparent)",
    color: "var(--success)",
    border: "1px solid color-mix(in oklch, var(--success) 30%, transparent)",
  },
  warn: {
    bg: "color-mix(in oklch, var(--warn) 14%, transparent)",
    color: "color-mix(in oklch, var(--warn) 65%, black)",
    border: "1px solid color-mix(in oklch, var(--warn) 30%, transparent)",
  },
  danger: {
    bg: "color-mix(in oklch, var(--danger) 10%, transparent)",
    color: "var(--danger)",
    border: "1px solid color-mix(in oklch, var(--danger) 30%, transparent)",
  },
  ghost: {
    bg: "transparent",
    color: "var(--ink-3)",
    border: "1px solid var(--line)",
  },
  ink: {
    bg: "var(--ink)",
    color: "var(--paper)",
    border: "1px solid var(--ink)",
  },
};

export function Chip({
  children,
  tone = "default",
  size = "sm",
  className,
  ...rest
}: {
  children: ReactNode;
  tone?: ChipTone;
  size?: ChipSize;
  className?: string;
} & Omit<ComponentPropsWithoutRef<"span">, "children">) {
  const style = CHIP_TONE_STYLES[tone];
  const sizeStyles =
    size === "xs"
      ? { padding: "1px 6px", fontSize: 10, letterSpacing: 0.4 }
      : { padding: "3px 8px", fontSize: 11, letterSpacing: 0.3 };

  return (
    <span
      {...rest}
      className={cn(
        "inline-flex items-center gap-1 whitespace-nowrap rounded-full font-medium uppercase",
        className,
      )}
      style={{
        ...sizeStyles,
        background: style.bg,
        color: style.color,
        border: style.border,
        fontFamily: "var(--sans)",
      }}
    >
      {children}
    </span>
  );
}

// ────────────────────────────────────────────────────────────────
// Dot
// ────────────────────────────────────────────────────────────────

export function Dot({
  color = "var(--ink-3)",
  size = 6,
  className,
}: {
  color?: string;
  size?: number;
  className?: string;
}) {
  return (
    <span
      aria-hidden
      className={cn("inline-block rounded-full", className)}
      style={{ width: size, height: size, background: color }}
    />
  );
}

// ────────────────────────────────────────────────────────────────
// Divider
// ────────────────────────────────────────────────────────────────

export function Divider({ label, className }: { label?: string; className?: string }) {
  if (!label) {
    return <div className={cn("h-px w-full", className)} style={{ background: "var(--line)" }} />;
  }
  return (
    <div
      className={cn("flex items-center gap-2.5", className)}
      style={{
        color: "var(--ink-4)",
        fontSize: 10,
        letterSpacing: 1.4,
        textTransform: "uppercase",
        fontFamily: "var(--mono)",
      }}
    >
      <div className="h-px flex-1" style={{ background: "var(--line)" }} />
      <span>{label}</span>
      <div className="h-px flex-1" style={{ background: "var(--line)" }} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// TierBadge
// ────────────────────────────────────────────────────────────────

export function TierBadge({ tier }: { tier: 1 | 2 | 3 }) {
  const tones: Record<1 | 2 | 3, ChipTone> = { 1: "success", 2: "accent", 3: "ghost" };
  const labels: Record<1 | 2 | 3, string> = { 1: "Tier 1", 2: "Tier 2", 3: "Tier 3" };
  return (
    <Chip size="xs" tone={tones[tier]}>
      {labels[tier]}
    </Chip>
  );
}

// ────────────────────────────────────────────────────────────────
// ProgressBars — 2-stage progress bar (used on engagement cards)
// ────────────────────────────────────────────────────────────────

export function ProgressBars({ stage, total = 2 }: { stage: number; total?: number }) {
  return (
    <div className="flex gap-1">
      {Array.from({ length: total }, (_, i) => i + 1).map((n) => (
        <div
          key={n}
          className="h-[3px] flex-1 rounded-[2px]"
          style={{
            background: n <= stage ? "var(--ink)" : "var(--line)",
          }}
        />
      ))}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
// Stage names — 2 stages
// ────────────────────────────────────────────────────────────────

export const V2_STAGES = [
  { n: 1, name: "Define Problem", sub: "Central question & audience" },
  { n: 2, name: "MECE Structure", sub: "Issue tree & branches" },
] as const;
