// Request type for POST /predictions
export interface PredictionRequest {
  home_team: string;
  away_team: string;
  span?: 3 | 5 | 7;
  neutral?: boolean;
  gender?: "men" | "women";
  model?:
    | "ensemble"
    | "logistic_regression"
    | "knn"
    | "random_forest"
    | "gradient_boosting"
    | "mlp"
    | "svm";
}

// Response type for POST /predictions
export interface PredictionResponse {
  home_team: string;
  away_team: string;
  home_win_probability: number;
  home_last_played: string;
  away_last_played: string;
  predicted_winner: string;
  neutral: boolean;
  span: 3 | 5 | 7;
  gender: "men" | "women";
  model: string;
}

// Response type for GET /rankings/{gender}
export interface RankingsResponse {
  gender: "men" | "women";
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
