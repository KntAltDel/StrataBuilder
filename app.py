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
                                    [c for c in profile_df.columns if c not in ["Column_Value", "Profile_Func_Id"]])

    # Step 3: Number of rules
    num_rules = st.number_input("How many rules will you define?", min_value=1, max_value=10, value=1)

    # Store bin logic
    strata_rules = []

    for i in range(num_rules):
        st.subheader(f"Rule {i+1}")
        rule_name = st.text_input(f"Name for Rule {i+1}", f"Rule_{i+1}")
        selected_column = st.selectbox(f"Select column for {rule_name}", [c for c in profile_df.columns], key=f"col_{i}")
        selected_metric = st.selectbox(f"Select metric for {rule_name}", metric_columns, key=f"metric_{i}")
        operator = st.selectbox(f"Condition for {rule_name}", [">", "<", ">=", "<=", "=", "!="], key=f"op_{i}")
        threshold = st.text_input(f"Threshold value for {rule_name}", key=f"thr_{i}")

        # Look up Profile_Func_Id for selected column
        profile_func_id = None
        if "Profile_Func_Id" in profile_df.columns and "Column_Name" in profile_df.columns:
            row = profile_df.loc[profile_df["Column_Name"] == selected_column]
            if not row.empty:
                profile_func_id = row["Profile_Func_Id"].iloc[0]

        if selected_metric and operator and threshold and profile_func_id is not None:
            # Simple bin logic string
            logic = f"{selected_metric} {operator} {threshold}"

            # Bin_Profile_Values_Logic SQL
            bin_profile_values_logic = (
                f'SELECT Column_Value FROM Profile_Results '
                f'WHERE Profile_Func_Id = "{profile_func_id}" AND {logic}'
            )

            strata_rules.append({
                "Bin_Name": rule_name,
                "Column_Name": selected_column,
                "Profile_Func_Id": profile_func_id,
                "Logic": logic,
                "Bin_Profile_Values_Logic": bin_profile_values_logic
            })

    if strata_rules:
        st.write("### Strata Rules")
        rules_df = pd.DataFrame(strata_rules)
        st.dataframe(rules_df)

        # Step 4: Cartesian of bins
        if st.button("Generate Strata Cartesian"):
            strata_list = []
            bin_names = [r["Bin_Name"] for r in strata_rules]

            for combo in itertools.product(bin_names, repeat=len(metric_columns)):
                combo_name = "_".join(combo)
                combo_sql = " AND ".join([r["Bin_Profile_Values_Logic"] for r in strata_rules if r["Bin_Name"] in combo])
                strata_list.append({"Strata_Name": combo_name, "SQL_Logic": combo_sql})

            strata_df = pd.DataFrame(strata_list)
            st.write("### Strata Cartesian Output")
            st.dataframe(strata_df)

            # Download to Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                rules_df.to_excel(writer, sheet_name="Strata_Rules", index=False)
                strata_df.to_excel(writer, sheet_name="Strata_Cartesian", index=False)

            st.download_button(
                label="Download Output as Excel",
                data=buffer,
                file_name="Stratas_Output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
