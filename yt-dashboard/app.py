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
st.subheader("Professional Content Audit & Strategic Planning")

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

# CATEGORIZED PDF GENERATOR
def create_categorized_pdf(df_source, v_m, s_m, l_m):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="YouTube Strategic Content Audit (Categorized)", ln=True, align='C')
    
    # Summary Section
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Format Efficiency Summary (2026)", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 7, txt=(
        f"Long-form: {v_m['Published']} posts | {v_m['Subscribers']} Subs | {v_m['Views']:,} Views | {v_m['CTR']:.2f}% Avg CTR\n"
        f"Shorts: {s_m['Published']} posts | {s_m['Subscribers']} Subs | {s_m['Views']:,} Views | {s_m['CTR']:.2f}% Avg CTR\n"
        f"Live Streams: {l_m['Published']} posts | {l_m['Subscribers']} Subs | {l_m['Views']:,} Views"
    ))

    # Helper for tables
    def add_category_section(pdf_obj, data, title):
        if data.empty:
            return
        pdf_obj.ln(10)
        pdf_obj.set_font("Arial", 'B', 12)
        pdf_obj.cell(200, 10, txt=f"Category: {title}", ln=True)
        
        pdf_obj.set_font("Arial", 'B', 9)
        pdf_obj.cell(85, 8, "Title (Truncated)", 1)
        pdf_obj.cell(25, 8, "Views", 1)
        pdf_obj.cell(20, 8, "Subs", 1)
        pdf_obj.cell(25, 8, "Watch Hrs", 1)
        pdf_obj.cell(20, 8, "CTR", 1, ln=True)

        pdf_obj.set_font("Arial", '', 8)
        for _, row in data.sort_values(by='Views', ascending=False).iterrows():
            clean_title = str(row['Video title'])[:45].encode('latin-1', 'ignore').decode('latin-1')
            pdf_obj.cell(85, 7, clean_title, 1)
            pdf_obj.cell(25, 7, f"{row['Views']:,.0f}", 1)
            pdf_obj.cell(20, 7, f"{row['Subscribers']:,.0f}", 1)
            pdf_obj.cell(25, 7, f"{row['Watch time (hours)']:,.1f}", 1)
            pdf_obj.cell(20, 7, f"{row['Impressions click-through rate (%)']:.1f}%", 1, ln=True)

    # Add Sections
    add_category_section(pdf, df_source[df_source['Category'] == 'Videos'], "Long-form Videos")
    add_category_section(pdf, df_source[df_source['Category'] == 'Shorts'], "Shorts")
    add_category_section(pdf, df_source[df_source['Category'] == 'Live Stream'], "Live Streams")
    
    return bytes(pdf.output())

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Gemini API Key", type="password")
    if api_key and HAS_GENAI:
        genai.configure(api_key=api_key)

# --- 5. DATA PROCESSING ---
uploaded_file = st.file_uploader("Upload 'Table Data.csv'", type="csv")

if uploaded_file:
    df_raw = load_yt_csv(uploaded_file)
    
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
        total_row = df_raw[total_mask].iloc[0] if total_mask.any() else None
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

        def get_stats(df_src, cat):
            group = df_src[df_src['Category'] == cat]
            total_imps = group[imp_col].sum()
            avg_ctr = (group[ctr_col] * group[imp_col]).sum() / total_imps if total_imps > 0 else 0
            return {"Published": len(group), "Subscribers": group[subs_col].sum(), "Watch Time": group[watch_col].sum(), "CTR": avg_ctr, "Views": group[views_col].sum()}

        v_m = get_stats(df_2026, 'Videos')
        s_m = get_stats(df_2026, 'Shorts')
        l_m = get_stats(df_2026, 'Live Stream')

        chan_subs = total_row[subs_col] if total_row is not None else (v_m['Subscribers'] + s_m['Subscribers'] + l_m['Subscribers'])
        other_subs = chan_subs - (v_m['Subscribers'] + s_m['Subscribers'] + l_m['Subscribers'])

        # --- TABS ---
        t1, t2, t3, t4 = st.tabs(["Summary", "Format Audit", "📄 Export Categorized PDF", "🤖 Strategy Roadmap"])

        with t1:
            st.markdown("### 2026 Performance Overview")
            h1, h2, h3 = st.columns(3)
            h1.metric("Published", f"{v_m['Published'] + s_m['Published'] + l_m['Published']}")
            h2.metric("Subs Gained", f"{chan_subs:,.0f}")
            h3.metric("Other Sources", f"{max(0, other_subs):,.0f}")
            
            summary_table = [
                {"Metric": "Subscribers", "Videos": f"{v_m['Subscribers']:,.0f}", "Shorts": f"{s_m['Subscribers']:,.0f}", "Live Streams": f"{l_m['Subscribers']:,.0f}", "Other": f"{other_subs:,.0f}"},
                {"Metric": "Watch Time (Hrs)", "Videos": f"{v_m['Watch Time']:,.1f}", "Shorts": f"{s_m['Watch Time']:,.1f}", "Live Streams": f"{l_m['Watch Time']:,.1f}", "Other": "—"},
                {"Metric": "Avg CTR", "Videos": f"{v_m['CTR']:.2f}%", "Shorts": f"{s_m['CTR']:.2f}%", "Live Streams": f"{l_m['CTR']:.2f}%", "Other": "—"}
            ]
            st.table(pd.DataFrame(summary_table).set_index("Metric"))

        with t2:
            st.markdown("### 🔍 Granular Format Audit")
            def show_ranks(df, label):
                st.write(f"**Top Performing {label} (by Views)**")
                st.table(df.sort_values(by=views_col, ascending=False).head(5)[[title_col, views_col, watch_col, ctr_col]].reset_index(drop=True))

            show_ranks(df_2026[df_2026['Category']=='Videos'], "Long-form Videos")
            show_ranks(df_2026[df_2026['Category']=='Shorts'], "Shorts")

        with t3:
            st.markdown("### 📄 Categorized Audit Document")
            st.info("This PDF organizes your entire content library by category, making it significantly easier for AI to perform a detailed strategic analysis.")
            try:
                categorized_pdf = create_categorized_pdf(df_2026, v_m, s_m, l_m)
                st.download_button(
                    label="📥 Download Categorized Strategic Audit",
                    data=categorized_pdf,
                    file_name="YouTube_Categorized_Audit.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Generation Error: {e}")

        with t4:
            st.markdown("### 🤖 Strategy Roadmap")
            v_roi = v_m['Subscribers'] / v_m['Published'] if v_m['Published'] > 0 else 0
            s_roi = s_m['Subscribers'] / s_m['Published'] if s_m['Published'] > 0 else 0

            prompt = f"""
            SYSTEM ROLE: Senior Strategy Consultant.
            OBJECTIVE: Audit the attached 2026 data categorized by Long-form, Shorts, and Live.
            
            EFFICIENCY (Subs per post):
            - Long-form: {v_roi:.2f} | Shorts: {s_roi:.2f}
            
            TASK: Identify specific topics or formats that should be STOPPED (low ROI) vs prioritized (high efficiency). 
            Spot the 'Grey Area' content. Focus strictly on objective reasoning. No themed lingo.
            """
            st.info("Upload the Categorized PDF to Gemini and use this prompt:")
            st.code(prompt, language="markdown")
