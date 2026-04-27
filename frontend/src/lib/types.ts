// TypeScript types for MECE Prompt Builder

export interface Project {
  id: string;
  name: string;
  description: string | null;
  audience: string;
  deck_type: string;
  engagement_type: string | null;
  created_at: string;
  updated_at: string;
  upload_count: number;
  slide_count: number;
  current_stage: number;
}

export interface Upload {
  id: string;
  project_id: string;
  filename: string;
  file_size: number | null;
  content_type: string | null;
  has_extracted_text: boolean;
  created_at: string;
}

export interface Session {
  id: string;
  project_id: string;
  current_stage: number;
  stage_data: Record<string, unknown>;
  created_at: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  stage: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export const STAGE_NAMES: Record<number, string> = {
  0: "Not Started",
  1: "Define Problem",
  2: "MECE Structure",
};

export const AUDIENCE_OPTIONS = [
  { value: "board", label: "Board / C-suite" },
  { value: "client", label: "Client (external)" },
  { value: "working_team", label: "Working Team" },
  { value: "steering", label: "Steering Committee" },
];

export const DECK_TYPE_OPTIONS = [
  { value: "strategic", label: "Strategic Recommendation" },
  { value: "diagnostic", label: "Diagnostic / Problem Analysis" },
  { value: "market_entry", label: "Market Entry Assessment" },
  { value: "due_diligence", label: "Due Diligence" },
  { value: "transformation", label: "Transformation" },
  { value: "progress_update", label: "Progress Update" },
  { value: "implementation", label: "Implementation Plan" },
];

export interface EngagementTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  default_audience: string;
  default_output_formats: string[];
  research_question_count: number;
  slide_range_min: number;
  slide_range_max: number;
}

export interface HandoffResponse {
  prompt: string;
  char_count: number;
  truncated: boolean;
}
