"""Reusable inference code for Practical 10 deployment demonstration."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import torch
from torch import nn
import joblib

ENVIRONMENTAL_FEATURES = [
    "precipitation", "soil_moisture", "temperature", "humidity", "pressure",
    "wind_speed", "evaporation", "water_area_km2", "water_area_change",
    "precip_3day_avg", "precip_7day_avg", "temp_3day_avg", "soil_3day_avg"
]

class LSTMFeatureEncoder(nn.Module):
    """Same LSTM architecture used in Practical 9; returns logits and embedding."""
    def __init__(self, n_features: int, hidden_size: int = 32, dropout: float = 0.20):
        super().__init__()
        self.lstm = nn.LSTM(input_size=n_features, hidden_size=hidden_size, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden_size, 1)

    def forward(self, x):
        _, (hidden_state, _) = self.lstm(x)
        embedding = hidden_state[-1]
        logits = self.classifier(self.dropout(embedding)).squeeze(-1)
        return logits, embedding

class IntegratedFloodSystem:
    """Load Practical 9 artifacts and run the same-day integrated classification pipeline."""
    def __init__(self, artifact_dir: str | Path):
        self.artifact_dir = Path(artifact_dir)
        bundle = joblib.load(self.artifact_dir / "task9_ml_and_preprocessing.joblib")
        self.rf = bundle["rf_predictor"]
        self.imputer = bundle["imputer"]
        self.scaler = bundle["scaler"]
        self.feature_names = list(bundle["feature_names"])
        self.window_days = int(bundle["window_days"])
        self.system_threshold = float(bundle["system_threshold"])
        self.rule_thresholds = dict(bundle["rule_thresholds"])

        metadata = json.loads((self.artifact_dir / "task9_system_metadata.json").read_text(encoding="utf-8"))
        thresholds = metadata["validation_selected_thresholds"]
        self.ml_threshold = float(thresholds["random_forest"])
        self.dl_threshold = float(thresholds["lstm"])
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.encoder = LSTMFeatureEncoder(n_features=len(self.feature_names), hidden_size=32, dropout=0.20)
        state_path = self.artifact_dir / "task9_lstm_encoder_state_dict.pt"
        try:
            state = torch.load(state_path, map_location="cpu", weights_only=True)
        except TypeError:  # Compatibility with older PyTorch versions.
            state = torch.load(state_path, map_location="cpu")
        self.encoder.load_state_dict(state)
        self.encoder.to(self.device).eval()

    def validate_window(self, raw_window: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(raw_window, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame.")
        required = {"date", *ENVIRONMENTAL_FEATURES}
        missing = sorted(required - set(raw_window.columns))
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(missing))
        if len(raw_window) != self.window_days:
            raise ValueError(f"Provide exactly {self.window_days} daily rows; received {len(raw_window)}.")
        window = raw_window.copy().reset_index(drop=True)
        window["date"] = pd.to_datetime(window["date"], errors="coerce")
        if window["date"].isna().any():
            raise ValueError("One or more dates are invalid. Use YYYY-MM-DD format.")
        if window["date"].duplicated().any():
            raise ValueError("Duplicate dates found. Keep one valid observation per day or aggregate legitimate daily readings first.")
        window = window.sort_values("date").reset_index(drop=True)
        diffs = window["date"].diff().dropna().dt.days
        if not (diffs == 1).all():
            raise ValueError("Dates must be consecutive daily observations with no gaps.")
        numeric = window[ENVIRONMENTAL_FEATURES].apply(pd.to_numeric, errors="coerce")
        if numeric.isna().all(axis=0).any():
            bad = numeric.columns[numeric.isna().all(axis=0)].tolist()
            raise ValueError("These input columns contain no usable numeric values: " + ", ".join(bad))
        window[ENVIRONMENTAL_FEATURES] = numeric
        return window

    def predict_window(self, raw_window: pd.DataFrame) -> dict:
        window = self.validate_window(raw_window)
        feature_frame = window[ENVIRONMENTAL_FEATURES].copy()
        doy = window["date"].dt.dayofyear.to_numpy()
        feature_frame["day_of_year_sin"] = np.sin(2 * np.pi * doy / 365.25)
        feature_frame["day_of_year_cos"] = np.cos(2 * np.pi * doy / 365.25)
        feature_frame = feature_frame[self.feature_names]
        scaled = self.scaler.transform(self.imputer.transform(feature_frame)).astype(np.float32)
        seq = torch.from_numpy(scaled.reshape(1, self.window_days, len(self.feature_names))).to(self.device)
        with torch.no_grad():
            logits, embedding = self.encoder(seq)
            p_dl = float(torch.sigmoid(logits).cpu().numpy()[0])
            embedding_np = embedding.cpu().numpy()
        p_ml = float(self.rf.predict_proba(embedding_np)[0, 1])
        p_integrated = 0.5 * (p_ml + p_dl)
        prediction = "Flood" if p_integrated >= self.system_threshold else "No Flood"

        last = window.iloc[-1]
        heavy_rain = float(last["precipitation"]) >= self.rule_thresholds["heavy_rain"] if pd.notna(last["precipitation"]) else False
        wet_soil = float(last["soil_moisture"]) >= self.rule_thresholds["wet_soil"] if pd.notna(last["soil_moisture"]) else False
        rapid_rise = float(last["water_area_change"]) >= self.rule_thresholds["rapid_water_rise"] if pd.notna(last["water_area_change"]) else False
        cues = []
        if heavy_rain: cues.append("heavy rainfall")
        if wet_soil: cues.append("high soil moisture")
        if rapid_rise: cues.append("rapid water-area increase")

        if (p_ml >= self.ml_threshold and p_dl >= self.dl_threshold) or p_integrated >= 0.75:
            advisory = "FLOOD WARNING"
            reason = "Model agreement/high integrated probability" + ("; " + ", ".join(cues) if cues else "")
        elif p_integrated >= max(0.35, self.system_threshold) or (rapid_rise and (heavy_rain or wet_soil)):
            advisory = "FLOOD WATCH"
            reason = "Elevated model score or combined environmental trigger" + ("; " + ", ".join(cues) if cues else "")
        elif cues:
            advisory = "MONITOR"
            reason = "Environmental rule triggered: " + ", ".join(cues)
        else:
            advisory = "LOW RISK"
            reason = "No model or environmental rule crossed its configured trigger"

        return {
            "target_date": str(last["date"].date()),
            "LSTM_probability": p_dl,
            "Random_Forest_probability": p_ml,
            "integrated_probability": p_integrated,
            "integrated_prediction": prediction,
            "AI_advisory": advisory,
            "reason": reason,
            "heavy_rain_rule": bool(heavy_rain),
            "wet_soil_rule": bool(wet_soil),
            "rapid_water_rise_rule": bool(rapid_rise),
            "task_note": "Same-day classification using a seven-day window; not a next-day forecast. Educational use only."
        }
