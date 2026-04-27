import type { Metadata } from "next";
import { Instrument_Serif, Inter, JetBrains_Mono } from "next/font/google";
import "./globals-v2.css";

const instrumentSerif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-instrument-serif",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Engagement Manager",
  description: "Turn a central question into a board-ready deck — with the rigor of a Monday-morning partner review.",
};

export default function V2Layout({ children }: { children: React.ReactNode }) {
  return (
    <div
      className={`v2-theme ${instrumentSerif.variable} ${inter.variable} ${jetbrainsMono.variable} min-h-screen`}
      style={{
        // Override the font-family CSS vars to point at the loaded Google fonts.
        // The CSS uses --serif/--sans/--mono; we map them to the Next.js variables.
        ["--serif" as string]: `var(--font-instrument-serif), 'Times New Roman', serif`,
        ["--sans" as string]: `var(--font-inter), -apple-system, sans-serif`,
        ["--mono" as string]: `var(--font-jetbrains-mono), 'Menlo', monospace`,
      }}
    >
      {children}
    </div>
  );
}
