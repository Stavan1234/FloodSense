# Practical 10 — Explanation and Viva Guide

## Aim
To validate, interpret, evaluate, and demonstrate deployment of the integrated AI system developed in Practical 9, while checking input reliability and documenting responsible-AI limitations.

## What Practical 10 does
- Reuses the saved LSTM encoder, Random Forest classifier, preprocessing objects, thresholds, and rule engine from Practical 9.
- Checks the held-out test predictions and reports classification metrics and error types.
- Tests valid and invalid input windows, including wrong row count, duplicate dates, date gaps, and missing feature columns.
- Runs the saved integrated pipeline on a real seven-day sample and verifies repeated predictions are consistent.
- Provides a small Streamlit interface for demo input and shows probabilities, the integrated prediction, the rule-based advisory, and the reasons/flags.

## Why reuse Practical 9 artifacts?
The purpose of Practical 10 is validation and deployment readiness, not training another model. Reusing the exact saved model and preprocessing objects ensures the deployed application follows the same pipeline evaluated in Practical 9.

## Key concepts
- **Validation:** Checking whether inputs and system behavior meet expected conditions.
- **Held-out test set:** Data kept separate from model fitting and threshold selection, used for final evaluation.
- **False positive:** The system predicts Flood when the actual label is No Flood.
- **False negative:** The system predicts No Flood when the actual label is Flood.
- **Input validation:** Rejecting malformed data before inference, such as missing columns or non-consecutive dates.
- **Deployment:** Making the saved system available through a usable interface. In this practical, Streamlit provides a small local demo.
- **Reproducibility:** Keeping the model weights, preprocessing, thresholds, and feature order together so predictions can be repeated consistently.
- **Responsible AI:** Reporting model limitations honestly, considering false alarms and missed floods, and avoiding claims unsupported by validation.

## Why these checks matter
A model can return a prediction even when input data is malformed or outside the assumptions used during training. Checking dates, row counts, required columns, numeric values, and deterministic inference prevents several avoidable failures. Confusion matrices show the types of errors rather than hiding them inside one accuracy score.

## Important limitation
The included model performs **same-day classification using a seven-day input window ending on the day being classified**. It does not predict a future day. The dataset and rule thresholds are educational; the application is not an official or validated flood-warning service. Water-area variables may be strongly related to the target labels, so performance must not be interpreted as proof of operational forecasting ability.

## Likely viva questions

1. **Why is Practical 10 separate from Practical 9?**  Practical 9 integrates the components; Practical 10 validates the complete system and demonstrates how it can be used through an interface.
2. **Why do we reuse the trained model?**  To evaluate and deploy the same model rather than silently changing the system after its evaluation.
3. **What is deployment?**  Making a system accessible through an application or service instead of only running it inside a notebook.
4. **Why use Streamlit?**  It provides a simple Python interface with minimal frontend code, suitable for a laboratory demonstration.
5. **Why validate the input dates?**  The LSTM expects seven unique consecutive daily observations in chronological order.
6. **What happens if a date is duplicated?**  The input is rejected so the user can resolve the duplicate properly instead of silently discarding data.
7. **Why not automatically drop duplicate dates?**  Different readings on the same date may be meaningful; they should be investigated or aggregated according to their meaning.
8. **What is a false negative?**  An actual Flood case predicted as No Flood.
9. **Why is a false negative serious here?**  It represents a missed flood case in this educational classification task.
10. **Why not report only accuracy?**  Accuracy can hide the balance of false positives and false negatives; precision, recall, F1-score, and the confusion matrix provide more detail.
11. **What is the purpose of the saved preprocessing objects?**  They ensure the same imputation and scaling learned during training are applied at inference time.
12. **Why save the feature order?**  The model expects inputs in the exact order used during training.
13. **What does the rule engine contribute?**  It applies transparent conditions to model scores and environmental indicators to produce a named advisory.
14. **Does a high model probability guarantee a flood?**  No. It is a model estimate learned from the available dataset, not certainty.
15. **Is this a next-day forecast?**  No. The labelled target is the final day in the seven-day window, so it is same-day classification.
16. **Can this application be used by emergency services?**  No. It lacks independent domain validation, calibrated operational thresholds, expert review, and reliability testing on external data.
17. **What does reproducibility mean?**  Repeating the same inference with the same valid input and saved artifacts produces the same output, within numerical tolerance.
18. **Why test invalid inputs?**  To ensure the application fails clearly and safely instead of producing misleading predictions.
19. **What files are needed to run the app?**  `streamlit_app.py`, `app_pages/`, `flood_ui.py`, `system_core.py`, model artifacts, the demo dataset, and the required Python packages.
20. **What is the conclusion?**  The integrated system was checked using test results and input-validation cases, and exposed through a simple interface; its limitations are documented.
