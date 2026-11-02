COMPUTATIONAL INTELLIGENCE LABORATORY - PRACTICALS 4 TO 10
FloodSense: next-day flood early warning for one monitored point (26.25N, 68E)

PACKAGE CONTENTS
- CIL_Practicals_4_to_10_FloodSense.ipynb : full notebook (Tasks 4-10); its export cell writes
  model_artifacts/ and site_data/, which the website loads
- input_data/flood_dataset.csv : the daily flood dataset (2022-2024)
- streamlit_app.py : website entry point (FloodSense, top navigation)
- app_pages/ : Home, Check a day, What-if lab, How it works, Can I trust it?
- flood_ui.py, fs_components.py : shared loading, explanations, charts and animated components
- system_core.py : the notebook's pipeline (validation, LSTM, Gradient Boosting, blend, rules)
- model_artifacts/ : trained LSTM, Gradient Boosting and preprocessing exported by the notebook
- site_data/ : merged dataset and evaluation results exported by the notebook
- sample_7_day_input.csv : the last 7 days of the dataset, a template for uploads
- requirements.txt, setup.bat, run.bat : install and run

RUN THE NOTEBOOK
1. Open CIL_Practicals_4_to_10_FloodSense.ipynb in Google Colab (or Jupyter).
2. Runtime -> Run all. The dataset is downloaded automatically.

RUN THE WEBSITE LOCALLY
1. Install Python 3.10+.
2. Windows: double-click setup.bat, then run.bat.
   Any OS: pip install -r requirements.txt, then streamlit run streamlit_app.py
3. Pick a day in "Check a day", or upload a CSV with exactly 7 consecutive daily rows.

RESULTS (164 unseen forecasts, 20 Jul - 30 Dec 2024)
- Accuracy 96.3 % (copying today: 81.7 %), precision 100 %, floods caught 33 of 39, F1 0.917, no false alarms.

IMPORTANT LIMITATIONS
- Forecasts one day ahead for one location.
- "Flood" means satellite water area of at least 766 km2, not ground reports.
- Do not use this prototype for real emergency or disaster-management decisions.
