// Sport type
export type Sport = "ncaam_basketball" | "ncaaw_basketball";

// Request type for POST /predictions
export interface PredictionRequest {
  home_team: string;
  away_team: string;
  span?: 3 | 5 | 7;
  neutral?: boolean;
  sport?: Sport;
  model?:
    | "ensemble"
    | "logistic_regression"
    | "knn"
    | "random_forest"
    | "gradient_boosting"
    | "mlp"
    | "svm";
}

// Response type for POST /predictions and GET /predictions/{id}
export interface PredictionResponse {
  id: string;
  type: "prediction";
  model: string;
  span: 3 | 5 | 7;
  sport: Sport;
  home_team: string;
  away_team: string;
  home_last_played: string;
  away_last_played: string;
  neutral: boolean;
  home_win_probability: number;
  created_at: string;
}

// Response type for GET /predictions (history) - cursor pagination
export interface PredictionsListResponse {
  data: PredictionResponse[];
  has_more: boolean;
  first_id: string | null;
  last_id: string | null;
}

// Query parameters for GET /predictions (history)
export interface PredictionsHistoryQuery {
  sport: Sport;
  home_team?: string;
  away_team?: string;
  model_version?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  before_id?: string;
  after_id?: string;
}

// Response type for GET /rankings/{sport}
export interface RankingsResponse {
  sport: Sport;
  updated_at: string;
  rankings: RankingEntry[];
}

export interface RankingEntry {
  rank: number;
  team: string;
  rating: number;
}

// Legacy types for backward compatibility during migration
/** @deprecated Use PredictionRequest instead */
export interface MatchupInput {
  model: string;
  isNeutral: boolean;
  team1: string;
  team2: string;
  isWomens?: boolean;
}

/** @deprecated Use PredictionResponse instead */
export interface MatchupOutput extends MatchupInput {
  predict: number[];
  predictProba: number[];
  team1LastPlayed: string;
  team2LastPlayed: string;
}
