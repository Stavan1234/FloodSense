"""FloodSense inference engine: next-day flood early warning.

Loads the model trained in ``CIL_Practicals_4_to_10_FloodSense.ipynb`` (files in
``model_artifacts/``) and reproduces the notebook's pipeline exactly:
validate 7 days → per-day features (season, flood counters) → LSTM + gradient boosting →
blend (weight chosen by cross-validation) → forward-chaining rules → advisory for TOMORROW.
No Streamlit code here.
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from torch import nn

ENVIRONMENTAL_FEATURES = [
    "precipitation", "soil_moisture", "temperature", "humidity", "pressure", "wind_speed", "evaporation",
    "water_area_km2", "water_area_change", "precip_3day_avg", "precip_7day_avg", "temp_3day_avg", "soil_3day_avg",
]
ADVISORIES = ["LOW RISK", "MONITOR", "FLOOD WATCH", "FLOOD WARNING"]
TRIGGERS = ["flooded_today", "near_line", "heavy_rain", "wet_soil", "rapid_rise"]


class FloodLSTM(nn.Module):
    """Same architecture as the notebook: one LSTM layer → last hidden state → dropout → output."""

    def __init__(self, n_inputs, hidden=16, dropout=0.1):
        super().__init__()
        self.lstm = nn.LSTM(n_inputs, hidden, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(hidden, 1)

    def embed(self, x):
        _, (h, _) = self.lstm(x)
        return h[-1]

    def forward(self, x):
        return self.head(self.dropout(self.embed(x))).squeeze(-1)


class IntegratedFloodSystem:
    def __init__(self, artifact_dir: str | Path, typical: dict | None = None):
        artifact_dir = Path(artifact_dir)
        b = joblib.load(artifact_dir / "system.joblib")
        ckpt = torch.load(artifact_dir / "lstm.pt", map_location="cpu", weights_only=True)
        self.encoder = FloodLSTM(ckpt["n_inputs"], ckpt["hidden"], ckpt["dropout"])
        self.encoder.load_state_dict(ckpt["state_dict"])
        self.encoder.eval()
        self.hidden_size = int(ckpt["hidden"])

        self.ml_model, self.ml_name, self.selected = b["ml_model"], b["ml_name"], list(b["selected"])
        self.seq_imputer, self.seq_scaler = b["seq_imputer"], b["seq_scaler"]
        self.env_features, self.lstm_inputs, self.ml_daily = list(b["env"]), list(b["lstm_inputs"]), list(b["ml_daily"])
        self.window_days = int(b["window"])
        self.flood_line = float(b["flood_line"])
        self.w_dl = float(b["w_dl"])
        self.thresholds = {k: float(v) for k, v in b["thresholds"].items()}       # dl, ml, sys
        self.rule_levels = {k: float(v) for k, v in b["rule_levels"].items()}
        self.watch_level = float(b["watch_level"])
        self.typical = typical or {}                                              # training medians, for explanations
        self.rules = [  # (id, advisory, condition in plain words, test on facts): checked top to bottom
            ("R1", "FLOOD WARNING", "The system predicts a flood tomorrow (score above the flood line)",
             lambda f: f["score"] >= self.thresholds["sys"]),
            ("R2", "FLOOD WATCH", f"A real chance of flooding tomorrow (score ≥ {self.watch_level:.0%})",
             lambda f: f["score"] >= self.watch_level),
            ("R3", "MONITOR", "Flooded today, water near the line, or any other warning sign",
             lambda f: f["flooded_today"] or f["near_line"] or f["heavy_rain"] or f["wet_soil"] or f["rapid_rise"]),
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
        w[self.env_features] = w[self.env_features].fillna(w[self.env_features].median())
        return w

    def frame(self, w: pd.DataFrame) -> pd.DataFrame:
        """Validated 7 days → per-day features (identical to ``window_frame`` in the notebook)."""
        env = w[self.env_features].to_numpy(float)
        doy = pd.to_datetime(w["date"]).dt.day_of_year.to_numpy()
        wet = env[:, self.env_features.index("water_area_km2")] >= self.flood_line
        fs, ds, a, b = [], [], 0, 0
        for x in wet:
            a, b = (a + 1, 0) if x else (0, b + 1)
            fs.append(a); ds.append(b)
        extra = np.column_stack([np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25), fs, ds])
        return pd.DataFrame(np.hstack([env, extra]),
                            columns=[*self.env_features, "day_of_year_sin", "day_of_year_cos", "flood_streak", "dry_streak"])

    def flat(self, frame: pd.DataFrame) -> pd.Series:
        """7 days × daily readings → one row named like ``water_area_km2@d-1`` (reading-major, oldest day first)."""
        n = self.window_days
        names = [f"{c}@d{i - n + 1}" for c in self.ml_daily for i in range(n)]
        return pd.Series(frame[self.ml_daily].to_numpy(float).T.ravel(), index=names)

    # ------------------------------------------------------------------ models
    def score_frames(self, frames: list[pd.DataFrame]):
        """Per-day feature tables → (P(LSTM), P(ML), combined) for tomorrow."""
        k, n = len(frames), self.window_days
        days = pd.DataFrame(np.concatenate([f[self.lstm_inputs].to_numpy(float) for f in frames]), columns=self.lstm_inputs)
        seq = self.seq_scaler.transform(self.seq_imputer.transform(days)).reshape(k, n, -1).astype(np.float32)
        with torch.no_grad():
            p_dl = torch.sigmoid(self.encoder(torch.from_numpy(seq))).numpy()
        X = pd.DataFrame([self.flat(f) for f in frames])[self.selected]
        p_ml = self.ml_model.predict_proba(X)[:, 1]
        return p_dl, p_ml, self.w_dl * p_dl + (1 - self.w_dl) * p_ml

    # ------------------------------------------------------------------ rules
    def facts(self, today: pd.Series, p_dl: float, p_ml: float) -> dict:
        water, L = float(today["water_area_km2"]), self.rule_levels
        return {"dl_flood": p_dl >= self.thresholds["dl"], "ml_flood": p_ml >= self.thresholds["ml"],
                "score": self.w_dl * p_dl + (1 - self.w_dl) * p_ml,
                "flooded_today": water >= self.flood_line, "near_line": L["near_line"] <= water < self.flood_line,
                "heavy_rain": bool(today["precipitation"] >= L["heavy_rain"]), "wet_soil": bool(today["soil_moisture"] >= L["wet_soil"]),
                "rapid_rise": bool(today["water_area_change"] >= L["rapid_rise"])}

    def forward_chain(self, facts: dict):
        for rule_id, advisory, text, test in self.rules:
            if test(facts):
                return advisory, rule_id, text

    def _result(self, w: pd.DataFrame, p_dl: float, p_ml: float) -> dict:
        f = self.facts(w.iloc[-1], p_dl, p_ml)
        advisory, rule_id, rule_text = self.forward_chain(f)
        today = w["date"].iloc[-1]
        return {"date": today.date(), "for_date": (today + pd.Timedelta(days=1)).date(), "p_dl": p_dl, "p_ml": p_ml,
                "score": f["score"], "prediction": "Flood" if f["score"] >= self.thresholds["sys"] else "No Flood",
                "advisory": advisory, "rule": rule_id, "rule_text": rule_text,
                "triggers": [t for t in TRIGGERS if f[t]], "facts": f}

    # ------------------------------------------------------------------ end to end
    def predict_window(self, window) -> dict:
        return self.predict_windows([window])[0]

    def predict_windows(self, windows: list) -> list[dict]:
        """Several 7-day windows in one model call."""
        ws = [self.validate_window(w) for w in windows]
        p_dl, p_ml, _ = self.score_frames([self.frame(w) for w in ws])
        return [self._result(w, float(a), float(b)) for w, a, b in zip(ws, p_dl, p_ml)]

    # ------------------------------------------------------------------ explanation
    def explain(self, window):
        """How much each reading (and each day) moves tomorrow's combined score.

        Occlusion: replace a reading's 7 values (or one whole day) with its typical training value,
        rescore, and take the difference. Positive = it pushed towards a flood tomorrow.
        """
        w = self.validate_window(window)
        typical = lambda c: self.typical.get(c, float(w[c].median()))
        variants, labels = [w], []
        for c in self.env_features:
            v = w.copy(); v[c] = typical(c)
            if c == "water_area_km2":                       # keep the derived change consistent
                v["water_area_change"] = v["water_area_km2"].diff().fillna(0.0)
            variants.append(v); labels.append(("reading", c))
        day_typical = [typical(c) for c in self.env_features]
        for d in range(self.window_days):
            v = w.copy()
            v.loc[d, self.env_features] = day_typical
            variants.append(v); labels.append(("day", d))
        _, _, s = self.score_frames([self.frame(v) for v in variants])
        base = s[0]
        readings = {c: base - x for (kind, c), x in zip(labels, s[1:]) if kind == "reading"}
        days = [base - x for (kind, _), x in zip(labels, s[1:]) if kind == "day"]
        return float(base), readings, days
