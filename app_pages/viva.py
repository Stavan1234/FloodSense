import streamlit as st

st.title("Glossary & viva questions", icon=":material/school:")
st.markdown("Every technical word used on this site, in plain English, followed by likely viva questions with short answers.")

query = st.text_input("Search", placeholder="e.g. recall, LSTM, false negative", icon=":material/search:").strip().lower()

GLOSSARY = [
    ("Accuracy", "Out of all days, the share the system got right."),
    ("Precision", "When the system says *Flood*, how often it really is a flood."),
    ("Recall", "Of all real floods, the share the system caught."),
    ("F1-score", "A single number balancing precision and recall."),
    ("Balanced accuracy", "Average of recall on flood days and on normal days, fair when one class is bigger."),
    ("ROC-AUC", "How well a model ranks flood days above normal days, ignoring the threshold. 1.0 perfect, 0.5 random."),
    ("Confusion matrix", "A 2×2 table counting caught floods, missed floods, false alarms and correctly calm days."),
    ("False negative", "A real flood the system missed. The most dangerous error here."),
    ("False positive", "A false alarm: the system said Flood on a normal day."),
    ("Threshold (Flood line)", "The probability at which a model switches its answer to Flood."),
    ("Held-out test set", "Data kept aside and never used for training or tuning, used only for the final check."),
    ("Validation set", "A separate period used to choose thresholds, so the test set stays untouched."),
    ("LSTM", "Long Short-Term Memory: a neural network that reads sequences step by step and remembers what matters."),
    ("Embedding / representation", "The LSTM's 32-number summary of the week, given to the Random Forest."),
    ("Random Forest", "Many decision trees that each vote; the majority (average) is the answer."),
    ("Rule engine", "A set of IF–THEN rules that turns scores and readings into a named advisory."),
    ("Forward chaining", "Start from the facts, apply rules in order until one fires, and conclude."),
    ("Occlusion analysis", "Hide one input (set it to its typical value), re-run the model, and measure how much the output changes."),
    ("Sensitivity analysis", "Change inputs on purpose (What-if lab) to see how strongly the output reacts."),
    ("Imputation", "Filling a missing value, here with the training-period average."),
    ("Scaling (standardisation)", "Putting every reading on the same scale so no feature dominates just because of its units."),
    ("Target proxy / leakage", "An input that secretly contains the answer, making a model look better than it really is."),
    ("Reproducibility", "The same input always gives the same output."),
    ("Deployment", "Making a trained system usable by others, here as a website."),
    ("Same-day classification", "Deciding about the last day of the window, not forecasting the future."),
]

VIVA = [
    ("What is the aim of Practical 10?", "To validate the integrated system on unseen data, explain its decisions, discuss ethical, fairness and bias issues, and deploy it through a usable interface."),
    ("Why is Practical 10 separate from Practical 9?", "Practical 9 builds and integrates the components; Practical 10 tests, explains and deploys that finished system."),
    ("Why reuse the trained model instead of retraining?", "So the system we evaluate is exactly the one we deploy. Retraining would silently change it after evaluation."),
    ("What does 'unseen test data' mean here?", "The last 204 days (Mar–Sep 2025), never used for training or for choosing thresholds."),
    ("What was the accuracy on unseen data?", "About 89.7%, with flood recall 83.3%, precision 89.0%, 13 missed floods and 8 false alarms."),
    ("Why not report only accuracy?", "Accuracy hides which errors happen. A missed flood is far worse than a false alarm, so we report recall, precision and the confusion matrix."),
    ("Which error is more serious here and why?", "A false negative (missed flood), because people would not be warned."),
    ("What interpretation technique did you use?", "Occlusion analysis: each reading or day is replaced by its typical value and the change in flood score shows its contribution. Plus the transparent rule path and model agreement."),
    ("Which input matters most?", "Change in water area, followed by rainfall. Together they carry most of the influence."),
    ("Why is relying on water-area change a concern?", "It may be a target proxy: spreading water may be the flood itself, so the model detects rather than predicts."),
    ("What does the rule engine add?", "A readable advisory (Low risk / Monitor / Watch / Warning) and a reason, using forward-chained IF–THEN rules."),
    ("What inference mechanism do the rules use?", "Forward chaining: rules are checked from most to least severe; the first that matches gives the conclusion."),
    ("Why validate input dates?", "The LSTM expects 7 unique, consecutive, ordered days. Gaps or duplicates would change the meaning of the sequence."),
    ("Why not automatically drop duplicate dates?", "Two readings for one day may both be meaningful; a person should decide how to resolve them."),
    ("Why save the scaler, imputer and feature order?", "Inference must transform data exactly as in training, or predictions become invalid."),
    ("What fairness issues exist?", "Performance varies by month; data covers one location only; there is no data about people, so protection of vulnerable groups cannot be measured."),
    ("What bias did you find in the data?", "Flood days occur at about 35% in every month, unlike a real monsoon pattern, suggesting simulated or noisy labels."),
    ("Is this a forecast?", "No. It classifies the last day of the window (same-day), not tomorrow."),
    ("Can emergency services use it?", "No. It needs real data, external validation, calibration, expert thresholds and fairness review first."),
    ("Why Streamlit for deployment?", "It turns Python code into an interactive website quickly, ideal for demonstrating a lab prototype."),
    ("What is reproducibility and how was it tested?", "Same input → same output. The same window was run twice and the probability difference was effectively zero."),
    ("How was the threshold chosen and why not on test data?", "On a separate validation period. Choosing it on test data would leak test information and overstate performance."),
]

g = [(t, d) for t, d in GLOSSARY if not query or query in t.lower() or query in d.lower()]
v = [(q, a) for q, a in VIVA if not query or query in q.lower() or query in a.lower()]

st.subheader(f"Glossary ({len(g)})", icon=":material/menu_book:")
cols = st.columns(2)
for i, (term, desc) in enumerate(g):
    with cols[i % 2].container(border=True):
        st.markdown(f"**{term}**  \n{desc}")
if not g:
    st.caption("No glossary terms match your search.")

st.subheader(f"Viva questions ({len(v)})", icon=":material/quiz:")
for q, a in v:
    with st.expander(q, icon=":material/help:"):
        st.markdown(a)
if not v:
    st.caption("No questions match your search.")
