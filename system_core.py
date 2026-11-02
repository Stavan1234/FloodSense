"""FloodSense inference engine.

Loads the model trained in ``CIL_Practicals_4_to_10_FloodSense.ipynb`` (files in
``model_artifacts/``) and reproduces the notebook's pipeline exactly:
validate → season features → impute → scale → LSTM → Random Forest on the LSTM
summary → 50/50 combination → forward-chaining rules. No Streamlit code here.
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from torch import nn

ENVIRONMENTAL_FEATURES = [
    "precipitation", "soil_moisture", "temperature", "humidity", "pressure",
    "wind_speed", "evaporation", "water_area_km2", "water_area_change",
    "precip_3day_avg", "precip_7day_avg", "temp_3day_avg", "soil_3day_avg",
]
ADVISORIES = ["LOW RISK", "MONITOR", "FLOOD WATCH", "FLOOD WARNING"]
TRIGGERS = ["heavy_rain", "wet_soil", "rapid_rise"]


class FloodLSTM(nn.Module):
    """Same architecture as the notebook: one LSTM layer → last hidden state → dropout → output."""

    def __init__(self, n_features, hidden=32, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(n_features, hidden, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(hidden, 1)

    def embed(self, x):
        _, (h, _) = self.lstm(x)
        return h[-1]

    def forward(self, x):
        return self.head(self.dropout(self.embed(x))).squeeze(-1)


class IntegratedFloodSystem:
    def __init__(self, artifact_dir: str | Path):
        artifact_dir = Path(artifact_dir)
        bundle = joblib.load(artifact_dir / "system.joblib")
        ckpt = torch.load(artifact_dir / "lstm.pt", map_location="cpu", weights_only=True)
        self.encoder = FloodLSTM(ckpt["n_features"], ckpt["hidden"], ckpt["dropout"])
        self.encoder.load_state_dict(ckpt["state_dict"])
        self.encoder.eval()
        self.hidden_size = int(ckpt["hidden"])

        self.rf = bundle["rf"]
        self.imputer, self.scaler = bundle["imputer"], bundle["scaler"]
        self.env_features = list(bundle["env_features"])
        self.feature_names = list(bundle["features"])
        self.window_days = int(bundle["window"])
        self.thresholds = {k: float(v) for k, v in bundle["thresholds"].items()}   # dl, ml, sys
        self.rule_levels = {k: float(v) for k, v in bundle["rule_levels"].items()}
        self.watch_level = float(bundle["watch_level"])
        self.background = torch.from_numpy(np.asarray(bundle["shap_background"], dtype=np.float32))
        self.shap_base = float(bundle["shap_base"])
        self.rules = [  # (id, advisory, condition in plain words, test on facts): checked top to bottom
            ("R1", "FLOOD WARNING", "Both models say Flood, or combined score ≥ 75 %",
             lambda f: (f["dl_flood"] and f["ml_flood"]) or f["score"] >= 0.75),
            ("R2", "FLOOD WATCH", f"Combined score ≥ {self.watch_level:.0%}, or rapid water rise with heavy rain / wet soil",
             lambda f: f["score"] >= self.watch_level or (f["rapid_rise"] and (f["heavy_rain"] or f["wet_soil"]))),
            ("R3", "MONITOR", "Any environmental trigger is active",
             lambda f: f["heavy_rain"] or f["wet_soil"] or f["rapid_rise"]),
            ("R4", "LOW RISK", "No rule above fired", lambda f: True),
        ]

    # ------------------------------------------------------------------ input
    def validate_window(self, window) -> pd.DataFrame:
        if not isinstance(window, pd.DataFrame):
            raise TypeError("Input must be a table (pandas DataFrame).")
        missing = [c for c in ["date"] + self.env_features if c not in window.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
        if len(window) != self.window_days:
            raise ValueError(f"Exactly {self.window_days} daily rows are required, got {len(window)}.")
        w = window.copy()
        w["date"] = pd.to_datetime(w["date"], errors="coerce")
        if w["date"].isna().any():
            raise ValueError("Invalid date found; use YYYY-MM-DD.")
        if w["date"].duplicated().any():
            raise ValueError("Duplicate dates found.")
        w = w.sort_values("date").reset_index(drop=True)
        if not w["date"].diff().dropna().dt.days.eq(1).all():
            raise ValueError("Dates must be consecutive days.")
        w[self.env_features] = w[self.env_features].apply(pd.to_numeric, errors="coerce")
        empty = w[self.env_features].isna().all()
        if empty.any():
            raise ValueError(f"Columns with no numeric values: {w[self.env_features].columns[empty].tolist()}")
        return w

    def scale(self, w: pd.DataFrame) -> np.ndarray:
        """Validated window → model input of shape (days, features)."""
        d = w["date"].dt.dayofyear
        frame = w[self.env_features].copy()
        frame["day_of_year_sin"] = np.sin(2 * np.pi * d / 365.25)
        frame["day_of_year_cos"] = np.cos(2 * np.pi * d / 365.25)
        return self.scaler.transform(self.imputer.transform(frame[self.feature_names])).astype(np.float32)

    # ------------------------------------------------------------------ models
    def score(self, batch: np.ndarray):
        """Scaled windows (n, days, features) → (P(LSTM), P(RF), combined)."""
        with torch.no_grad():
            t = torch.from_numpy(np.ascontiguousarray(batch, dtype=np.float32))
            p_dl = torch.sigmoid(self.encoder(t)).numpy()
            emb = self.encoder.embed(t).numpy()
        p_ml = self.rf.predict_proba(emb)[:, 1]
        return p_dl, p_ml, 0.5 * p_dl + 0.5 * p_ml

    # ------------------------------------------------------------------ rules
    def facts(self, last_day: pd.Series, p_dl: float, p_ml: float) -> dict:
        return {"dl_flood": p_dl >= self.thresholds["dl"], "ml_flood": p_ml >= self.thresholds["ml"],
                "score": 0.5 * p_dl + 0.5 * p_ml,
                "heavy_rain": bool(last_day["precipitation"] >= self.rule_levels["heavy_rain"]),
                "wet_soil": bool(last_day["soil_moisture"] >= self.rule_levels["wet_soil"]),
                "rapid_rise": bool(last_day["water_area_change"] >= self.rule_levels["rapid_rise"])}

    def forward_chain(self, facts: dict):
        for rule_id, advisory, text, test in self.rules:
            if test(facts):
                return advisory, rule_id, text

    # ------------------------------------------------------------------ end to end
    def predict_window(self, window) -> dict:
        w = self.validate_window(window)
        p_dl, p_ml, _ = self.score(self.scale(w)[None])
        f = self.facts(w.iloc[-1], float(p_dl[0]), float(p_ml[0]))
        advisory, rule_id, rule_text = self.forward_chain(f)
        return {"date": w["date"].iloc[-1].date(), "p_dl": float(p_dl[0]), "p_ml": float(p_ml[0]),
                "score": f["score"], "prediction": "Flood" if f["score"] >= self.thresholds["sys"] else "No Flood",
                "advisory": advisory, "rule": rule_id, "rule_text": rule_text,
                "triggers": [t for t in TRIGGERS if f[t]], "facts": f}

    # ------------------------------------------------------------------ explanation
    def explain(self, window, n_samples: int = 400, seed: int = 0) -> np.ndarray:
        """Expected-gradients SHAP values (days × features) for the LSTM flood probability.

        The same method as ``shap.GradientExplainer`` in the notebook, with the same
        background windows: values sum (approximately) to P(LSTM) − ``shap_base``.
        """
        x = torch.from_numpy(self.scale(self.validate_window(window)))[None]
        gen = torch.Generator().manual_seed(seed)
        ref = self.background[torch.randint(len(self.background), (n_samples,), generator=gen)]
        alpha = torch.rand(n_samples, 1, 1, generator=gen)
        path = (ref + alpha * (x - ref)).requires_grad_(True)
        prob = torch.sigmoid(self.encoder(path))
        grads, = torch.autograd.grad(prob.sum(), path)
        return ((x - ref) * grads).mean(0).detach().numpy()
