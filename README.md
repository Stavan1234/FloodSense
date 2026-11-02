# FloodSense

**Can AI recognise a flood day?** Pick a day and FloodSense reads a week of weather and satellite data, gives a clear flood-risk level, and shows why. Deep learning (LSTM) → machine learning (Random Forest) → transparent rules.

Computational Intelligence Laboratory, **Practical 10**: validation, interpretation, ethics and deployment (LO 4.2).

> ⚠️ Educational prototype. Same-day classification on an educational dataset from a single location. **Not** for real emergency decisions.

## Full notebook (Practicals 4–10)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Stavan1234/FloodSense/blob/main/CIL_Practicals_4_to_10_FloodSense.ipynb)

`CIL_Practicals_4_to_10_FloodSense.ipynb` covers every task in one place: EDA and cleaning, feature engineering, ML models with SHAP, LSTM design and tuning, interpretability (permutation, ablation, activations, SHAP), DL→ML→AI integration, and validation/ethics/deployment. In Colab, just choose **Runtime → Run all**; the dataset is downloaded automatically and a full run takes about 3–5 minutes on CPU.

## Quick start

**Windows:**
1. Double-click **`setup.bat`** once. It creates a virtual environment and installs the packages.
2. Double-click **`run.bat`** to start the website in your browser. (If you skip step 1, `run.bat` runs setup for you.)

Run `setup.bat` again any time to reinstall or update packages.

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
5. Click **Deploy**. The first build takes a few minutes (it installs PyTorch).

Every push to `main` redeploys automatically. Apps with no visitors for a while go to sleep; the next visitor clicks "wake up" and waits about 30 seconds.

`requirements.txt` pins the exact tested versions (scikit-learn 1.8.0 matches the saved model) and installs CPU-only PyTorch to keep the install small.

## What the website offers

| Page | What you can do |
|---|---|
| Home | Interactive 3D globe (NASA imagery, day/night) pinned at the monitored point, the living advisory for the latest day, numbers that count up |
| Check a day | Pick a day (or upload 7 days) → a living advisory card whose rain, clouds and water level follow the model, animated reasons, a 7-day weather strip, SHAP charts and the rule that fired |
| What-if lab | One-click scenarios and plain-language sliders; the living advisory card turns stormy or calm as you change the weather |
| How it works | Press Play to follow one real day through the engine: readings → LSTM → 32-number summary → 250 tree votes → rules |
| Can I trust it? | Calendar of all 204 unseen days (click to open one), performance over time, what it looks at, safety checks, limits |

## How it works

```
7 days × 13 readings → validate → impute + scale → LSTM (32-number summary of the week)
        ├─ LSTM probability ───────────────┐
        └─ Random Forest (250 trees) ──────┴─ 50/50 combine → 4 IF–THEN rules → LOW RISK / MONITOR / FLOOD WATCH / FLOOD WARNING
```

The website loads exactly the model trained in the notebook (`model_artifacts/`, `site_data/` are written by its export cell), so both show the same numbers.

## Results on 204 unseen test days (Mar–Sep 2025)

| Accuracy | Floods caught | Precision | F1 | Missed floods | False alarms |
|---|---|---|---|---|---|
| 89.7% | 70 of 78 (89.7%) | 84.3% | 0.870 | 8 | 13 |

## Project structure

```
streamlit_app.py           Website entry point and top navigation
app_pages/                 home · check_day · what_if · how_it_works · trust
flood_ui.py                Shared loaders, SHAP explanations, ECharts specs
fs_components.py           Animated components (living advisory, week strip, engine walkthrough, globe)
system_core.py             The notebook's pipeline: validation, LSTM, Random Forest, rules, SHAP
model_artifacts/           Trained LSTM + Random Forest + preprocessing (exported by the notebook)
site_data/                 Clean dataset and evaluation results (exported by the notebook)
CIL_Practicals_4_to_10_FloodSense.ipynb   Full notebook, Tasks 4–10
.streamlit/config.toml     Light and dark theme
setup.bat / run.bat        One-click setup and launcher for Windows
```

## Known limitations

- Single location (19°N, 73°E); flood labels are about 35% in every month with no monsoon pattern, suggesting simulated labels.
- The most relied-on input, change in water area, may be a target proxy (it can *be* the flood).
- Classifies the last day of the window; it is not a forecast.
