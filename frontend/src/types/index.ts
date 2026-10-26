export type UserRole = "ADMIN" | "TEACHER" | "RESEARCHER";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  institution?: string | null;
  institution_code?: string | null;
  department?: string | null;
  designation?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export type PaperStatus = "UPLOADED" | "EXTRACTED" | "ANALYZED" | "REVIEWED" | "ARCHIVED";

export interface Prediction {
  id: number;
  analysis_run_id: number;
  question_id: number;
  predicted_blooms_level: string;
  blooms_confidence: number;
  blooms_probabilities?: Record<string, number> | null;
  predicted_difficulty: string;
  difficulty_confidence: number;
  difficulty_probabilities?: Record<string, number> | null;
  continuous_difficulty_score?: number | null;
  created_at: string;
}

export interface TeacherCorrection {
  id: number;
  question_id: number;
  teacher_id: number;
  original_blooms_level?: string | null;
  corrected_blooms_level: string;
  original_difficulty?: string | null;
  corrected_difficulty: string;
  corrected_marks?: number | null;
  corrected_text?: string | null;
  rationale?: string | null;
  created_at: string;
}

export interface Question {
  id: number;
  paper_id: number;
  section_id?: number | null;
  section_name?: string | null;
  question_number: string;
  question_text: string;
  marks?: number | null;
  page_number?: number | null;
  order_index: number;
  is_reviewed_by_teacher: boolean;
  predictions: Prediction[];
  corrections: TeacherCorrection[];
  effective_blooms_level?: string | null;
  effective_difficulty?: string | null;
}

export interface Section {
  id: number;
  paper_id: number;
  section_name: string;
  order_index: number;
  created_at: string;
}

export interface AnalysisRun {
  id: number;
  paper_id: number;
  triggered_by_user_id: number;
  model_version: string;
  bloom_model_name: string;
  difficulty_model_name: string;
  execution_duration_ms: number;
  status: string;
  created_at: string;
}

export interface Paper {
  id: number;
  owner_id: number;
  title: string;
  subject: string;
  academic_year?: string | null;
  term?: string | null;
  original_filename: string;
  file_type: string;
  file_size_bytes: number;
  total_marks?: number | null;
  status: PaperStatus;
  total_questions?: number;
  created_at: string;
  updated_at: string;
}

export interface PaperDetail extends Paper {
  sections: Section[];
  questions: Question[];
  latest_analysis_run?: AnalysisRun | null;
  extraction_metadata?: string | null;
}

export interface CognitiveDistributionItem {
  count: number;
  percentage: number;
  marks: number;
  marks_percentage: number;
}

export interface DifficultyDistributionItem {
  count: number;
  percentage: number;
  marks: number;
  marks_percentage: number;
}

export interface PaperAnalytics {
  paper_id: number;
  paper_title: string;
  total_questions: number;
  total_marks: number;
  average_difficulty_score: number;
  overall_difficulty_rating: string;
  reviewed_questions_count: number;
  review_progress_percentage: number;
  blooms_distribution: Record<string, CognitiveDistributionItem>;
  difficulty_distribution: Record<string, DifficultyDistributionItem>;
  section_breakdown: Array<{
    section_name: string;
    questions_count: number;
    total_marks: number;
  }>;
}

export interface SystemHealth {
  status: string;
  project_name: string;
  version: string;
  environment: string;
  timestamp: string;
  system_info: {
    python_version?: string;
    platform?: string;
    debug_mode?: boolean;
    uptime?: string;
  };
  database_status: string;
  database_engine?: string;
}

export interface ResearchMetrics {
  metadata: {
    version: string;
    model_type: string;
    blooms_champion: string;
    difficulty_champion: string;
    blooms_test_accuracy: number;
    blooms_test_macro_f1: number;
    difficulty_test_accuracy: number;
    difficulty_test_macro_f1: number;
    blooms_classes: string[];
    difficulty_classes: string[];
  };
  task_a_blooms: any;
  task_b_difficulty: any;
}
