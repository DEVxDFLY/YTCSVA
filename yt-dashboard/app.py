import streamlit as st
import pandas as pd
from fpdf import FPDF
from google import genai
import io

# --- 1. SETUP & UI ---
st.set_page_config(page_title="YouTube Strategy Dashboard", layout="wide")
st.title("📊 YouTube Content Strategist")
st.markdown("---")

# Sidebar for Setup
with st.sidebar:
    st.header("Setup")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    st.info("💡 **Pro-Tip:** Export the **Table Data** CSV from YouTube Studio > Advanced Mode to see individual video performance.")
    
    with st.expander("How to get your CSVs"):
        st.write("1. Go to **Advanced Mode** in YouTube Analytics.")
        st.write("2. Ensure the **Video** tab is selected.")
        st.write("3. Click the **Export** icon (down arrow).")
        st.write("4. Download the **Comma-separated values (.csv)**.")
        st.write("5. Use the file named **Table Data.csv**.")

# --- 2. HELPERS: ROBUST DATA LOADING ---
def load_yt_csv(file):
    """Detects header row and handles YouTube-specific CSV encodings."""
    raw_bytes = file.getvalue()
    try:
        content = raw_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        content = raw_bytes.decode("utf-16").splitlines()
    
    header_idx = 0
    for i, line in enumerate(content):
        if "Views" in line or "Video title" in line or "Subscribers" in line:
            header_idx = i
            break
            
    file.seek(0)
    df = pd.read_csv(file, skiprows=header_idx, sep=None, engine='python')
    df.columns = df.columns.str.strip().str.replace('"', '')
    return df

def find_column(df, possible_names):
    """Finds a column name regardless of slight variations (case, spacing)."""
    for name in possible_names:
        if name in df.columns:
            return name
    return None

# --- 3. FILE UPLOADS ---
col1, col2 = st.columns(2)
with col1:
    totals_file = st.file_uploader("Upload 'Table Data.csv'", type="csv")
with col2:
    # This is for future expansion (Geo/Demo data)
    geo_file = st.file_uploader("Upload 'Geography.csv' (Optional)", type="csv")

if totals_file:
    df = load_yt_csv(totals_file)
    
    # Identify Core Metrics
    title_col = find_column(df, ['Video title', 'Title', 'Content'])
    views_col = find_column(df, ['Views', 'views'])
    subs_col = find_column(df, ['Subscribers', 'subscribers', 'Subscribers gained'])
    watch_col = find_column(df, ['Watch time (hours)', 'Watch time'])
    retention_col = find_column(df, ['Average view duration', 'Avg. view duration'])

    # Validate if user uploaded the 'Chart' file by mistake
    if "Date" in df.columns and len(df.columns) <= 3:
        st.error("⚠️ **Wrong File:** You uploaded a 'Chart' CSV. Please upload the **Table Data** CSV instead.")
    elif views_col and subs_col:
        
        # --- 4. CATEGORIZATION: Long-form vs Shorts ---
        # Strategy: Use #shorts tag or duration logic
        is_shorts = df[title_col].str.contains('#shorts', case=False, na=False)
        shorts_df = df[is_shorts]
        long_df = df[~is_shorts]

        st.success(f"Dashboard Ready: Analyzed {len(long_df)} Long-form videos and {len(shorts_df)} Shorts.")

        # --- 5. CALCULATION ENGINE ---
        def get_metrics(data, is_shorts=False):
            v = pd.to_numeric(data[views_col], errors='coerce').sum()
            s = pd.to_numeric(data[subs_col], errors='coerce').sum()
            # Calculate Ratio: (Subs / Views) * 100
            ratio = (s / v * 100) if v > 0 else 0
            
            metrics = {
                "Views": v,
                "Subscribers": s,
                "Ratio": ratio
            }
            
            if not is_shorts:
                metrics["Watch Hours"] = pd.to_numeric(data[watch_col], errors='coerce').sum()
            
            return metrics

        long_metrics = get_metrics(long_df)
        shorts_metrics = get_metrics(shorts_df, is_shorts=True)

        # --- 6. DISPLAY DASHBOARD ---
        st.header("🎬 Performance Breakdown")
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Long Form")
            st.metric("Views", f"{long_metrics['Views']:,}")
            st.metric("Subscribers", f"{long_metrics['Subscribers']:,}")
            st.metric("Sub-to-View Ratio", f"{long_metrics['Ratio']:.2f}%")
            st.metric("Watch Hours", f"{long_metrics['Watch Hours']:.1f}")

        with c2:
            st.subheader("Shorts")
            st.metric("Views", f"{shorts_metrics['Views']:,}")
            st.metric("Subscribers", f"{shorts_metrics['Subscribers']:,}")
            st.metric("Sub-to-View Ratio", f"{shorts_metrics['Ratio']:.2f}%")

        # Retention Winners/Losers
        st.markdown("---")
        st.header("⏱️ Retention Deep Dive (Long Form)")
        if retention_col:
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**Top 5 Retention (Best)**")
                st.write(long_df.nlargest(5, retention_col)[[title_col, retention_col]])
            with col_b:
                st.write("**Bottom 5 Retention (Worst)**")
                st.write(long_df.nsmallest(5, retention_col)[[title_col, retention_col]])

        # --- 7. AI STRATEGY ENGINE ---
        if 'strategy' not in st.session_state:
            st.session_state.strategy = ""

        if st.button("🚀 Generate AI Strategy"):
            if not api_key:
                st.warning("Please provide an API Key to get insights.")
            else:
                client = genai.Client(api_key=api_key)
                
                # We feed the AI the real numbers
                prompt = f"""
                Act as a direct, data-driven YouTube growth expert. Analyze these stats:
                - Long Form Ratio: {long_metrics['Ratio']:.2f}%
                - Shorts Ratio: {shorts_metrics['Ratio']:.2f}%
                - Top Retention Videos: {long_df.nlargest(3, retention_col)[title_col].tolist()}
                
                Tell me exactly 3 things to STOP doing and 3 things to DOUBLE DOWN on. 
                Be blunt. Skip the introductions, greetings, and AI fluff. Direct bullets only.
                """
                
                response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                st.session_state.strategy = response.text
                st.info(st.session_state.strategy)

        # --- 8. PDF GENERATION ---
        if st.button("📂 Download PDF Report"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", 'B', 18)
            pdf.cell(200, 10, txt="YouTube Performance Roadmap", ln=True, align='C')
            
            pdf.set_font("Helvetica", size=12)
            pdf.ln(10)
            pdf.cell(100, 10, txt=f"Long Form Views: {long_metrics['Views']:,}", ln=True)
            pdf.cell(100, 10, txt=f"Sub-to-View Ratio: {long_metrics['Ratio']:.2f}%", ln=True)
            pdf.cell(100, 10, txt=f"Watch Hours: {long_metrics['Watch Hours']:.1f}", ln=True)

            if st.session_state.strategy:
                pdf.ln(10)
                pdf.set_font("Helvetica", 'B', 14)
                pdf.cell(100, 10, txt="AI Strategic Recommendations:", ln=True)
                pdf.set_font("Helvetica", size=10)
                # Clean text for PDF format
                clean_text = st.session_state.strategy.encode('latin-1', 'ignore').decode('latin-1')
                pdf.multi_cell(0, 8, txt=clean_text)

            pdf_output = pdf.output(dest='S').encode('latin-1', 'ignore')
            st.download_button("📥 Download My Report", data=pdf_output, file_name="YouTube_Growth_Report.pdf")

    else:
        st.error("Required columns missing. Please ensure you are using the 'Table Data' export.")
