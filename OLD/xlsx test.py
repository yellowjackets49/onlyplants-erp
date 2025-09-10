import streamlit as st
import pandas as pd
import io

# ✅ No engine specified — Pandas will auto-select (usually openpyxl)
def export_to_excel(df, filename="export.xlsx"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    return buffer.getvalue()

st.title("🔍 Excel Export Test")

# Sample data
df = pd.DataFrame({
    "Product": ["Widget A", "Widget B", "Widget C"],
    "Stock": [100, 50, 0],
    "Price": [10.0, 12.5, 7.99]
})

st.dataframe(df)

st.download_button(
    label="📥 Download Excel",
    data=export_to_excel(df, "test.xlsx"),
    file_name="test.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
