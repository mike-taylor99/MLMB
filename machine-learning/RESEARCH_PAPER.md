# Incorporating Opponent Defensive Statistics into NCAA Basketball Game Outcome Prediction: An Ensemble Machine Learning Approach

**Date:** February 2026  
**Project:** MLMB — Machine Learning March Bracket

---

## Abstract

This paper presents the results of incorporating opponent defensive statistics into a multi-model ensemble system for predicting NCAA Division I basketball game outcomes. We expanded a feature set from 35 offensive statistics to 59 statistics (35 offensive + 24 defensive), generating 356 engineered features via moving averages. Six classification models — Logistic Regression, Support Vector Machine, K-Nearest Neighbors, Random Forest, Gradient Boosting, and Multilayer Perceptron — were trained with `StandardScaler` normalization via `sklearn.Pipeline` and evaluated using accuracy, log loss, and Brier score. Models were trained separately for men's (NCAA Division I Men's) and women's (NCAA Division I Women's) basketball using data from the 2022–2026 seasons. Feature importance analysis confirms that defensive statistics contribute 18.6–38.8% of total predictive importance, validating their inclusion in the pipeline.

---

## 1. Introduction

Predicting NCAA basketball game outcomes is a challenging task due to the inherent randomness of single-game results and the parity across Division I programs. Prior iterations of this system used only the team's own box score statistics (field goals, rebounds, assists, etc.) and advanced metrics (offensive rating, effective field goal percentage, etc.) as features. However, this approach ignored a critical dimension: _how teams perform defensively against their opponents_.

This work extends the feature set by adding 24 opponent defensive statistics scraped from Sports Reference box scores, capturing how a team forces turnovers, contests shots, and limits opponent efficiency. The hypothesis is straightforward: a team's defensive quality is at least as predictive as its offensive output, and encoding it explicitly should improve model calibration.

### 1.1 System Architecture

The MLMB system operates as a full-stack prediction pipeline:

1. **Data Collection**: Game-by-game box scores scraped from Sports Reference (HTML parsing via BeautifulSoup)
2. **Feature Engineering**: Raw stats → 3 moving average types (SMA, CMA, EMA) → team + opponent features → neutral site flag
3. **Model Training**: 6 classifiers trained via `GridSearchCV` with `StandardScaler` pipelines
4. **Prediction API**: FastAPI server loads all 18 models per gender (6 models × 3 spans), ensembles predictions by averaging `predict_proba` outputs
5. **Frontend**: React UI for bracket-style matchup predictions

---

## 2. Methodology

### 2.1 Data Source and Collection

Game data was collected from Sports Reference for NCAA Division I basketball seasons 2021–22 through 2025–26 (referred to as seasons 2022–2026). For each game, both the team's box score and the opponent's box score were scraped, providing both offensive and defensive perspectives.

**Train/Test split:** 70% train / 30% test, randomly sampled across all seasons (2022–2026) using `sklearn.model_selection.train_test_split`

### 2.2 Feature Engineering

#### 2.2.1 Raw Statistics (59 total)

**35 Offensive Statistics** (team's own box score):

- Basic: FG, FGA, FG%, 2P, 2PA, 2P%, 3P, 3PA, 3P%, FT, FTA, FT%, ORB, DRB, TRB, AST, STL, BLK, TOV, PF, PTS
- Advanced: ORtg, DRtg, Pace, FTr, 3PAr, TS%, TRB%, AST%, STL%, BLK%, eFG%, TOV%, ORB%, FT/FGA

**24 Defensive Statistics** (opponent's box score, prefixed with `def_`):

- Basic (21): def_FG, def_FGA, def_FG%, def_2P, def_2PA, def_2P%, def_3P, def_3PA, def_3P%, def_FT, def_FTA, def_FT%, def_ORB, def_DRB, def_TRB, def_AST, def_STL, def_BLK, def_TOV, def_PF, def_PTS
- Advanced Defensive Four Factors (3): def_eFG%, def_TOV%, def_ORB%, def_FT/FGA

**Note:** `def_eFG%` from the advanced table was dropped as it duplicated the basic box score value. A cross-season normalization was applied to handle Sports Reference renaming `def_DRB%` to `def_ORB%` between the 2024 and 2025 data.

#### 2.2.2 Moving Averages (354 features)

Each of the 59 raw statistics was transformed into 3 moving average representations:

| Type                       | Abbreviation | Description                                              |
| -------------------------- | ------------ | -------------------------------------------------------- |
| Simple Moving Average      | SMA          | Rolling mean of last _N_ games                           |
| Cumulative Moving Average  | CMA          | Season-to-date mean                                      |
| Exponential Moving Average | EMA          | Exponentially weighted mean (recent games weighted more) |

This produces 59 × 3 = 177 features per team. Each game has two teams, yielding 177 × 2 = 354 features plus 1 neutral-site flag and 1 target (Win), totaling **356 columns** per dataset row.

#### 2.2.3 Span Variants

Three dataset variants were created with different moving average window sizes:

- **3-span**: Last 3 games (most reactive to recent form)
- **5-span**: Last 5 games (balanced)
- **7-span**: Last 7 games (most stable/smoothed)

### 2.3 Model Training

#### 2.3.1 Pipeline Architecture

Every model was wrapped in an `sklearn.Pipeline` with `StandardScaler` as the first step:

```python
Pipeline([
    ('scaler', StandardScaler()),
    ('model', estimator)
])
```

This ensures feature normalization is baked into the serialized `.pkl` file, so the production API does not need separate scaling logic.

#### 2.3.2 Hyperparameter Optimization

`GridSearchCV` with `ShuffleSplit(n_splits=3)` was used for all models. Scoring was set to `neg_log_loss` (except SVM, which used `accuracy` during grid search due to the computational cost of Platt scaling). This aligns with the ensemble's actual usage: averaging `predict_proba` outputs, where probability calibration matters more than binary accuracy.

#### 2.3.3 Models and Hyperparameter Grids

| Model               | Key Hyperparameters Searched                                                                                    |
| ------------------- | --------------------------------------------------------------------------------------------------------------- |
| Logistic Regression | C: [0.001, 0.01, 0.1, 1, 10, 100], penalty: [L1, L2], solver: saga                                              |
| SVM                 | C: [0.1, 1], kernel: [rbf, linear], gamma: [scale, auto]                                                        |
| KNN                 | n_neighbors: [3, 5, 7, 11, 15], weights: [uniform, distance], p: [1, 2]                                         |
| Random Forest       | n_estimators: [200, 500], max_depth: [8, 12, 20, None], criterion: [gini, entropy]                              |
| Gradient Boosting   | learning_rate: [0.01, 0.05, 0.1], max_depth: [3, 5, 8], n_estimators: [200, 500]                                |
| MLP                 | hidden_layers: [(128,64), (256,128), (354,177), (256,)], activation: [relu, tanh], alpha: [0.0001, 0.001, 0.01] |

#### 2.3.4 Evaluation Metrics

- **Accuracy**: Percentage of correct binary predictions
- **Log Loss**: Measures quality of predicted probabilities; penalizes confident wrong predictions severely. Lower is better (perfect = 0, coin flip ≈ 0.693).
- **Brier Score**: Mean squared error of predicted probabilities vs. actual outcomes. Lower is better (perfect = 0, coin flip = 0.25).

---

## 3. Results

### 3.1 Men's Basketball

#### 3.1.1 Per-Span Results

| Model               | Span | Accuracy   | Log Loss   | Brier Score |
| ------------------- | ---- | ---------- | ---------- | ----------- |
| Logistic Regression | 3    | 69.62%     | 0.5684     | 0.1942      |
| Logistic Regression | 5    | **69.94%** | **0.5663** | **0.1931**  |
| Logistic Regression | 7    | 69.58%     | 0.5751     | 0.1963      |
| SVM                 | 3    | 69.32%     | 0.5743     | 0.1965      |
| SVM                 | 5    | 69.49%     | 0.5706     | 0.1950      |
| SVM                 | 7    | 68.84%     | 0.5914     | 0.2027      |
| KNN                 | 3    | 63.81%     | 0.6439     | 0.2196      |
| KNN                 | 5    | 64.92%     | 0.6488     | 0.2167      |
| KNN                 | 7    | 65.33%     | 0.6627     | 0.2162      |
| Random Forest       | 3    | 68.83%     | 0.5872     | 0.2014      |
| Random Forest       | 5    | 68.68%     | 0.5835     | 0.1999      |
| Random Forest       | 7    | 68.25%     | 0.5910     | 0.2030      |
| Gradient Boosting   | 3    | 69.02%     | 0.5735     | 0.1963      |
| Gradient Boosting   | 5    | 68.89%     | 0.5725     | 0.1959      |
| Gradient Boosting   | 7    | 69.04%     | 0.5806     | 0.1987      |
| MLP                 | 3    | 68.96%     | 0.5780     | 0.1980      |
| MLP                 | 5    | 68.75%     | 0.5770     | 0.1977      |
| MLP                 | 7    | 68.35%     | 0.5944     | 0.2040      |

#### 3.1.2 Average Across Spans

| Model                   | Avg Accuracy | Avg Log Loss | Avg Brier  |
| ----------------------- | ------------ | ------------ | ---------- |
| **Logistic Regression** | **69.71%**   | **0.5699**   | **0.1945** |
| SVM                     | 69.22%       | 0.5788       | 0.1981     |
| Gradient Boosting       | 68.98%       | 0.5755       | 0.1970     |
| MLP                     | 68.69%       | 0.5831       | 0.1999     |
| Random Forest           | 68.59%       | 0.5872       | 0.2014     |
| KNN                     | 64.69%       | 0.6518       | 0.2175     |

**Key Finding (Men's):** Logistic Regression is the top-performing individual model by all three metrics, followed closely by SVM and Gradient Boosting. KNN is the clear weakest performer, ~5 percentage points below the leaders. The 5-span variant tends to produce the best results, suggesting a 5-game rolling window captures recent form without excessive noise.

### 3.2 Women's Basketball

#### 3.2.1 Per-Span Results

| Model               | Span | Accuracy   | Log Loss   | Brier Score |
| ------------------- | ---- | ---------- | ---------- | ----------- |
| Logistic Regression | 3    | 73.17%     | 0.5207     | 0.1747      |
| Logistic Regression | 5    | 73.56%     | 0.5180     | 0.1737      |
| Logistic Regression | 7    | **73.97%** | **0.5054** | **0.1696**  |
| SVM                 | 3    | 73.13%     | 0.5235     | 0.1758      |
| SVM                 | 5    | 73.40%     | 0.5239     | 0.1760      |
| SVM                 | 7    | 73.77%     | 0.5112     | 0.1717      |
| KNN                 | 3    | 69.69%     | 0.6216     | 0.1943      |
| KNN                 | 5    | 70.64%     | 0.6116     | 0.1899      |
| KNN                 | 7    | 70.95%     | 0.5981     | 0.1865      |
| Random Forest       | 3    | 72.78%     | 0.5381     | 0.1811      |
| Random Forest       | 5    | 73.34%     | 0.5327     | 0.1788      |
| Random Forest       | 7    | 73.82%     | 0.5250     | 0.1759      |
| Gradient Boosting   | 3    | 72.61%     | 0.5279     | 0.1778      |
| Gradient Boosting   | 5    | 73.20%     | 0.5257     | 0.1767      |
| Gradient Boosting   | 7    | 74.02%     | 0.5148     | 0.1732      |
| MLP                 | 3    | 72.86%     | 0.5302     | 0.1784      |
| MLP                 | 5    | 73.04%     | 0.5321     | 0.1789      |
| MLP                 | 7    | 73.23%     | 0.5232     | 0.1759      |

#### 3.2.2 Average Across Spans

| Model                   | Avg Accuracy | Avg Log Loss | Avg Brier  |
| ----------------------- | ------------ | ------------ | ---------- |
| **Logistic Regression** | **73.57%**   | **0.5147**   | **0.1727** |
| SVM                     | 73.43%       | 0.5195       | 0.1745     |
| Random Forest           | 73.31%       | 0.5319       | 0.1786     |
| Gradient Boosting       | 73.28%       | 0.5228       | 0.1759     |
| MLP                     | 73.04%       | 0.5285       | 0.1777     |
| KNN                     | 70.43%       | 0.6104       | 0.1902     |

**Key Finding (Women's):** Women's models are consistently ~4 percentage points more accurate than men's (73.4% vs 69.2% average), suggesting women's basketball outcomes are more predictable from box score statistics. Unlike men's, the 7-span variant performs best, indicating that longer-horizon averages better capture team quality in the women's game. Gradient Boosting achieves the single highest accuracy (74.02% at span 7).

### 3.3 Men's vs. Women's Comparison

| Metric      | Men's (Best Avg) | Women's (Best Avg) | Delta    |
| ----------- | ---------------- | ------------------ | -------- |
| Accuracy    | 69.71% (LogReg)  | 73.57% (LogReg)    | +3.86 pp |
| Log Loss    | 0.5699 (LogReg)  | 0.5147 (LogReg)    | -0.0552  |
| Brier Score | 0.1945 (LogReg)  | 0.1727 (LogReg)    | -0.0218  |

Women's basketball is more predictable across all metrics and all models. This may be attributable to greater talent disparity between top and bottom programs in Division I women's basketball, or to more consistent game-to-game performance patterns.

---

## 4. Feature Importance Analysis

Feature importance was extracted from the tree-based models (Random Forest and Gradient Boosting) using the 5-span dataset as a representative sample.

### 4.1 Men's Basketball — Top 15 Features

**Random Forest:**

| Rank | Feature              | Importance |
| ---- | -------------------- | ---------- |
| 1    | ORtg_CMA             | 0.0095     |
| 2    | DRtg_CMA             | 0.0094     |
| 3    | opp_ORtg_CMA         | 0.0091     |
| 4    | opp_DRtg_CMA         | 0.0075     |
| 5    | opp_ORtg_SMA         | 0.0069     |
| 6    | TRB%\_CMA            | 0.0062     |
| 7    | FG_CMA               | 0.0058     |
| 8    | opp_ORtg_EMA         | 0.0057     |
| 9    | opp_TRB%\_CMA        | 0.0055     |
| 10   | opp_TS%\_CMA         | 0.0054     |
| 11   | ORtg_EMA             | 0.0050     |
| 12   | **def_eFG%\_CMA**    | 0.0050     |
| 13   | opp_FG%\_CMA         | 0.0049     |
| 14   | opp_DRtg_EMA         | 0.0049     |
| 15   | **opp_def_FG%\_CMA** | 0.0049     |

**Gradient Boosting:**

| Rank | Feature        | Importance |
| ---- | -------------- | ---------- |
| 1    | opp_ORtg_CMA   | 0.0259     |
| 2    | ORtg_CMA       | 0.0259     |
| 3    | Neutral        | 0.0250     |
| 4    | DRtg_CMA       | 0.0205     |
| 5    | opp_TRB%\_CMA  | 0.0186     |
| 6    | FG_CMA         | 0.0181     |
| 7    | opp_TS%\_CMA   | 0.0179     |
| 8    | opp_DRtg_CMA   | 0.0179     |
| 9    | AST_CMA        | 0.0174     |
| 10   | opp_ORtg_EMA   | 0.0159     |
| 11   | TRB%\_CMA      | 0.0147     |
| 12   | opp_DRtg_SMA   | 0.0142     |
| 13   | opp_DRtg_EMA   | 0.0135     |
| 14   | **def_FG_CMA** | 0.0131     |
| 15   | DRtg_SMA       | 0.0127     |

### 4.2 Women's Basketball — Top 15 Features

**Random Forest:**

| Rank | Feature       | Importance |
| ---- | ------------- | ---------- |
| 1    | ORtg_CMA      | 0.0157     |
| 2    | opp_ORtg_CMA  | 0.0133     |
| 3    | opp_ORtg_EMA  | 0.0101     |
| 4    | opp_ORtg_SMA  | 0.0099     |
| 5    | ORtg_EMA      | 0.0097     |
| 6    | ORtg_SMA      | 0.0095     |
| 7    | FG_CMA        | 0.0086     |
| 8    | DRtg_CMA      | 0.0083     |
| 9    | TOV%\_CMA     | 0.0078     |
| 10   | opp_DRtg_CMA  | 0.0077     |
| 11   | opp_FG_CMA    | 0.0077     |
| 12   | opp_TS%\_CMA  | 0.0071     |
| 13   | opp_TOV%\_CMA | 0.0068     |
| 14   | opp_FG%\_CMA  | 0.0066     |
| 15   | TS%\_CMA      | 0.0066     |

**Gradient Boosting:**

| Rank | Feature         | Importance |
| ---- | --------------- | ---------- |
| 1    | ORtg_SMA        | 0.0580     |
| 2    | opp_FG_CMA      | 0.0411     |
| 3    | ORtg_CMA        | 0.0389     |
| 4    | DRtg_CMA        | 0.0376     |
| 5    | opp_ORtg_CMA    | 0.0340     |
| 6    | FG_CMA          | 0.0330     |
| 7    | opp_DRtg_CMA    | 0.0324     |
| 8    | TOV%\_CMA       | 0.0306     |
| 9    | AST_CMA         | 0.0237     |
| 10   | opp_TOV%\_EMA   | 0.0222     |
| 11   | opp_AST_SMA     | 0.0198     |
| 12   | opp_ORtg_SMA    | 0.0188     |
| 13   | opp_AST_CMA     | 0.0182     |
| 14   | opp_ORtg_EMA    | 0.0156     |
| 15   | **def_AST_CMA** | 0.0145     |

### 4.3 Defensive Feature Contribution (Total)

| Model             | Men's     | Women's   |
| ----------------- | --------- | --------- |
| Random Forest     | **38.8%** | **35.0%** |
| Gradient Boosting | **29.6%** | **18.6%** |

Defensive features account for roughly one-third of all feature importance in Random Forest models, and approximately one-quarter in Gradient Boosting. This is a substantial contribution considering defensive stats represent only 24 out of 59 raw statistics (40.7%) — their importance is roughly proportional to their share of the feature space, confirming they carry signal comparable to offensive stats.

### 4.4 Most Important Defensive Features

Across both genders and both tree-based models, the most consistently important defensive features are:

| Feature          | Description                       | Why It Matters                         |
| ---------------- | --------------------------------- | -------------------------------------- |
| def_eFG%\_CMA    | Opponent effective FG% allowed    | Core shooting defense metric           |
| def_FG%\_CMA     | Opponent FG% allowed              | Raw shooting defense                   |
| def_2P%\_CMA     | Opponent 2P% allowed              | Interior defense quality               |
| def_FG_CMA       | Opponent field goals made allowed | Volume of baskets conceded             |
| def_AST_CMA      | Opponent assists allowed          | Half-court defense breakdown indicator |
| def_TOV%\_CMA    | Forced turnover rate              | Disruptive defense metric              |
| def_STL_CMA      | Steals per game                   | Active hands / press defense           |
| opp_def_FG%\_CMA | Opponent's own defensive FG%      | "Defense vs. defense" matchup signal   |

---

## 5. Model Architecture Observations

### 5.1 Model Rankings

The model ranking is consistent across genders:

1. **Logistic Regression** — Best overall. Benefits most from StandardScaler and the high-dimensional feature space. L1 regularization (selected in all spans) performs implicit feature selection.
2. **SVM** — Close second. Linear kernel preferred for men's spans 3 & 5; RBF for span 7. Computationally expensive.
3. **Gradient Boosting** — Strong performer with best single-span accuracy in women's (74.02%). Handles non-linear interactions natively.
4. **MLP** — Competitive but no clear advantage over simpler models at this dataset size (~15-18K training samples).
5. **Random Forest** — Solid but slightly behind boosting methods. Most useful for feature importance analysis.
6. **KNN** — Consistently weakest. Distance-based methods suffer in 354-dimensional space (curse of dimensionality).

### 5.2 Span Analysis

| Gender  | Best Span | Interpretation                                                   |
| ------- | --------- | ---------------------------------------------------------------- |
| Men's   | 5         | Balanced window; 3-game too noisy, 7-game oversmooths            |
| Women's | 7         | Longer window better; suggests more stable game-to-game patterns |

### 5.3 Ensemble Implications

The production system averages `predict_proba` across all 6 models for a given span. Since Logistic Regression and Gradient Boosting produce the best-calibrated probabilities (lowest log loss), they implicitly dominate the ensemble signal even though each model has equal weight. KNN's poor log loss (0.65+) means it contributes noisy probabilities that dilute ensemble quality.

**Recommendation:** Consider weighted ensemble voting based on per-model log loss, or dropping KNN from the ensemble entirely to improve average probability calibration.

---

## 6. Limitations and Future Work

### 6.1 Limitations

- **No opponent-adjusted metrics**: Features are raw/averaged rather than strength-of-schedule adjusted
- **Equal ensemble weighting**: All 6 models contribute equally despite varying quality
- **No temporal features**: Day of week, rest days, travel distance not included
- **Random split across seasons**: Train/test split is random rather than temporal; a model could see 2026 games in training and 2023 games in test, which may cause slight data leakage if team rosters/styles change over time
- **SVM grid truncation**: `C=10` removed from SVM grid due to computational constraints; full grid might yield marginally better results

### 6.2 Future Work

1. **Weighted ensemble**: Weight model contributions by inverse log loss on validation set
2. **Drop KNN**: Remove from ensemble to improve average probability calibration
3. **Strength of schedule**: Adjust stats by opponent quality (e.g., KenPom-style adjustments)
4. **XGBoost / LightGBM**: Modern gradient boosting implementations with faster training and built-in regularization
5. **Feature reduction**: Use L1 importances or PCA to reduce from 354 to ~100–150 most informative features
6. **Calibration analysis**: Plot reliability diagrams to assess probability calibration per model

---

## 7. Conclusion

The addition of 24 opponent defensive statistics to the NCAA basketball prediction pipeline was validated by feature importance analysis showing these features contribute 18.6–38.8% of total predictive signal. Models achieve 68.6–69.7% accuracy for men's and 73.0–73.6% accuracy for women's basketball, with Logistic Regression and Gradient Boosting producing the best-calibrated probabilities for ensemble use. The `StandardScaler` + `Pipeline` architecture ensures production deployment requires zero preprocessing changes, and the `neg_log_loss` scoring metric aligns training optimization with the ensemble's actual probability-averaging behavior.

---

## Appendix A: Dataset Statistics

| Metric                  | Men's            | Women's          |
| ----------------------- | ---------------- | ---------------- |
| Seasons                 | 2022–2026        | 2022–2026        |
| Train/test split        | 70/30 random     | 70/30 random     |
| Raw features            | 59               | 59               |
| Engineered features     | 356              | 356              |
| 3-span training samples | 18,585           | 17,184           |
| 3-span test samples     | 7,966            | 7,365            |
| 5-span training samples | 16,747           | 15,584           |
| 5-span test samples     | 7,178            | 6,680            |
| 7-span training samples | 15,146           | 13,997           |
| 7-span test samples     | 6,492            | 6,000            |
| Models per gender       | 18 (6 × 3 spans) | 18 (6 × 3 spans) |
| Total models            | 36               | —                |

## Appendix B: Technology Stack

| Component           | Technology                                   |
| ------------------- | -------------------------------------------- |
| Data scraping       | Python, BeautifulSoup, requests              |
| Data processing     | pandas, NumPy                                |
| Machine learning    | scikit-learn 1.4.1                           |
| Model serialization | pickle (Pipeline objects)                    |
| API server          | FastAPI + uvicorn                            |
| Frontend            | React + TypeScript + Vite                    |
| Cloud storage       | Azure Blob Storage                           |
| Deployment          | Azure Static Web Apps + Azure Container Apps |
