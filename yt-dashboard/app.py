import streamlit as st
import pandas as pd
from fpdf import FPDF
from google import genai

# --- 1. SETUP & UI ---
st.set_page_config(page_title="YouTube Strategy Dashboard", layout="wide")
st.title("📊 YouTube Content Strategist")
st.subheader("Upload your exports to get a professional PDF growth roadmap.")

# Sidebar for API Key (In production, use Streamlit Secrets)
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

# --- 2. FILE UPLOADS ---
col1, col2 = st.columns(2)
with col1:
    totals_file = st.file_uploader("Upload totals.csv", type="csv")
with col2:
    chart_file = st.file_uploader("Upload chart_data.csv", type="csv")

if totals_file and chart_file:
    # Read Data
    df_totals = pd.read_csv(totals_file)
    
    # --- 3. DATA PROCESSING ---
    # Example logic: Categorize by "Duration" if available, or Video Type
    # Note: Check the exact column names in the YouTube export
    long_form = df_totals[df_totals['Average view duration'] > 60] # Simplistic example
    shorts = df_totals[df_totals['Average view duration'] <= 60]

    st.success("Data processed successfully!")

    # --- 4. DISPLAY METRICS ---
    st.write("### Long Form Performance")
    st.dataframe(long_form.head())

    # --- 5. AI INSIGHTS GENERATION ---
    if st.button("Generate AI Strategy"):
        if not api_key:
            st.error("Please enter your API Key in the sidebar.")
        else:
            client = genai.Client(api_key=api_key)
            # Create a summary of the data to send to Gemini
            data_summary = f"Long form views: {long_form['Views'].sum()}, Shorts views: {shorts['Views'].sum()}"
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Analyze these YouTube stats and give 3 things to cut and 3 to double down on: {data_summary}"
            )
            st.write("### Gemini's Strategic Advice")
            st.info(response.text)

    # --- 6. PDF EXPORT ---
    if st.button("Download PDF Report"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="YouTube Growth Report", ln=True, align='C')
        # Add your metrics and AI text here...
        pdf_output = pdf.output(dest='S').encode('latin-1')
        st.download_button(label="📥 Download Report", data=pdf_output, file_name="YT_Report.pdf", mime="application/pdf")
