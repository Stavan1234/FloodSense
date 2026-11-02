COMPUTATIONAL INTELLIGENCE LABORATORY — PRACTICAL 10
Validation, Interpretation, Evaluation and Deployment Readiness

PACKAGE CONTENTS
- CIL_Practicals_4_to_10_FloodSense.ipynb : full notebook (Tasks 4-10); its export cell writes
  model_artifacts/ and site_data/, which the website loads
- CIL_Practical_10_Validation_and_Deployment.ipynb : original Practical 10 validation notebook
- streamlit_app.py : website entry point (FloodSense, top navigation)
- app_pages/ : Home, Check a day, What-if lab, How it works, Can I trust it?
- flood_ui.py : shared loading, SHAP explanations and Plotly components
- .streamlit/config.toml : website theme (light and dark)
- system_core.py : the notebook's pipeline (validation, LSTM, Random Forest, rules, SHAP)
- model_artifacts/ : trained LSTM, Random Forest and preprocessing exported by the notebook
- site_data/ : clean dataset and evaluation results exported by the notebook
- input_data/flood_dataset.csv : educational dataset used for the lab demonstration
- validation_data_task9_predictions.csv : saved held-out predictions from Practical 9
- Practical_10_Explanation_and_Viva.md : separate beginner-friendly guide and viva questions
- practical10_results/ : generated validation tables and figures after notebook execution
- requirements.txt : Python packages

RUN THE NOTEBOOK
1. Extract this ZIP.
2. Open CIL_Practical_10_Validation_and_Deployment.ipynb in Jupyter or Google Colab.
3. Run all cells in order. If files are not beside the notebook, the first setup cell asks you to upload the package ZIP.

RUN THE DEPLOYMENT DEMO LOCALLY
1. Install Python 3.10+ (a compatible environment with PyTorch is recommended).
2. Open a terminal in this extracted folder.
3. Run: pip install -r requirements.txt
4. Run: streamlit run streamlit_app.py
5. Use the included demo data or upload a CSV with exactly seven consecutive daily rows and the required environmental columns.

IMPORTANT LIMITATIONS
- This app performs same-day flood classification from a seven-day window ending on the labelled day. It is NOT a next-day forecast.
- The dataset and thresholds are educational and have not been validated for operational flood warnings.
- Do not use this prototype for real emergency or disaster-management decisions.
