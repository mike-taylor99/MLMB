import { IMatchupFormInput } from "./models";

export const EMPTY_FORM_MATCHUP: IMatchupFormInput = {
  home_team: "",
  away_team: "",
  span: 3,
  neutral: true,
  sport: "ncaam_basketball",
  model: "ensemble",
};

// Model options for dropdown
export const MODEL_OPTIONS = [
  { key: "ensemble", text: "Ensemble (All Models)" },
  { key: "logistic_regression", text: "Logistic Regression" },
  { key: "knn", text: "K-Nearest Neighbors" },
  { key: "random_forest", text: "Random Forest" },
  { key: "gradient_boosting", text: "Gradient Boosting" },
  { key: "mlp", text: "Neural Network (MLP)" },
  { key: "svm", text: "Support Vector Machine" },
];

// Span options for dropdown
export const SPAN_OPTIONS = [
  { key: 3, text: "3-Game Window" },
  { key: 5, text: "5-Game Window" },
  { key: 7, text: "7-Game Window" },
];
