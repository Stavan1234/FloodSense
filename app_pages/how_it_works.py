import pandas as pd
import streamlit as st

from flood_ui import load_dataset, load_metadata, load_system, load_test_predictions, pct

system = load_system()
meta = load_metadata()
df = load_dataset()
preds = load_test_predictions()

st.title("How it's built", icon=":material/account_tree:")
st.markdown(
    "This page documents the **architecture**, the **methodology** and the **deployment** of the system, "
    "as required by Practical 10 (LO 4.2)."
)

st.subheader("System architecture", icon=":material/schema:")
st.mermaid_chart(
    f"""
    flowchart LR
        U(["User<br/>picks a day or uploads CSV"]) --> V
        subgraph S0[" 1 · Input safety "]
            V["Validation<br/>7 consecutive days<br/>13 numeric readings"]
        end
        V --> P
        subgraph S1[" 2 · Preprocessing (saved) "]
            P["+ season features<br/>Imputer → Scaler<br/>7 × 15 matrix"]
        end
        P --> L
        subgraph S2[" 3 · Deep learning "]
            L["LSTM encoder<br/>32-number summary<br/>of the week"]
        end
        L -->|"summary"| R
        L -->|"LSTM probability"| C
        subgraph S3[" 4 · Machine learning "]
            R["Random Forest<br/>250 trees"]
        end
        R -->|"RF probability"| C
        subgraph S4[" 5 · AI reasoning "]
            C["Combine 50 / 50"] --> E["Rule engine<br/>IF–THEN, forward chaining"]
        end
        E --> O(["Advisory + explanation<br/>Low risk · Monitor · Watch · Warning"])
    """,
    alt="Architecture: validation, preprocessing, LSTM, Random Forest, rule engine, advisory",
)

st.subheader("The parts, in plain words", icon=":material/widgets:")
parts = [
    (":material/shield:", "Input validation", "system_core.validate_window",
     "Checks there are exactly 7 unique, consecutive days and all 13 readings are present and numeric. Bad input is refused with a clear message."),
    (":material/cleaning_services:", "Preprocessing", "imputer + scaler (saved from Practical 9)",
     "Adds two *season* features from the date, fills any single blank with the training average, and puts every reading on the same scale."),
    (":material/neurology:", "Deep learning: LSTM", "1 LSTM layer · 32 hidden units · dropout 0.2",
     "Reads the week day by day, remembering what it saw, and compresses it into 32 numbers. It also gives its own flood probability."),
    (":material/forest:", "Machine learning: Random Forest", "250 trees · max depth 6 · class-balanced",
     "Takes the LSTM's 32-number summary and lets 250 decision trees vote. A second, independent opinion."),
    (":material/rule:", "AI reasoning: rule engine", "4 IF–THEN rules + 3 environmental triggers",
     "Combines the two probabilities (50/50) and checks rainfall, soil moisture and water rise to choose a readable advisory with a reason."),
    (":material/web:", "Deployment: this website", "Streamlit · app.py + app_pages/",
     "Loads the exact saved artifacts once, then serves the whole pipeline through a browser. No retraining happens here."),
]
cols = st.columns(3)
for i, (icon, name, tech, text) in enumerate(parts):
    with cols[i % 3].container(border=True, height="stretch"):
        st.markdown(f"**{icon} {name}**")
        st.caption(tech)
        st.markdown(text)

st.subheader("Methodology: how Practical 10 fits the whole course", icon=":material/timeline:")
journey = pd.DataFrame([
    {"Practicals": "1–3", "Module": "Knowledge & decision systems", "What was built": "Flood knowledge model, IF–THEN rules, state-space search", "Used here as": "The rule engine and advisory logic"},
    {"Practicals": "4–6", "Module": "Data-driven modelling", "What was built": "Cleaning, feature engineering, classical ML", "Used here as": "Imputer, scaler, rolling-average features, Random Forest"},
    {"Practicals": "7–8", "Module": "Deep learning & interpretability", "What was built": "LSTM on 7-day sequences, interpretation", "Used here as": "The LSTM encoder"},
    {"Practicals": "9", "Module": "Integration", "What was built": "DL → ML → AI pipeline, thresholds chosen on validation data", "Used here as": "The saved, integrated system"},
    {"Practicals": "10", "Module": "Validation & deployment", "What was built": "Unseen-data testing, explanation, safety tests, ethics, this website", "Used here as": "Everything on this site"},
])
st.dataframe(journey, hide_index=True, alt="How each practical contributes to the final system")

st.markdown("**Practical 10 steps**")
steps = [
    "**Reuse, don't retrain.** Load the exact Practical 9 model weights, preprocessing and thresholds, so what we test is what we deploy.",
    f"**Validate the source data.** Required columns, no duplicate dates, a continuous daily timeline, binary labels ({len(df):,} days, "
    f"{df['date'].min():%b %Y} – {df['date'].max():%b %Y}).",
    f"**Evaluate on unseen data.** {len(preds)} held-out days: accuracy, precision, recall, F1, confusion matrix and every mistake.",
    "**Check stability.** Month-by-month performance and repeated-run reproducibility.",
    "**Explain decisions.** Occlusion analysis per decision and overall, model agreement, and the transparent rule path.",
    "**Test input safety.** Feed broken inputs and confirm each one is refused clearly.",
    "**Review responsibly.** Error costs, fairness, data bias, target-proxy risk and limits.",
    "**Deploy.** Package everything into this Streamlit website.",
]
for i, s in enumerate(steps, 1):
    st.markdown(f"{i}. {s}")

st.subheader("Key settings", icon=":material/settings:")
with st.container(horizontal=True):
    st.metric("Window length", f"{system.window_days} days", border=True)
    st.metric("Model inputs per day", len(system.feature_names), border=True, help="13 readings + 2 season features")
    st.metric("LSTM Flood line", pct(system.dl_threshold), border=True)
    st.metric("Random Forest Flood line", pct(system.ml_threshold), border=True)
    st.metric("Combined Flood line", pct(system.system_threshold), border=True)

st.subheader("Run it yourself", icon=":material/terminal:")
st.markdown("From the project folder:")
st.code("pip install -r requirements.txt\nstreamlit run app.py", language="bash")
with st.expander("Project files", icon=":material/folder:"):
    st.table(pd.DataFrame([
        {"File": "app.py", "Purpose": "Website entry point and navigation"},
        {"File": "app_pages/", "Purpose": "One file per page of this website"},
        {"File": "flood_ui.py", "Purpose": "Shared loading, occlusion explanations and plain-language helpers"},
        {"File": "system_core.py", "Purpose": "Validation + integrated inference (the exact Practical 9 pipeline)"},
        {"File": "model_artifacts/", "Purpose": "Saved LSTM weights, Random Forest, imputer, scaler, thresholds"},
        {"File": "input_data/flood_dataset.csv", "Purpose": "Educational dataset"},
        {"File": "CIL_Practical_10_Validation_and_Deployment.ipynb", "Purpose": "Validation notebook that produced the evidence files"},
        {"File": "practical10_results/", "Purpose": "Metrics, tests and figures generated by the notebook"},
        {"File": ".streamlit/config.toml", "Purpose": "Website theme (light & dark)"},
    ]), hide_index=True)
    st.caption(f"Model: {meta['deep_learning_component']}; {meta['integration_score']}.")
