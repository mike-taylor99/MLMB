# Machine Learning

Model training and evaluation for NCAA basketball game outcome prediction.

## Structure

```
notebooks/          Training notebooks
  mens_training     Train 8 classifiers on men's data (GridSearchCV + StandardScaler pipelines)
  womens_training   Train 8 classifiers on women's data
  voting_classifier Build VotingClassifier ensemble from trained models
model/              Exported .pkl files (git-ignored, uploaded to Azure Blob Storage)
  mens/             27 men's models (9 types × 3 spans)
  womens/           27 women's models
RESEARCH_PAPER.md   Detailed methodology, results, and analysis
```

## Models

| Model                           | Key                   |
| ------------------------------- | --------------------- |
| Logistic Regression             | `logistic_regression` |
| Support Vector Machine          | `svm`                 |
| K-Nearest Neighbors             | `knn`                 |
| Random Forest                   | `random_forest`       |
| Gradient Boosting               | `gradient_boosting`   |
| Multilayer Perceptron           | `mlp`                 |
| XGBoost                         | `xgboost`             |
| LightGBM                        | `lightgbm`            |
| **Ensemble** (VotingClassifier) | `ensemble`            |

Each model is trained at 3 moving-average spans (3, 5, 7) for both men's and women's basketball.

The ensemble is a `VotingClassifier` with soft voting and equal weights over 7 models (all except KNN). It is exported as a single `.pkl` file and loaded/called like any individual model.

## Features

59 raw statistics per team (35 offensive + 24 defensive) × 3 moving average types (SMA, CMA, EMA) = 177 features per team. Full input vector: home (177) + away (177) + neutral flag (1) + target (1) = **356 columns**.

Training data: seasons 2022–2026, 70/30 train/test split.

## Blob Storage

Models are uploaded to Azure Blob Storage (`mlmb-models` container) under versioned folders:

```
ncaam_basketball/2026-03-02/3span_logistic_regression_model.pkl
ncaam_basketball/2026-03-02/3span_logistic_regression_model.pkl.gz
...
```

Both raw `.pkl` and gzipped `.pkl.gz` variants are stored. The API loads gzipped versions first for faster cold starts, falling back to raw if unavailable. Model paths are resolved via `models_manifest.json` in the same container.
