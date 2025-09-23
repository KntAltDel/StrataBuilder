import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Strata Logic Builder", layout="wide")
st.title("📊 Strata Logic Builder")

st.markdown("""
Upload a profiling CSV (must contain a column of distinct values and metric columns like Count, Count_Pct, Sum_Amount, Amount_Pct).
Build rules (Metric + Operator + Threshold) and export the strata rules + preview mapping to Excel.
""")

uploaded_file = st.file_uploader("Upload Profile Results CSV", type=["csv"])
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        st.stop()

    st.subheader("Profile Results - Preview")
    st.dataframe(df.head(30), use_container_width=True)

    # Let user choose which column represents the distinct value (Column_Value)
    value_col = st.selectbox("Choose column that contains distinct values (e.g. Column_Value)", df.columns)

    # Detect metric candidates (prefer known names; fallback numeric columns)
    def detect_metric_candidates(df):
        candidates = []
        preferred = ["count_pct", "amount_pct", "sum_amount", "count", "sum", "amount"]
        for c in df.columns:
            lc = c.lower()
            if any(p in lc for p in preferred):
                candidates.append(c)
        # fallback: add numeric columns not already included
        for c in df.select_dtypes(include=["number"]).columns:
            if c not in candidates:
                candidates.append(c)
        return list(dict.fromkeys(candidates))

    metric_candidates = detect_metric_candidates(df)
    st.write("Detected metric columns (you may choose any for rule building):", metric_candidates)

    if not metric_candidates:
        st.warning("No metric columns detected. Make sure CSV includes Count, Count_Pct, Sum_Amount, or Amount_Pct.")
        st.stop()

    st.subheader("Define Strata Rules")
    num_rules = st.number_input("How many rules will you define?", min_value=1, max_value=12, value=2)

    rules = []
    for i in range(int(num_rules)):
        st.markdown(f"**Rule {i+1}**")
        cols = st.columns([3,2,2,2,3])
        metric = cols[0].selectbox("Metric", metric_candidates, key=f"metric_{i}")
        operator = cols[1].selectbox("Operator", [">", ">=", "<", "<=", "=", "between"], key=f"op_{i}")
        if operator == "between":
            low = cols[2].number_input("Lower", key=f"low_{i}")
            high = cols[3].number_input("Upper", key=f"high_{i}")
            threshold = (low, high)
        else:
            thr = cols[2].number_input("Threshold", key=f"thr_{i}")
            threshold = thr
        label = cols[4].text_input("Bin Label", value=f"BIN_{i+1}", key=f"label_{i}")
        rules.append({
            "rule_id": i+1,
            "column_name": value_col,
            "metric": metric,
            "operator": operator,
            "threshold": threshold,
            "label": label
        })

    # --- Apply rules to preview mapping ---
    st.subheader("Preview Mapping (first 100 distinct values)")
    preview_cols = [value_col] + metric_candidates
    preview_df = df[preview_cols].copy()
    # Ensure metrics numeric
    for m in metric_candidates:
        preview_df[m] = pd.to_numeric(preview_df[m], errors="coerce")

    preview_df["Assigned_Bin"] = None

    for r in rules:
        metric = r["metric"]
        op = r["operator"]
        thr = r["threshold"]
        if op == "between":
            low, high = thr
            mask = preview_df[metric].between(low, high)
        else:
            try:
                val = float(thr)
            except:
                val = None
            if val is None:
                mask = pd.Series([False] * len(preview_df))
            else:
                if op == ">":
                    mask = preview_df[metric] > val
                elif op == ">=":
                    mask = preview_df[metric] >= val
                elif op == "<":
                    mask = preview_df[metric] < val
                elif op == "<=":
                    mask = preview_df[metric] <= val
                elif op == "=":
                    mask = preview_df[metric] == val
                else:
                    mask = pd.Series([False] * len(preview_df))

        # assign only if not already assigned (first-match precedence)
        preview_df.loc[mask & preview_df["Assigned_Bin"].isna(), "Assigned_Bin"] = r["label"]

    st.dataframe(preview_df.head(100), use_container_width=True)

    # show counts per bin
    st.markdown("**Bin summary**")
    st.dataframe(preview_df.groupby("Assigned_Bin").agg({value_col:"count"}).rename(columns={value_col:"DistinctValuesCount"}))

    # Export Excel
    if st.button("📥 Export Strata Logic to Excel"):
        export_rules = pd.DataFrame(rules)
        # human friendly preview: keep only relevant columns
        preview_for_export = preview_df[[value_col, "Assigned_Bin"] + metric_candidates].copy()
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            export_rules.to_excel(writer, index=False, sheet_name="StrataRules")
            preview_for_export.to_excel(writer, index=False, sheet_name="PreviewMapping")
            # optionally include a README sheet
            pd.DataFrame({
                "Notes": [
                    "Rules are applied in order (first matching rule wins).",
                    "Thresholds must be expressed in same units as the metric column in the CSV.",
                    "Use Count_Pct and Amount_Pct as percentages (e.g. 50 for 50%)."
                ]
            }).to_excel(writer, index=False, sheet_name="README")
        data = output.getvalue()
        st.download_button(
            label="Download strata_logic.xlsx",
            data=data,
            file_name="strata_logic.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("Upload a profiling CSV to begin. You can also use the sample data in the repo (profiling_sample.csv).")
