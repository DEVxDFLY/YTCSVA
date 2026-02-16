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
    """Skips YouTube metadata rows and cleans headers."""
    # Read first 5 lines to find where the actual header starts
    # YouTube exports usually have 1-2 lines of 'Total' info before headers
    df = pd.read_csv(file, skiprows=1)
    df.columns = df.columns.str.strip()
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
    time_col = find_column(df_totals, ['Average view duration', 'Avg. view duration', 'Watch time (hours)'])
    title_col = find_column(df_totals, ['Video title', 'Title', 'Content'])

    if views_col and subs_col:
        # --- 4. DATA PROCESSING ---
        # Splitting Long Form vs Shorts (Usually based on title containing #Shorts or duration)
        # For this version, we'll check for #shorts in the title if available
        if title_col:
            is_shorts = df_totals[title_col].str.contains('#shorts', case=False, na=False)
            shorts_df = df_totals[is_shorts]
            long_df = df_totals[~is_shorts]
        else:
            # Fallback: Treat as one list if titles are missing
            long_df = df_totals
            shorts_df = pd.DataFrame()

        st.success(f"Processed {len(long_df)} Long-form videos and {len(shorts_df)} Shorts.")

        # Metrics Calculation
        total_views = long_df[views_col].sum()
        total_subs = long_df[subs_col].sum()
        sub_ratio = (total_subs / total_views * 100) if total_views > 0 else 0

        # --- 5. DISPLAY ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Long-form Views", f"{total_views:,}")
        m2.metric("Subscribers Gained", f"{total_subs:,}")
        m3.metric("Sub-to-View Ratio", f"{sub_ratio:.2f}%")

        # --- 6. AI STRATEGY ---
        ai_insight = ""
        if st.button("Generate AI Growth Strategy"):
            if not api_key:
                st.error("Please enter your Gemini API Key in the sidebar.")
            else:
                try:
                    client = genai.Client(api_key=api_key)
                    # Create a condensed data snippet for the AI
                    top_5 = long_df.nlargest(5, views_col)[title_col].tolist() if title_col else "Unknown"
                    
                    prompt = f"""
                    Analyze these YouTube stats:
                    - Long-form Views: {total_views}
                    - Sub-to-View Ratio: {sub_ratio:.2f}%
                    - Top Content: {top_5}
                    
                    Provide 3 specific things to 'Cut' and 3 things to 'Double Down On' based on performance.
                    Skip the themed lingo. Give direct, actionable advice.
                    """
                    
                    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                    ai_insight = response.text
                    st.info(ai_insight)
                except Exception as e:
                    st.error(f"AI Error: {e}")

        # --- 7. PDF EXPORT ---
        if st.button("Download PDF Report"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="YouTube Growth Report", ln=True, align='C')
            
            pdf.set_font("Arial", size=12)
            pdf.ln(10)
            pdf.cell(200, 10, txt=f"Total Long-form Views: {total_views:,}", ln=True)
            pdf.cell(200, 10, txt=f"Sub-to-View Ratio: {sub_ratio:.2f}%", ln=True)
            
            if ai_insight:
                pdf.ln(10)
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(200, 10, txt="AI Strategic Advice:", ln=True)
                pdf.set_font("Arial", size=11)
                pdf.multi_cell(0, 10, txt=ai_insight)
            
            # Export
            pdf_output = pdf.output(dest='S').encode('latin-1', 'ignore')
            st.download_button(
                label="📥 Download PDF",
                data=pdf_output,
                file_name="YouTube_Strategy_Report.pdf",
                mime="application/pdf"
            )
    else:
        st.error("Could not find required columns (Views/Subscribers). Please check your CSV format.")
