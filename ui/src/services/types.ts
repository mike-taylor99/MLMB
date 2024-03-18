export interface MatchupInput {
  model: string;
  isNeutral: boolean;
  team1: string;
  team2: string;
  isWomens?: boolean;
}

export interface MatchupOutput extends MatchupInput {
  predict: number[];
  predictProba: number[];
  team1LastPlayed: string;
  team2LastPlayed: string;
}
