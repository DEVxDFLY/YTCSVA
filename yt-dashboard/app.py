import streamlit as st
import pandas as pd
from fpdf import FPDF
from google import genai
import io

# --- 1. SETUP & UI ---
st.set_page_config(page_title="YouTube Strategy Dashboard", layout="wide")
st.title("📊 YouTube Content Strategist")
st.subheader("Upload your exports to get a professional PDF growth roadmap.")

# Sidebar for API Key
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

# --- 2. HELPERS: ROBUST DATA LOADING ---
def load_yt_csv(file):
    """Robustly finds the header row and handles different encodings."""
    raw_bytes = file.getvalue()
    try:
        content = raw_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        content = raw_bytes.decode("utf-16").splitlines()
    
    # Hunt for the header: Look for the line that mentions "Views" or "Video title"
    header_idx = 0
    for i, line in enumerate(content):
        if "Views" in line or "Video title" in line or "Subscribers" in line:
            header_idx = i
            break
            
    file.seek(0)
    # sep=None with engine='python' allows pandas to guess comma vs tab
    df = pd.read_csv(file, skiprows=header_idx, sep=None, engine='python')
    df.columns = df.columns.str.strip().str.replace('"', '')
    return df

def find_column(df, possible_names):
    """Finds a column even if the name varies slightly."""
    for name in possible_names:
        if name in df.columns:
            return name
    return None

# --- 3. FILE UPLOADS ---
col1, col2 = st.columns(2)
with col1:
    totals_file = st.file_uploader("Upload totals.csv (Table data)", type="csv")
with col2:
    chart_file = st.file_uploader("Upload chart_data.csv (Time-series)", type="csv")

if totals_file and chart_file:
    # Load and clean data
    df_totals = load_yt_csv(totals_file)
    
    # Identify critical columns
    views_col = find_column(df_totals, ['Views', 'views'])
    subs_col = find_column(df_totals, ['Subscribers', 'subscribers', 'Subscribers gained'])
    title_col = find_column(df_totals, ['Video title', 'Title', 'Content'])

    # --- 4. ERROR HANDLING FOR WRONG FILE TYPE ---
    if "Date" in df_totals.columns and len(df_totals.columns) <= 3:
        st.error("⚠️ **Wrong File Detected:** You uploaded a 'Chart' CSV (Date/Views only). Please go to YouTube Analytics > Advanced Mode and export the **Table Data** CSV instead.")
    
    elif views_col and subs_col:
        # --- 5. DATA PROCESSING ---
        if title_col:
            is_shorts = df_totals[title_col].str.contains('#shorts', case=False, na=False)
            shorts_df = df_totals[is_shorts]
            long_df = df_totals[~is_shorts]
        else:
            long_df = df_totals
            shorts_df = pd.DataFrame()

        st.success(f"Processed {len(long_df)} Long-form videos and {len(shorts_df)} Shorts.")

        # Metrics Calculation (Using to_numeric to handle commas in numbers)
        total_views = pd.to_numeric(long_df[views_col], errors='coerce').sum()
        total_subs = pd.to_numeric(long_df[subs_col], errors='coerce').sum()
        sub_ratio = (total_subs / total_views * 100) if total_views > 0 else 0

        # --- 6. DISPLAY ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Long-form Views", f"{total_views:,.0f}")
        m2.metric("Subscribers Gained", f"{total_subs:,.0f}")
        m3.metric("Sub-to-View Ratio", f"{sub_ratio:.2f}%")

        # --- 7. AI STRATEGY ---
        if 'ai_insight' not in st.session_state:
            st.session_state.ai_insight = ""

        if st.button("Generate AI Growth Strategy"):
            if not api_key:
                st.error("Please enter your Gemini API Key in the sidebar.")
            else:
                try:
                    client = genai.Client(api_key=api_key)
                    top_5 = long_df.nlargest(5, views_col)[title_col].tolist() if title_col else "Unknown"
                    
                    prompt = f"""
                    Analyze these YouTube stats:
                    - Long-form Views: {total_views}
                    - Sub-to-View Ratio: {sub_ratio:.2f}%
                    - Top Content: {top_5}
                    
                    Provide 3 specific things to 'Cut' and 3 things to 'Double Down On'. 
                    No themed lingo. Direct, actionable advice.
                    """
                    
                    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                    st.session_state.ai_insight = response.text
                    st.info(st.session_state.ai_insight)
                except Exception as e:
                    st.error(f"AI Error: {e}")

        # --- 8. PDF EXPORT ---
        if st.button("Download PDF Report"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", 'B', 16)
            pdf.cell(200, 10, txt="YouTube Growth Report", ln=True, align='C')
            
            pdf.set_font("Helvetica", size=12)
            pdf.ln(10)
            pdf.cell(200, 10, txt=f"Total Long-form Views: {total_views:,.0f}", ln=True)
            pdf.cell(200, 10, txt=f"Sub-to-View Ratio: {sub_ratio:.2f}%", ln=True)
            
            if st.session_state.ai_insight:
                pdf.ln(10)
                pdf.set_font("Helvetica", 'B', 14)
                pdf.cell(200, 10, txt="AI Strategic Advice:", ln=True)
                pdf.set_font("Helvetica", size=11)
                # Ensure text is compatible with Latin-1 for PDF generation
                clean_text = st.session_state.ai_insight.encode('latin-1', 'ignore').decode('latin-1')
                pdf.multi_cell(0, 10, txt=clean_text)
            
            pdf_output = pdf.output(dest='S').encode('latin-1', 'ignore')
            st.download_button(label="📥 Download PDF", data=pdf_output, file_name="YouTube_Report.pdf", mime="application/pdf")
    else:
        st.error("Could not find required columns. Ensure you are uploading the 'Table Data' CSV.")
