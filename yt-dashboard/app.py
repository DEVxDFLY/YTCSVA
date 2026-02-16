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

# FIXED PDF GENERATOR
def create_analysis_pdf(df_source, v_m, s_m, l_m):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="YouTube Strategic Content Audit", ln=True, align='C')
    
    # Summary Section
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Executive Efficiency Metrics (2026)", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 8, txt=(
        f"Videos: {v_m['Published']} posts | {v_m['Subscribers']} Subs | {v_m['Views']:,} Views | {v_m['CTR']:.2f}% CTR\n"
        f"Shorts: {s_m['Published']} posts | {s_m['Subscribers']} Subs | {s_m['Views']:,} Views | {s_m['CTR']:.2f}% CTR\n"
        f"Live Streams: {l_m['Published']} posts | {l_m['Subscribers']} Subs | {l_m['Views']:,} Views"
    ))

    # Data Dump Header
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(85, 8, "Title (Truncated)", 1)
    pdf.cell(25, 8, "Views", 1)
    pdf.cell(20, 8, "Subs", 1)
    pdf.cell(25, 8, "Watch Hrs", 1)
    pdf.cell(20, 8, "CTR", 1, ln=True)

    pdf.set_font("Arial", '', 8)
    # Sort for the AI to see the biggest impact first
    for _, row in df_source.sort_values(by='Views', ascending=False).iterrows():
        title = str(row['Video title'])[:45]
        pdf.cell(85, 7, title.encode('latin-1', 'ignore').decode('latin-1'), 1)
        pdf.cell(25, 7, f"{row['Views']:,.0f}", 1)
        pdf.cell(20, 7, f"{row['Subscribers']:,.0f}", 1)
        pdf.cell(25, 7, f"{row['Watch time (hours)']:,.1f}", 1)
        pdf.cell(20, 7, f"{row['Impressions click-through rate (%)']:.1f}%", 1, ln=True)
    
    # Return as bytes for Streamlit
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
        # Separate Total Row
        total_mask = df_raw.iloc[:, 0].astype(str).str.contains('Total', case=False, na=False)
        total_row = df_raw[total_mask].iloc[0] if total_mask.any() else None
        df_data = df_raw[~total_mask].copy()

        # Clean Metrics
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
        def get_stats(df_src, cat):
            group = df_src[df_src['Category'] == cat]
            total_imps = group[imp_col].sum()
            avg_ctr = (group[ctr_col] * group[imp_col]).sum() / total_imps if total_imps > 0 else 0
            return {
                "Published": len(group), 
                "Subscribers": group[subs_col].sum(), 
                "Watch Time": group[watch_col].sum(), 
                "CTR": avg_ctr, 
                "Views": group[views_col].sum()
            }

        v_m = get_stats(df_2026, 'Videos')
        s_m = get_stats(df_2026, 'Shorts')
        l_m = get_stats(df_2026, 'Live Stream')

        # Channels Totals
        chan_subs = total_row[subs_col] if total_row is not None else (v_m['Subscribers'] + s_m['Subscribers'] + l_m['Subscribers'])
        other_subs = chan_subs - (v_m['Subscribers'] + s_m['Subscribers'] + l_m['Subscribers'])

        # --- TABS ---
        t1, t2, t3, t4 = st.tabs(["Performance Summary", "Ranking Audit", "📄 Export Audit PDF", "🤖 Strategic Roadmap"])

        with t1:
            st.markdown("### 2026 Channel Summary")
            h1, h2, h3 = st.columns(3)
            h1.metric("Total Published", f"{v_m['Published'] + s_m['Published'] + l_m['Published']}")
            h2.metric("Total Subs Gained", f"{chan_subs:,.0f}")
            h3.metric("Other Subscribers", f"{max(0, other_subs):,.0f}")
            
            summary_table = [
                {"Metric": "Subscribers", "Videos": f"{v_m['Subscribers']:,.0f}", "Shorts": f"{s_m['Subscribers']:,.0f}", "Live Streams": f"{l_m['Subscribers']:,.0f}", "Other": f"{other_subs:,.0f}"},
                {"Metric": "Watch Time (Hrs)", "Videos": f"{v_m['Watch Time']:,.1f}", "Shorts": f"{s_m['Watch Time']:,.1f}", "Live Streams": f"{l_m['Watch Time']:,.1f}", "Other": "—"},
                {"Metric": "Average CTR", "Videos": f"{v_m['CTR']:.2f}%", "Shorts": f"{s_m['CTR']:.2f}%", "Live Streams": f"{l_m['CTR']:.2f}%", "Other": "—"}
            ]
            st.table(pd.DataFrame(summary_table).set_index("Metric"))

        with t2:
            st.markdown("### 🔍 Video & Shorts Deep Dive")
            def show_ranks(df, sort_col, label, is_ctr=False):
                sorted_df = df.sort_values(by=sort_col, ascending=False).head(5)
                # Keep CTR and Watch Time visible for context
                disp = sorted_df[[title_col, sort_col, watch_col, ctr_col]].copy()
                disp[ctr_col] = disp[ctr_col].map("{:.2f}%".format)
                if not is_ctr: disp[sort_col] = disp[sort_col].map("{:,.0f}".format)
                st.write(f"**Top 5 {label}**")
                st.table(disp.reset_index(drop=True))

            c1, c2 = st.columns(2)
            with c1:
                show_ranks(df_data[df_data['Category']=='Videos'], views_col, "Videos by Views")
            with c2:
                show_ranks(df_data[df_data['Category']=='Shorts'], views_col, "Shorts by Views")

        with t3:
            st.markdown("### 📄 Strategic Audit Document")
            st.info("This PDF converts your entire content library into a structured list that AI can analyze for ROI.")
            try:
                pdf_bytes = create_analysis_pdf(df_2026, v_m, s_m, l_m)
                st.download_button(
                    label="📥 Download Strategic Audit PDF",
                    data=pdf_bytes,
                    file_name="YouTube_Strategic_Audit.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"PDF Generation Error: {e}")

        with t4:
            st.markdown("### 🤖 Senior Strategy Roadmap")
            
            v_roi = v_m['Subscribers'] / v_m['Published'] if v_m['Published'] > 0 else 0
            s_roi = s_m['Subscribers'] / s_m['Published'] if s_m['Published'] > 0 else 0

            prompt = f"""
            SYSTEM ROLE: Senior YouTube Strategy Consultant.
            OBJECTIVE: Analyze 2026 performance to 'trim the fat' and identify high-ROI growth drivers.
            
            EFFICIENCY METRICS (Subs per post):
            - Long-form Videos: {v_roi:.2f}
            - Shorts: {s_roi:.2f}
            
            CHANNEL TOTALS:
            - Videos: {v_m['Published']} posts, {v_m['Views']:,} views, {v_m['Subscribers']} subs.
            - Shorts: {s_m['Published']} posts, {s_m['Views']:,} views, {s_m['Subscribers']} subs.
            
            TASK:
            1. STOP: Identify specific content formats or topics with the lowest ROI.
            2. CONTINUE: Identify the 'Growth Muscle' (high sub conversion).
            3. GREY AREA: Identify content that is neutral (retention only, no acquisition).
            4. ACTION PLAN: 3 concrete steps to increase efficiency.
            
            *Instruction: Analyze the individual video list provided in the PDF for patterns. Skip all themed lingo. Provide objective reasoning only.*
            """
            
            st.info("💡 **Instructions:** Upload the PDF from the previous tab to Gemini and paste this prompt:")
            st.code(prompt, language="markdown")
            
            if HAS_GENAI and api_key:
                if st.button("Generate Executive AI Summary"):
                    with st.spinner("Analyzing..."):
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        st.markdown(model.generate_content(prompt).text)
