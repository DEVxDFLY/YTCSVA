import streamlit as st
import pandas as pd
from fpdf import FPDF
from google import genai
import io

# --- 1. SETUP & UI ---
st.set_page_config(page_title="YouTube Strategy Dashboard", layout="wide")
st.title("📊 YouTube Content Strategist")
st.subheader("Upload your Table Data export to get a professional PDF growth roadmap.")

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
    """Finds a column even if the name varies slightly."""
    for name in possible_names:
        if name in df.columns:
            return name
    return None

# --- 3. FILE UPLOADS ---
col1, col2 = st.columns(2)
with col1:
    totals_file = st.file_uploader("Upload Table Data.csv", type="csv")
with col2:
    chart_file = st.file_uploader("Upload Chart Data.csv (Optional)", type="csv")

if totals_file:
    df_totals = load_yt_csv(totals_file)
    
    # Identify critical columns
    views_col = find_column(df_totals, ['Views', 'views'])
    subs_col = find_column(df_totals, ['Subscribers', 'subscribers', 'Subscribers gained'])
    title_col = find_column(df_totals, ['Video title', 'Title', 'Content'])
    imp_col = find_column(df_totals, ['Impressions', 'impressions'])
    ctr_col = find_column(df_totals, ['Impressions click-through rate (%)', 'CTR', 'Click-through rate'])
    watch_col = find_column(df_totals, ['Watch time (hours)', 'Watch time'])
    duration_col = find_column(df_totals, ['Average view duration', 'Avg. view duration'])

    # --- 4. ERROR HANDLING ---
    if "Date" in df_totals.columns and len(df_totals.columns) <= 3:
        st.error("⚠️ **Wrong File:** You uploaded a 'Chart' CSV. Please upload the **Table Data** CSV instead.")
    
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

        # Metrics Calculation
        def calc_metrics(df):
            v = pd.to_numeric(df[views_col], errors='coerce').sum()
            s = pd.to_numeric(df[subs_col], errors='coerce').sum()
            i = pd.to_numeric(df[imp_col], errors='coerce').sum() if imp_col else 0
            w = pd.to_numeric(df[watch_col], errors='coerce').sum() if watch_col else 0
            
            ratio = (s / v * 100) if v > 0 else 0
            total_ctr = (v / i * 100) if i > 0 else 0
            
            return {"views": v, "subs": s, "ratio": ratio, "imps": i, "ctr": total_ctr, "watch": w}

        l_stats = calc_metrics(long_df)
        s_stats = calc_metrics(shorts_df)

        # --- 6. DISPLAY DASHBOARD ---
        st.subheader("📈 Content Reach & Conversion")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Long-form Views", f"{l_stats['views']:,.0f}")
        m2.metric("Sub-to-View Ratio", f"{l_stats['ratio']:.2f}%")
        m3.metric("Total Impressions", f"{l_stats['imps']:,.0f}")
        m4.metric("Average CTR", f"{l_stats['ctr']:.2f}%")

        # Top 5 / Bottom 5 Retention (Long Form)
        if duration_col:
            st.markdown("---")
            st.subheader("⏱️ Retention Leaderboard (Long Form)")
            c_top, c_bot = st.columns(2)
            with c_top:
                st.write("**Top 5 Performers**")
                st.dataframe(long_df.nlargest(5, duration_col)[[title_col, duration_col]])
            with c_bot:
                st.write("**Bottom 5 Performers**")
                st.dataframe(long_df.nsmallest(5, duration_col)[[title_col, duration_col]])

        # --- 7. AI STRATEGY ---
        if 'ai_insight' not in st.session_state:
            st.session_state.ai_insight = ""

        if st.button("Generate AI Growth Strategy"):
            if not api_key:
                st.error("Please enter your Gemini API Key in the sidebar.")
            else:
                try:
                    client = genai.Client(api_key=api_key)
                    top_5_titles = long_df.nlargest(5, views_col)[title_col].tolist() if title_col else "Unknown"
                    
                    prompt = f"""
                    Analyze these YouTube stats:
                    - Long-form Views: {l_stats['views']}
                    - Impressions: {l_stats['imps']}
                    - CTR: {l_stats['ctr']:.2f}%
                    - Sub-to-View Ratio: {l_stats['ratio']:.2f}%
                    - Top Content: {top_5_titles}
                    
                    Identify if the bottleneck is 'Packaging' (CTR) or 'Conversion' (Ratio).
                    Provide 3 specific things to 'Cut' and 3 things to 'Double Down On'. 
                    SKIP all greetings and AI fluff. Give direct, actionable advice only.
                    """
                    
                    response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
                    st.session_state.ai_insight = response.text
                    st.info(st.session_state.ai_insight)
                except Exception as e:
                    st.error(f"AI Error: {e}")

        # --- 8. PDF EXPORT ---
        if st.button("Download PDF Report"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", 'B', 16)
            pdf.cell(200, 10, txt="YouTube Performance Roadmap", ln=True, align='C')
            
            pdf.set_font("Helvetica", size=12)
            pdf.ln(10)
            pdf.cell(200, 10, txt=f"Total Long-form Views: {l_stats['views']:,.0f}", ln=True)
            pdf.cell(200, 10, txt=f"Impressions: {l_stats['imps']:,.0f}", ln=True)
            pdf.cell(200, 10, txt=f"Average CTR: {l_stats['ctr']:.2f}%", ln=True)
            pdf.cell(200, 10, txt=f"Sub-to-View Ratio: {l_stats['ratio']:.2f}%", ln=True)
            
            if st.session_state.ai_insight:
                pdf.ln(10)
                pdf.set_font("Helvetica", 'B', 14)
                pdf.cell(200, 10, txt="AI Strategic Advice:", ln=True)
                pdf.set_font("Helvetica", size=11)
                clean_text = st.session_state.ai_insight.encode('latin-1', 'ignore').decode('latin-1')
                pdf.multi_cell(0, 8, txt=clean_text)
            
            pdf_output = pdf.output(dest='S').encode('latin-1', 'ignore')
            st.download_button(label="📥 Download PDF", data=pdf_output, file_name="YouTube_Growth_Report.pdf", mime="application/pdf")
    else:
        st.error("Required columns (Views/Subscribers) not found. Ensure you are uploading the 'Table Data' export.")
