COMPUTATIONAL INTELLIGENCE LABORATORY — PRACTICAL 10
Validation, Interpretation, Evaluation and Deployment Readiness

PACKAGE CONTENTS
- CIL_Practical_10_Validation_and_Deployment.ipynb : executable validation notebook
- streamlit_app.py : website entry point (FloodSense, multi-page Streamlit app)
- app_pages/ : one file per website page (Check a day, What-if lab, Test results, Why the AI decides,
  Input safety tests, Responsible AI)
- flood_ui.py : shared loading, occlusion-based explanations and plain-language helpers
- .streamlit/config.toml : website theme (light and dark)
- system_core.py : reusable inference and input-validation code
- model_artifacts/ : saved Practical 9 LSTM weights, Random Forest, preprocessing, and metadata
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
