import streamlit as st
import pandas as pd
from fpdf import FPDF
import io

# --- 1. SAFE DEPENDENCY CHECK ---
try:
    import google.generativeapi as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# --- 2. SETUP ---
st.set_page_config(page_title="YouTube Strategy Dashboard", layout="wide")
st.title("📊 YouTube Growth Strategy")
st.subheader("Data-Driven Content Analysis & Strategic Planning")

# --- 3. CONFIG & HELPERS ---
LIVE_KEYWORDS = ['live!', 'watchalong', 'stream', "let's play", 'd&d', 'diablo', 'ready player nerd']

def load_yt_csv(file):
    raw_bytes = file.getvalue()
    try:
        content = raw_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        content = raw_bytes.decode("utf-16").splitlines()
    
    header_idx = 0
    for i, line in enumerate(content):
        if any(term in line for term in ["Content", "Video title", "Video publish time"]):
            header_idx = i
            break
            
    file.seek(0)
    df = pd.read_csv(file, skiprows=header_idx, sep=None, engine='python')
    df.columns = df.columns.str.strip().str.replace('"', '')
    return df

def find_column(df, possible_names):
    for name in possible_names:
        for col in df.columns:
            if name.lower() in col.lower():
                return col
    return None

def to_num(series):
    return pd.to_numeric(series.astype(str).str.replace(',', '').str.replace('%', ''), errors='coerce').fillna(0)

# PDF Generation Function
def create_analysis_pdf(df, v_m, s_m, l_m):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="YouTube Channel Strategic Audit Data", ln=True, align='C')
    
    # Executive Summary Section
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Executive Summary (2026 Totals)", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 8, txt=(
        f"Videos: {v_m['Published']} posts | {v_m['Subscribers']} Subs | {v_m['Views']} Views | {v_m['CTR']:.2f}% CTR\n"
        f"Shorts: {s_m['Published']} posts | {s_m['Subscribers']} Subs | {s_m['Views']} Views | {s_m['CTR']:.2f}% CTR\n"
        f"Live Streams: {l_m['Published']} posts | {l_m['Subscribers']} Subs | {l_m['Views']} Views"
    ))

    # Granular Data Dump
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Granular Performance List (Videos & Shorts)", ln=True)
    pdf.set_font("Arial", '', 8)
    
    # Header for Table
    pdf.cell(90, 8, "Title", 1)
    pdf.cell(25, 8, "Views", 1)
    pdf.cell(25, 8, "Subs", 1)
    pdf.cell(25, 8, "Watch Hrs", 1)
    pdf.cell(25, 8, "CTR", 1, ln=True)

    for _, row in df.iterrows():
        title = str(row['Video title'])[:50] # Truncate for PDF fit
        pdf.cell(90, 7, title.encode('latin-1', 'ignore').decode('latin-1'), 1)
        pdf.cell(25, 7, str(int(row['Views'])), 1)
        pdf.cell(25, 7, str(int(row['Subscribers'])), 1)
        pdf.cell(25, 7, f"{row['Watch time (hours)']:,.1f}", 1)
        pdf.cell(25, 7, f"{row['Impressions click-through rate (%)']:.1f}%", 1, ln=True)
    
    return pdf.output()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("Strategic Tools")
    if HAS_GENAI:
        api_key = st.text_input("Gemini API Key", type="password")
        if api_key: genai.configure(api_key=api_key)

# --- 5. FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload 'Table Data.csv'", type="csv")

if uploaded_file:
    df_raw = load_yt_csv(uploaded_file)
    
    # Column IDs
    title_col = find_column(df_raw, ['Video title', 'Title'])
    date_col = find_column(df_raw, ['Video publish time', 'Published', 'Date'])
    dur_col = find_column(df_raw, ['Duration'])
    views_col = find_column(df_raw, ['Views'])
    subs_col = find_column(df_raw, ['Subscribers'])
    watch_col = find_column(df_raw, ['Watch time (hours)', 'Watch time'])
    imp_col = find_column(df_raw, ['Impressions'])
    ctr_col = find_column(df_raw, ['Impressions click-through rate (%)', 'CTR'])

    if all([title_col, views_col, subs_col]):
        total_mask = df_raw.iloc[:, 0].astype(str).str.contains('Total', case=False, na=False)
        df_data = df_raw[~total_mask].copy()

        for col in [views_col, subs_col, watch_col, imp_col, ctr_col]:
            if col: df_data[col] = to_num(df_data[col])

        def categorize(row):
            title = str(row[title_col]).lower()
            duration = row[dur_col] if dur_col else 0
            if any(k in title for k in LIVE_KEYWORDS) and duration > 300: return 'Live Stream'
            if '#' in title or duration <= 60: return 'Shorts'
            return 'Videos'

        df_data['Category'] = df_data.apply(categorize, axis=1)
        df_data['Parsed_Date'] = pd.to_datetime(df_data[date_col], errors='coerce')
        df_2026 = df_data[df_data['Parsed_Date'].dt.year == 2026].copy()

        # Calculation Logic
        def get_cat_metrics(df_src, cat_name):
            group = df_src[df_src['Category'] == cat_name]
            total_imps = group[imp_col].sum()
            avg_ctr = (group[ctr_col] * group[imp_col]).sum() / total_imps if total_imps > 0 else 0
            return {"Published": len(group), "Subscribers": group[subs_col].sum(), "Watch Time": group[watch_col].sum(), "CTR": avg_ctr, "Views": group[views_col].sum()}

        v_m = get_cat_metrics(df_2026, 'Videos')
        s_m = get_cat_metrics(df_2026, 'Shorts')
        l_m = get_cat_metrics(df_2026, 'Live Stream')

        # NEW TABS
        tabs = st.tabs(["Performance Summary", "Audit Rankings", "📄 Strategic PDF Export", "🤖 AI Roadmap"])

        with tabs[0]:
            st.markdown("---")
            # (Standard metrics table code here)
            st.table(pd.DataFrame([
                {"Metric": "Subscribers", "Videos": v_m['Subscribers'], "Shorts": s_m['Subscribers'], "Live": l_m['Subscribers']},
                {"Metric": "Views", "Videos": v_m['Views'], "Shorts": s_m['Views'], "Live": l_m['Views']},
            ]).set_index("Metric"))

        with tabs[1]:
            st.write("#### Performance Rankings (See individual metrics for audit)")
            st.dataframe(df_2026[[title_col, views_col, subs_col, watch_col, ctr_col]].sort_values(by=views_col, ascending=False))

        with tabs[2]:
            st.markdown("### 📄 Generate Strategic Audit Document")
            st.write("Click below to generate a formatted PDF containing your full 2026 granular data list for AI analysis.")
            
            pdf_data = create_analysis_pdf(df_2026, v_m, s_m, l_m)
            st.download_button(
                label="📥 Download Strategic Audit PDF",
                data=pdf_data,
                file_name="YouTube_Strategic_Audit_2026.pdf",
                mime="application/pdf"
            )

        with tabs[3]:
            # (The existing AI Prompt and roadmap code)
            st.info("Copy the PDF data or use the API for your Roadmap.")
