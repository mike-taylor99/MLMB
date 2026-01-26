export interface ITeam {
  School: string;
  ["City, State"]: string;
  ["SR key"]: string;
  ["NCAA key"]?: string;
  ["NCAA School"]?: string;
  ["NCAA Name"]?: string;
  ["background-color"]?: string;
  isMenTeam?: boolean;
  isWomenTeam?: boolean;
}

// New form input matching the API contract
export interface IMatchupFormInput {
  team1: string;
  team2: string;
  span: 3 | 5 | 7;
  neutral: boolean;
  gender: "men" | "women";
  model:
    | "ensemble"
    | "logistic_regression"
    | "knn"
    | "random_forest"
    | "gradient_boosting"
    | "mlp"
    | "svm";
}
