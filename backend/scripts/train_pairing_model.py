"""
Stub training script for the pairing logistic regression model.

This script bootstraps a dataset from historical `pairing_events` rows that
contain serialized feature vectors and persists a LogisticRegression model to
`data/models/pairing_prl_v1.pkl`. It is intentionally conservative and meant
to be run offline.
"""
import os
import sys
from pathlib import Path

# Force path so imports always work
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import argparse
import json
import sqlite3
from typing import List

try:
    import joblib  # type: ignore
    from sklearn.linear_model import LogisticRegression  # type: ignore
except ImportError:  # pragma: no cover - training is optional
    joblib = None
    LogisticRegression = None

from backend.app.db import DB_PATH
from backend.services.pairing_service import MODEL_FEATURE_ORDER, MODEL_PATH

POSITIVE_ACTIONS = {"auto_paired", "confirmed_manual"}
NEGATIVE_ACTIONS = {"rejected"}


def load_training_rows(min_samples: int) -> List[tuple]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT action, feature_vector_json
        FROM pairing_events
        WHERE feature_vector_json IS NOT NULL
          AND action IN ({})
        """.format(
            ",".join("?" for _ in POSITIVE_ACTIONS.union(NEGATIVE_ACTIONS))
        ),
        tuple(POSITIVE_ACTIONS.union(NEGATIVE_ACTIONS)),
    )
    rows = cursor.fetchall()
    conn.close()
    if len(rows) < min_samples:
        raise RuntimeError(f"Not enough pairing_events rows to train (found {len(rows)}, need {min_samples})")
    return rows


def vectorize(rows: List[tuple]) -> tuple:
    X = []
    y = []
    for action, vector_json in rows:
        features = json.loads(vector_json)
        X.append([float(features.get(name, 0.0)) for name in MODEL_FEATURE_ORDER])
        y.append(1 if action in POSITIVE_ACTIONS else 0)
    return X, y


def train_model(min_samples: int) -> None:
    if not joblib or not LogisticRegression:
        raise RuntimeError("scikit-learn and joblib are required to train the pairing model")

    rows = load_training_rows(min_samples)
    X, y = vectorize(rows)
    model = LogisticRegression(max_iter=200, class_weight="balanced")
    model.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Saved pairing model to {MODEL_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Train the pairing logistic regression model from pairing_events.")
    parser.add_argument("--min-samples", type=int, default=100, help="Minimum number of labeled events required to train.")
    args = parser.parse_args()

    train_model(args.min_samples)


if __name__ == "__main__":
    main()

