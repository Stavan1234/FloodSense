# FloodSense

**Can AI recognise a flood day?** An integrated flood-risk system (LSTM → Random Forest → rule engine) with a beginner-friendly Streamlit website that validates, explains and deploys it.

Computational Intelligence Laboratory, **Practical 10**: validation, interpretation, ethics and deployment (LO 4.2).

> ⚠️ Educational prototype. Same-day classification on an educational dataset from a single location. **Not** for real emergency decisions.

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

## Deploy on Vercel

The repo is ready for Vercel's Python runtime:

- `app.py` exposes `app = st.App("streamlit_app.py")`, Streamlit's ASGI app, which Vercel loads as the function entrypoint. Vercel's Python functions support WebSockets, which Streamlit needs.
- `requirements.txt` pulls **CPU-only PyTorch**, `.python-version` pins Python 3.12, and `vercel.json` sets `maxDuration` and excludes files the site doesn't need.

Steps: import the GitHub repo in Vercel → leave the framework preset on **Other** → Deploy.

If the build says the function is too large, add the environment variable `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` (Project → Settings → Environment Variables) and redeploy. PyTorch is big; Vercel's large-functions beta allows up to 5 GB.

Notes:
- On the Hobby plan a function (and so the live connection) runs for at most 5 minutes; after that the page reconnects automatically and may reset what you entered.
- The first visit after idle time is slow (cold start loads PyTorch and the models).
- [Streamlit Community Cloud](https://share.streamlit.io) is a simpler free alternative: point it at `streamlit_app.py`.

## What the website offers

| Page | What you can do |
|---|---|
| Start here | Plain-English overview, key results, 3-step guide |
| Check a day | Pick a date (or upload a 7-day CSV) → see the readings → get an advisory with its reasons |
| What-if lab | Move rain / soil / water sliders and watch the decision change |
| Test results | Scorecard, confusion matrix, timeline, monthly stability, every mistake |
| Why the AI decides | Occlusion importance, LSTM vs Random Forest agreement, rule flowchart |
| Input safety tests | Live validation tests and a "try to break it" table |
| Responsible AI | Error trade-off, fairness, data bias, ethics, readiness |
| How it's built | Architecture, methodology, settings |
| Glossary & viva | Searchable terms and viva questions |

## How it works

```
7 days × 13 readings → validation → imputer + scaler → LSTM encoder (32-d)
        ├─ LSTM probability ───────────────┐
        └─ Random Forest (250 trees) ──────┴─ 50/50 combine → rule engine → LOW RISK / MONITOR / FLOOD WATCH / FLOOD WARNING
```

## Results on 204 unseen test days (Mar–Sep 2025)

| Accuracy | Recall (floods caught) | Precision | F1 | Missed floods | False alarms |
|---|---|---|---|---|---|
| 89.7% | 83.3% | 89.0% | 0.861 | 13 | 8 |

## Project structure

```
streamlit_app.py           Website entry point and navigation
app.py                     ASGI wrapper loaded by Vercel (st.App)
vercel.json                Vercel function settings
app_pages/                 One file per page
flood_ui.py                Shared loaders, occlusion explanations, UI helpers
system_core.py             Input validation + integrated inference (Practical 9 pipeline)
model_artifacts/           Saved LSTM weights, Random Forest, preprocessing, thresholds
input_data/                Educational flood dataset
practical10_results/       Metrics, tests and figures from the notebook
CIL_Practical_10_Validation_and_Deployment.ipynb   Validation notebook
.streamlit/config.toml     Light and dark theme
setup.bat                  One-time setup for Windows (venv + packages)
run.bat                    One-click launcher for Windows
```

## Known limitations

- Single location (19°N, 73°E); flood labels are about 35% in every month with no monsoon pattern, suggesting simulated labels.
- The most relied-on input, change in water area, may be a target proxy (it can *be* the flood).
- Classifies the last day of the window; it is not a forecast.
