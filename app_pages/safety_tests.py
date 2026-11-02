import numpy as np
import pandas as pd
import streamlit as st

from flood_ui import ENVIRONMENTAL_FEATURES, FRIENDLY_NAMES, ADVISORY_STYLE, load_dataset, load_system, load_test_predictions, pct, window_ending

system = load_system()
df = load_dataset()
preds = load_test_predictions()
valid = window_ending(df, preds["date"].iloc[-1], system.window_days)[["date"] + ENVIRONMENTAL_FEATURES].reset_index(drop=True)

st.title("Input safety tests", icon=":material/shield:")
st.markdown(
    "A deployed AI must **refuse bad data** instead of quietly producing a misleading answer. "
    "These tests feed the real system deliberately broken inputs and check that each one is rejected with a clear message. "
    "They also check that the same input always gives the same answer (**reproducibility**)."
)


def build_cases():
    short = valid.iloc[:-1].copy()
    dup = valid.copy(); dup.loc[6, "date"] = dup.loc[5, "date"]
    gap = valid.copy(); gap.loc[6, "date"] = gap.loc[6, "date"] + pd.Timedelta(days=2)
    missing_col = valid.drop(columns=["precipitation"])
    text_col = valid.copy(); text_col["precipitation"] = "not-a-number"
    bad_date = valid.copy(); bad_date["date"] = bad_date["date"].astype(str); bad_date.loc[3, "date"] = "31-31-2025"
    one_blank = valid.copy(); one_blank.loc[2, "humidity"] = np.nan
    shuffled = valid.sample(frac=1, random_state=1)
    return [
        ("Seven valid consecutive days", valid, True, "The normal case must work."),
        ("Only six days", short, False, "The LSTM was trained on exactly 7 days; fewer days would change its meaning."),
        ("A date appears twice", dup, False, "Two readings for one day must be resolved by a person, not silently dropped."),
        ("A day is missing (gap)", gap, False, "A gap would make the model treat 8 days as 7."),
        ("A required column is missing", missing_col, False, "The model cannot guess a whole missing measurement."),
        ("A column contains only text", text_col, False, "Non-numbers would break scaling and produce nonsense."),
        ("An impossible date", bad_date, False, "Unreadable dates make the sequence order unknown."),
        ("One blank cell", one_blank, True, "A single gap is filled using the training-period average (imputation)."),
        ("Rows in the wrong order", shuffled, True, "Rows are sorted by date before use, so order does not matter."),
    ]


if st.button("Run all safety tests", type="primary", icon=":material/play_arrow:"):
    rows = []
    for name, data, should_accept, why in build_cases():
        try:
            system.predict_window(data)
            accepted, message = True, "Accepted and processed"
        except Exception as exc:
            accepted, message = False, str(exc)
        rows.append({
            "Result": "PASS" if accepted == should_accept else "FAIL",
            "Test": name,
            "Expected": "Accept" if should_accept else "Reject",
            "What happened": "Accepted" if accepted else "Rejected",
            "Message shown to the user": message,
            "Why it matters": why,
        })
    a = system.predict_window(valid); b = system.predict_window(valid)
    diff = abs(a["integrated_probability"] - b["integrated_probability"])
    rows.append({
        "Result": "PASS" if diff < 1e-7 and a["AI_advisory"] == b["AI_advisory"] else "FAIL",
        "Test": "Same input twice gives the same answer", "Expected": "Identical", "What happened": f"Difference {diff:.1e}",
        "Message shown to the user": f"Both runs: {ADVISORY_STYLE[a['AI_advisory']]['headline']}, {pct(a['integrated_probability'])}",
        "Why it matters": "A trustworthy system must be reproducible.",
    })
    st.session_state.safety = pd.DataFrame(rows)

res = st.session_state.get("safety")
if res is not None:
    passed = int((res["Result"] == "PASS").sum())
    if passed == len(res):
        st.success(f"All **{passed} of {len(res)}** tests passed.", icon=":material/verified_user:", title="Safety checks passed")
    else:
        st.error(f"{passed} of {len(res)} tests passed.", icon=":material/gpp_bad:")
    st.dataframe(
        res, hide_index=True, alt="Results of input validation tests",
        column_config={"Result": st.column_config.TextColumn(width="small"),
                       "Message shown to the user": st.column_config.TextColumn(width="large"),
                       "Why it matters": st.column_config.TextColumn(width="large")},
    )
else:
    st.caption("Press the button to run the tests against the live system.")

st.subheader("Try to break it yourself", icon=":material/build:")
st.markdown(
    "Below is a real, valid 7-day window. **Edit any cell, change a date, or delete/add rows** "
    "(select a row and press Delete, or use the + at the bottom). Then press *Validate*."
)
edited = st.data_editor(
    valid.assign(date=valid["date"].dt.strftime("%Y-%m-%d")).rename(columns=FRIENDLY_NAMES),
    num_rows="dynamic", hide_index=True, key="breaker",
)
if st.button("Validate my edited window", icon=":material/fact_check:"):
    candidate = edited.rename(columns={v: k for k, v in FRIENDLY_NAMES.items()})
    try:
        out = system.predict_window(candidate)
        s = ADVISORY_STYLE[out["AI_advisory"]]
        st.success(f"Input accepted. Result: **:{s['color']}[{s['headline']}]** with a flood score of "
                   f"**{pct(out['integrated_probability'])}**.", icon=":material/check_circle:")
    except Exception as exc:
        st.error(f"{exc}", title="Input rejected", icon=":material/block:")
