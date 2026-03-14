// ============================================================================
// API Types — mirrors api/app/schemas.py + api/app/constants.py
// ============================================================================

/** Supported sport codes. */
export type Sport = "ncaam_basketball" | "ncaaw_basketball";

/** Available prediction model types. */
export type ModelType =
  | "ensemble"
  | "logistic_regression"
  | "knn"
  | "random_forest"
  | "gradient_boosting"
  | "mlp"
  | "svm";

/** Valid moving-average spans. */
export type Span = 3 | 5 | 7;

// ---------------------------------------------------------------------------
// Teams
// ---------------------------------------------------------------------------

export interface TeamMeta {
  school: string;
  name: string;
  location: string;
  ncaa_key: string | null;
  color: string | null;
}

export interface TeamLatestStats {
  sport: string;
  last_played: string;
  stats: Record<string, number>;
}

export interface Team {
  id: string;
  type: "team";
  sports: string[];
  meta: TeamMeta;
  latest?: TeamLatestStats[] | null;
}

export interface TeamsListResponse {
  data: Team[];
  first_id: string | null;
  last_id: string | null;
  has_more: boolean;
  stats_updated_at: string | null;
}

// ---------------------------------------------------------------------------
// Predictions
// ---------------------------------------------------------------------------

export interface PredictionRequest {
  home_team: string;
  away_team: string;
  span?: Span;
  neutral?: boolean;
  sport?: Sport;
  model?: ModelType;
}

export interface Prediction {
  id: string;
  type: "prediction";
  model: string;
  span: number;
  sport: string;
  home_team: string;
  away_team: string;
  home_last_played: string | null;
  away_last_played: string | null;
  neutral: boolean;
  home_win_probability: number;
  created_at: string | null;
}

export interface PredictionListResponse {
  data: Prediction[];
  first_id: string | null;
  last_id: string | null;
  has_more: boolean;
}

export interface BatchRequest {
  input: PredictionRequest[];
}

export interface BatchResponse {
  type: "prediction_batch";
  output: (Prediction | ErrorResponse)[];
}

// ---------------------------------------------------------------------------
// Analysis
// ---------------------------------------------------------------------------

export interface AnalysisRequest {
  home_team: string;
  away_team: string;
  sport?: Sport;
  neutral?: boolean;
}

export interface AnalysisPredictionSummary {
  span: number;
  home_team: string;
  away_team: string;
  home_win_probability: number;
  neutral: boolean;
}

export interface Analysis {
  id: string;
  type: "analysis";
  home_team: string;
  away_team: string;
  sport: string;
  neutral: boolean;
  predictions: AnalysisPredictionSummary[];
  home_stats: Record<string, number>;
  away_stats: Record<string, number>;
  home_last_played: string;
  away_last_played: string;
  analysis: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Rankings
// ---------------------------------------------------------------------------

export interface RankingEntry {
  rank: number;
  team: string;
  rating: number;
}

export interface RankingsResponse {
  sport: string;
  updated_at: string;
  rankings: RankingEntry[];
}

// ---------------------------------------------------------------------------
// Tournaments
// ---------------------------------------------------------------------------

export interface PlayInGame {
  slot: string;
  region: string;
  seed: number;
  teams: string[];
  result: string | null;
}

export interface RegionDef {
  name: string;
  seeds: Record<string, string | null>;
}

export interface FinalFourDef {
  semifinal_1: [string, string];
  semifinal_2: [string, string];
}

export interface TournamentSummary {
  id: string;
  name: string;
  year: number;
  sport: string;
  lock_date: string;
  is_locked: boolean;
}

export interface TournamentListResponse {
  data: TournamentSummary[];
}

export interface Tournament {
  id: string;
  type: "tournament";
  name: string;
  year: number;
  sport: string;
  lock_date: string;
  is_locked: boolean;
  play_in: PlayInGame[];
  regions: Record<string, RegionDef>;
  final_four: FinalFourDef;
  results: Record<string, string>;
}

// ---------------------------------------------------------------------------
// Brackets
// ---------------------------------------------------------------------------

export interface CreateBracketRequest {
  tournament_id: string;
  name: string;
  picks: Record<string, string>;
}

export interface UpdateBracketRequest {
  name?: string;
  picks?: Record<string, string>;
}

export interface Bracket {
  id: string;
  type: "bracket";
  tournament_id: string;
  name: string;
  picks: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface BracketListResponse {
  data: Bracket[];
}

// ---------------------------------------------------------------------------
// Errors / Health
// ---------------------------------------------------------------------------

export interface ErrorDetail {
  code: string;
  message: string;
}

export interface ErrorResponse {
  type: "error";
  error: ErrorDetail;
}

export interface HealthResponse {
  status: "healthy" | "unhealthy";
}
