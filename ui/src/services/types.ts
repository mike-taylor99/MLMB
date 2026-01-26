// Request type for POST /predictions
export interface PredictionRequest {
  team1: string;
  team2: string;
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
  team1: string;
  team1_probability: number;
  team1_last_played: string;
  team2: string;
  team2_probability: number;
  team2_last_played: string;
  winner: "team1" | "team2";
  confidence: number;
  span: 3 | 5 | 7;
  neutral: boolean;
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
