# FloodSense

**Will it flood tomorrow?** FloodSense reads the last 7 days of satellite water-area and weather data for one monitored point (26.25°N, 68°E), forecasts tomorrow's flood risk, and shows why. Deep learning (LSTM) + machine learning (Gradient Boosting) → transparent rules.

Computational Intelligence Laboratory, Practicals 4–10: from data cleaning to a validated, explained and deployed intelligent system.

> ⚠️ Educational prototype trained on one location's data. **Not** an official flood warning service.

## The data, and why it forecasts tomorrow

- `input_data/flood_dataset.csv`: daily data, 2022-01-01 → 2024-12-30 (ERA5 weather + satellite water area + flood label).
- Some days have **two satellite passes** (two rows with the same weather but different water readings). They are merged into one row per day (larger water area), giving 1,095 days, 32.5 % of them flood days.
- `days_since_last_flood` gives the answer away (it is 0 on flood days), so it is dropped.
- A day is labelled *flood* exactly when the satellite sees **≥ 766 km² of water**. Classifying *today* would just mean reading that number. So FloodSense answers the useful question: **will the water cross the line tomorrow?**

## Full notebook (Practicals 4–10)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Stavan1234/FloodSense/blob/main/CIL_Practicals_4_to_10_FloodSense.ipynb)

`CIL_Practicals_4_to_10_FloodSense.ipynb` covers every task in one place:

- Task 4: data audit, merge and EDA;
- Task 5: next-day target and feature engineering;
- Task 6: five ML models, SHAP and clustering;
- Task 7: LSTM design and tuning;
- Task 8: interpretability (permutation, ablation, activations, SHAP);
- Task 9: DL + ML + AI-rules integration;
- Task 10: validation, robustness, ethics and deployment.

In Colab, choose **Runtime → Run all**. The dataset is downloaded automatically.

## Quick start

**Windows:**
1. Double-click **`setup.bat`** once. It creates a virtual environment and installs the packages.
2. Double-click **`run.bat`** to start the website in your browser. (If you skip step 1, `run.bat` runs setup for you.)

**Any OS:**

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Requires Python 3.10+.

## Deploy free on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Repository `Stavan1234/FloodSense`, branch `main`, main file path `streamlit_app.py`.
4. Open **Advanced settings** and choose Python **3.12**.
5. Click **Deploy**.

Every push to `main` redeploys automatically. `requirements.txt` pins the tested versions (scikit-learn 1.8.0 matches the saved model).

## What the website offers

| Page | What you can do |
|---|---|
| Home | Particle globe at the monitored point, tomorrow's advisory from the latest data, headline results |
| Check a day | Pick any day as "today" (or upload 7 days) → tomorrow's advisory, was it right, the reasons, the 7-day strip and the rule that fired |
| What-if lab | Change today's water area, its trend, rain and soil; four one-tap scenarios, one per risk level |
| How it works | Follow one real day through the engine; the LSTM, Gradient Boosting and the rules explained; model card |
| Can I trust it? | Calendar of every test forecast, accuracy 1–3 days ahead, performance over time, what it looks at, safety checks, limits |

## How it works

```
last 7 days ─┬─ 8 inputs/day ───────► LSTM (32 units) ─────────────── 20 % ─┐
             └─ 30 best readings ───► Gradient Boosting (250 trees) ── 80 % ─┴─► P(flood tomorrow)
                                                                                    │
            R1 score ≥ 0.62 → FLOOD WARNING · R2 score ≥ 0.15 → FLOOD WATCH        ◄─┘
            R3 any warning sign → MONITOR   · R4 otherwise → LOW RISK
```

The blend weight and the thresholds were chosen by time-series cross-validation on training data, never on test days. The website loads exactly the model the notebook exports (`model_artifacts/`, `site_data/`), and reproduces all its test predictions.

## Results on 164 unseen next-day forecasts (20 Jul – 30 Dec 2024)

| | Accuracy | Precision | Floods caught | F1 |
|---|---|---|---|---|
| Copy today ("tomorrow = today") | 81.7 % | 61.5 % | 61.5 % | 0.615 |
| LSTM alone | 92.1 % | 81.0 % | 87.2 % | 0.840 |
| Gradient Boosting alone | 95.7 % | 97.1 % | 84.6 % | 0.904 |
| **FloodSense (combined)** | **96.3 %** | **100 %** | **84.6 % (33 of 39)** | **0.917** |

No false alarms. Counting Flood watch as an alert too, 37 of 39 floods (94.9 %) were flagged the day before; none of the 6 missed floods was rated Low risk.

## Project structure

```
streamlit_app.py           Website entry point and top navigation
app_pages/                 home · check_day · what_if · how_it_works · trust
flood_ui.py                Shared loaders, explanations, chart specs
fs_components.py           Animated components (living advisory, week strip, engine walkthrough, globe, background)
system_core.py             The notebook's pipeline: validation, LSTM, Gradient Boosting, blend, rules
model_artifacts/           Trained models + preprocessing (exported by the notebook)
site_data/                 Merged dataset and evaluation results (exported by the notebook)
CIL_Practicals_4_to_10_FloodSense.ipynb   Full notebook, Tasks 4–10
setup.bat / run.bat        One-click setup and launcher for Windows
```

## Known limitations

- One location, one day ahead. Two or three days ahead the accuracy drops (89.6 %, 88.3 %).
- "Flood" means satellite water area above a threshold, not ground reports.
- The hardest days are borderline ones, when the water is falling but stays just over the line.
