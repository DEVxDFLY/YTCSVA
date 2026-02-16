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

# UPDATED PDF GENERATOR WITH TOP/BOTTOM SUMMARY
def create_categorized_pdf(df_source, v_m, s_m, l_m, views_col, subs_col, watch_col, ctr_col):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="YouTube Strategic Content Audit", ln=True, align='C')
    
    # Format Efficiency Summary
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Executive Efficiency Summary (2026)", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 7, txt=(
        f"Long-form: {v_m['Published']} posts | {v_m['Subscribers']} Subs | {v_m['Views']:,} Views | {v_m['CTR']:.2f}% Avg CTR\n"
        f"Shorts: {s_m['Published']} posts | {s_m['Subscribers']} Subs | {s_m['Views']:,} Views | {s_m['CTR']:.2f}% Avg CTR\n"
        f"Live Streams: {l_m['Published']} posts | {l_m['Subscribers']} Subs | {l_m['Views']:,} Views"
    ))

    # STRATEGIC RANKING OVERVIEW (Top/Bottom 5)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(200, 10, txt="Priority Audit: Top & Bottom Performers", ln=True)
    
    def add_rank_table(pdf_obj, data, title, is_top=True):
        pdf_obj.set_font("Arial", 'B', 10)
        color = (0, 128, 0) if is_top else (200, 0, 0)
        pdf_obj.set_text_color(*color)
        pdf_obj.cell(200, 8, txt=title, ln=True)
        pdf_obj.set_text_color(0, 0, 0)
        
        pdf_obj.set_font("Arial", 'B', 8)
        pdf_obj.cell(100, 7, "Title", 1)
        pdf_obj.cell(30, 7, "Views", 1)
        pdf_obj.cell(30, 7, "Subs", 1)
        pdf_obj.cell(30, 7, "CTR", 1, ln=True)
        
        pdf_obj.set_font("Arial", '', 7)
        subset = data.head(5) if is_top else data.tail(5).iloc[::-1]
        for _, row in subset.iterrows():
            title_text = str(row['Video title'])[:55].encode('latin-1', 'ignore').decode('latin-1')
            pdf_obj.cell(100, 6, title_text, 1)
            pdf_obj.cell(30, 6, f"{row[views_col]:,.0f}", 1)
            pdf_obj.cell(30, 6, f"{row[subs_col]:,.0f}", 1)
            pdf_obj.cell(30, 6, f"{row[ctr_col]:.2f}%", 1, ln=True)
        pdf_obj.ln(4)

    # Videos and Shorts rankings for the first page
    video_data = df_source[df_source['Category'] == 'Videos'].sort_values(by=views_col, ascending=False)
    shorts_data = df_source[df_source['Category'] == 'Shorts'].sort_values(by=views_col, ascending=False)
    
    if not video_data.empty:
        add_rank_table(pdf, video_data, "TOP 5 VIDEOS (Growth Muscle)", is_top=True)
        add_rank_table(pdf, video_data, "BOTTOM 5 VIDEOS (Potential Fat)", is_top=False)
    
    if not shorts_data.empty:
        add_rank_table(pdf, shorts_data, "TOP 5 SHORTS (Reach Drivers)", is_top=True)
        add_rank_table(pdf, shorts_data, "BOTTOM 5 SHORTS (Low Engagement)", is_top=False)

    # FULL GRANULAR LIST BY CATEGORY
    pdf.add_page()
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(200, 10, txt="Full Granular Content Inventory", ln=True)

    def add_full_section(pdf_obj, data, title):
        if data.empty: return
        pdf_obj.ln(5)
        pdf_obj.set_font("Arial", 'B', 11)
        pdf_obj.cell(200, 8, txt=f"Category: {title}", ln=True)
        pdf_obj.set_font("Arial", 'B', 8)
        pdf_obj.cell(90, 7, "Title", 1)
        pdf_obj.cell(25, 7, "Views", 1)
        pdf_obj.cell(20, 7, "Subs", 1)
        pdf_obj.cell(25, 7, "Watch Hrs", 1)
        pdf_obj.cell(20, 7, "CTR", 1, ln=True)
        pdf_obj.set_font("Arial", '', 7)
        for _, row in data.sort_values(by=views_col, ascending=False).iterrows():
            t = str(row['Video title'])[:50].encode('latin-1', 'ignore').decode('latin-1')
            pdf_obj.cell(90, 6, t, 1)
            pdf_obj.cell(25, 6, f"{row[views_col]:,.0f}", 1)
            pdf_obj.cell(20, 6, f"{row[subs_col]:,.0f}", 1)
            pdf_obj.cell(25, 6, f"{row[watch_col]:,.1f}", 1)
            pdf_obj.cell(20, 6, f"{row[ctr_col]:.1f}%", 1, ln=True)

    add_full_section(pdf, video_data, "Long-form Videos")
    add_full_section(pdf, shorts_data, "Shorts")
    add_full_section(pdf, df_source[df_source['Category'] == 'Live Stream'], "Live Streams")
    
    return bytes(pdf.output())

# --- 4. DATA PROCESSING ---
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

        # Stats aggregation
        def get_stats(df_src, cat):
            group = df_src[df_src['Category'] == cat]
            total_imps = group[imp_col].sum()
            avg_ctr = (group[ctr_col] * group[imp_col]).sum() / total_imps if total_imps > 0 else 0
            return {"Published": len(group), "Subscribers": group[subs_col].sum(), "Watch Time": group[watch_col].sum(), "CTR": avg_ctr, "Views": group[views_col].sum()}

        v_m = get_stats(df_2026, 'Videos'); s_m = get_stats(df_2026, 'Shorts'); l_m = get_stats(df_2026, 'Live Stream')
        chan_subs = total_row[subs_col] if total_row is not None else (v_m['Subscribers'] + s_m['Subscribers'] + l_m['Subscribers'])
        other_subs = chan_subs - (v_m['Subscribers'] + s_m['Subscribers'] + l_m['Subscribers'])

        # --- TABS ---
        t1, t2, t3, t4 = st.tabs(["Summary", "Ranking Audit", "📄 Export Audit PDF", "🤖 Strategy Roadmap"])

        with t1:
            st.markdown("### 2026 Performance Overview")
            comparison_data = [
                {"Metric": "Subscribers", "Videos": f"{v_m['Subscribers']:,.0f}", "Shorts": f"{s_m['Subscribers']:,.0f}", "Live Streams": f"{l_m['Subscribers']:,.0f}", "Other": f"{other_subs:,.0f}"},
                {"Metric": "Watch Time (Hrs)", "Videos": f"{v_m['Watch Time']:,.1f}", "Shorts": f"{s_m['Watch Time']:,.1f}", "Live Streams": f"{l_m['Watch Time']:,.1f}", "Other": "—"}
            ]
            st.table(pd.DataFrame(comparison_data).set_index("Metric"))

        with t2:
            st.markdown("### 🔍 Ranking Audit")
            # Original tables for in-app viewing
            c1, c2 = st.columns(2)
            c1.success("Top 5 Videos (Views)"); c1.table(df_2026[df_2026['Category']=='Videos'].nlargest(5, views_col)[[title_col, views_col, ctr_col]])
            c2.error("Bottom 5 Videos (Views)"); c2.table(df_2026[df_2026['Category']=='Videos'].nsmallest(5, views_col)[[title_col, views_col, ctr_col]])

        with t3:
            st.markdown("### 📄 Categorized Audit Document")
            st.info("The top and bottom 5 performers are now highlighted at the start of the PDF.")
            pdf_bytes = create_categorized_pdf(df_2026, v_m, s_m, l_m, views_col, subs_col, watch_col, ctr_col)
            st.download_button(label="📥 Download Strategic Audit PDF", data=pdf_bytes, file_name="YouTube_Audit_Categorized.pdf", mime="application/pdf")

        with t4:
            st.markdown("### 🤖 Strategy Roadmap")
            prompt = f"SYSTEM ROLE: Senior Strategy Consultant. OBJECTIVE: Audit 2026 performance. STOP: low ROI content. CONTINUE: Growth muscles. ACTION: 3 steps to efficiency. Skip themed lingo."
            st.code(prompt, language="markdown")
