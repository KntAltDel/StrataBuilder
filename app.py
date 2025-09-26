import streamlit as st
import pandas as pd
import itertools
import io

st.set_page_config(page_title="Strata Logic Builder", layout="wide")

st.title("📊 Strata Logic & SQL Builder")

# Upload profile results
uploaded_file = st.file_uploader("Upload Profile Results CSV", type=["csv"])
if uploaded_file:
    profile_df = pd.read_csv(uploaded_file)
    st.write("### Profile Results Preview")
    st.dataframe(profile_df.head())

    # Step 1: Select column to profile
    column_value = st.selectbox("Choose column containing distinct values:", profile_df.columns)

    # Step 2: Select metric columns
    metric_columns = st.multiselect("Choose metric columns for rule building:", 
                                    [c for c in profile_df.columns if c != column_value])

    # Step 3: Number of rules
    num_rules = st.number_input("How many rules will you define?", min_value=1, max_value=10, value=1)

    # Store bin logic
    bin_definitions = []
    sql_definitions = {}

    for i in range(num_rules):
        st.subheader(f"Rule {i+1}")
        rule_name = st.text_input(f"Name for Rule {i+1}", f"Rule_{i+1}")
        selected_metric = st.selectbox(f"Select metric for {rule_name}", metric_columns, key=f"metric_{i}")
        operator = st.selectbox(f"Condition for {rule_name}", [">", "<", ">=", "<=", "=", "!="], key=f"op_{i}")
        threshold = st.text_input(f"Threshold value for {rule_name}", key=f"thr_{i}")

        if selected_metric and operator and threshold:
            logic = f"{selected_metric} {operator} {threshold}"
            bin_definitions.append((rule_name, logic))

            # SQL logic
            sql_definitions[rule_name] = f"CASE WHEN {logic} THEN '{rule_name}' END"

    st.write("### Bin Logic Defined")
    st.table(pd.DataFrame(bin_definitions, columns=["Bin Name", "Logic"]))

    st.write("### SQL Snippets for Each Bin")
    for rule, sql in sql_definitions.items():
        st.code(sql, language="sql")

    # Step 4: Cartesian of bins (Strata)
    if st.button("Generate Strata Cartesian"):
        strata_list = []
        rule_names = [rule for rule, _ in bin_definitions]
        for combo in itertools.product(rule_names, repeat=len(metric_columns)):
            combo_name = "_".join(combo)
            combo_sql = " AND ".join([sql_definitions[r] for r in combo])
            strata_list.append({"Strata_Name": combo_name, "SQL_Logic": combo_sql})

        strata_df = pd.DataFrame(strata_list)
        st.write("### Strata Cartesian Output")
        st.dataframe(strata_df)

        # Download to Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            strata_df.to_excel(writer, sheet_name="Strata", index=False)
        st.download_button(
            label="Download Strata Output as Excel",
            data=buffer,
            file_name="Stratas_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
