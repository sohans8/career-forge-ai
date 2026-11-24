# Career Forge AI: Class 10 stream recommender (ML)

## Overview

This folder holds the machine learning pipeline behind the Class 10 stream recommender (`POST /api/v1/recommend`). It extends the domain rule engine with a data-driven model and combines the two in a hybrid.

## Data inspection and sufficiency

- **Catalogue data (`backend/data/raw/career_copilot_expanded_dataset/`):** 105 subjects, 76 skills, 59 interests, 12 streams, 104 courses, 200 careers and 1,250 domain rule pairs.
- **Sufficiency:** the catalogue files do **not** contain real student interaction logs or labelled outcomes. `stream_recommendation_rules.csv` is domain knowledge, not ground truth.
- **Synthetic profiles:** a transparent generator (`ml/data/generate_synthetic_dataset.py`) samples student profiles from 12 domain archetypes with controlled cross-domain noise.

## Dataset schema (`synthetic_student_dataset.csv`)

| Column | Type | Description |
| :--- | :--- | :--- |
| `student_id` | String | Unique profile ID (for example `STU0001`) |
| `student_name` | String | Synthetic student name |
| `subjects` | String | Semicolon-separated favourite subjects |
| `skills` | String | Semicolon-separated skills |
| `interests` | String | Semicolon-separated interests |
| `target_stream_id` | String | Target stream label (`S01` to `S12`) |
| `target_broad_pathway` | String | Broad pathway (Science, Commerce, Humanities, Other) |
| `archetype` | String | Domain archetype used for sampling |

## Feature representation

Each profile is encoded as a **multi-hot binary vector**:

- **Subjects:** 105 binary features
- **Skills:** 76 binary features
- **Interests:** 59 binary features
- **Total:** 105 + 76 + 59 = **240 binary features** per profile

## Models

- **Primary model:** Logistic Regression (`sklearn.linear_model.LogisticRegression`), calibrated. It suits sparse multi-hot vectors, trains and predicts quickly, and outputs probabilities directly.
- **Alternative:** Random Forest (`sklearn.ensemble.RandomForestClassifier`).
- **Hybrid (used in production):** `score = w_rule × rule_score + w_ml × (probability × 100)`, with `w_rule = 0.85, w_ml = 0.15` for sparse inputs and `0.50 / 0.50` for complete profiles.

## Train / test split

- **Dataset:** 600 synthetic profiles across 12 stream archetypes.
- **Stratified split:** 80% training (480 profiles), 20% held-out test (120 profiles, saved to `ml/data/held_out_test_set.csv`).
- **No leakage:** the multi-hot vocabulary is fitted on training data only.

## Evaluation

- **Top-1 accuracy:** exact match with the target stream.
- **Top-3 accuracy:** target appears in the top 3 recommendations (important for counselling, where students compare options).
- **Macro F1:** unweighted average F1 across the 12 streams.

### Held-out test results (N = 120)

| System | Top-1 accuracy | Top-3 accuracy | Macro F1 |
| :--- | :---: | :---: | :---: |
| Rule engine baseline | 91.67% | 100.00% | 91.68% |
| Logistic Regression | 100.00% | 100.00% | 100.00% |
| Hybrid (rule + ML) | 100.00% | 100.00% | 100.00% |

The 100% scores reflect clean synthetic data. The robustness study in `ml/robustness/` shows accuracy falling to about 80% at 30% input noise. Real-world accuracy needs real student data to measure.

## Commands

```bash
# Generate the synthetic dataset
python ml/data/generate_synthetic_dataset.py

# Train the models and save the train/test split
python ml/train.py

# Evaluate every system on the held-out test set
python ml/evaluate.py
```
