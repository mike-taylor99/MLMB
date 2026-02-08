// ============================================================================
// API Types — mirrors api/app/schemas.py + api/app/constants.py
// ============================================================================

/** Supported sport codes. */
export type Sport = 'ncaam_basketball' | 'ncaaw_basketball'

/** Available prediction model types. */
export type ModelType =
  | 'ensemble'
  | 'logistic_regression'
  | 'knn'
  | 'random_forest'
  | 'gradient_boosting'
  | 'mlp'
  | 'svm'

/** Valid moving-average spans. */
export type Span = 3 | 5 | 7

// ---------------------------------------------------------------------------
// Teams
// ---------------------------------------------------------------------------

export interface TeamMeta {
  school: string
  name: string
  location: string
  ncaa_key: string | null
  color: string | null
}

export interface Team {
  id: string
  type: 'team'
  sports: string[]
  meta: TeamMeta
}

export interface TeamsListResponse {
  data: Team[]
  first_id: string | null
  last_id: string | null
  has_more: boolean
}

// ---------------------------------------------------------------------------
// Predictions
// ---------------------------------------------------------------------------

export interface PredictionRequest {
  home_team: string
  away_team: string
  span?: Span
  neutral?: boolean
  sport?: Sport
  model?: ModelType
}

export interface Prediction {
  id: string
  type: 'prediction'
  model: string
  span: number
  sport: string
  home_team: string
  away_team: string
  home_last_played: string | null
  away_last_played: string | null
  neutral: boolean
  home_win_probability: number
  created_at: string | null
}

export interface PredictionListResponse {
  data: Prediction[]
  first_id: string | null
  last_id: string | null
  has_more: boolean
}

export interface BatchRequest {
  input: PredictionRequest[]
}

export interface BatchResponse {
  type: 'prediction_batch'
  output: (Prediction | ErrorResponse)[]
}

// ---------------------------------------------------------------------------
// Rankings
// ---------------------------------------------------------------------------

export interface RankingEntry {
  rank: number
  team: string
  rating: number
}

export interface RankingsResponse {
  sport: string
  updated_at: string
  rankings: RankingEntry[]
}

// ---------------------------------------------------------------------------
// Errors / Health
// ---------------------------------------------------------------------------

export interface ErrorDetail {
  code: string
  message: string
}

export interface ErrorResponse {
  type: 'error'
  error: ErrorDetail
}

export interface HealthResponse {
  status: 'healthy' | 'unhealthy'
}
