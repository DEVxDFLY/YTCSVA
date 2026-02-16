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
def create_categorized_pdf(df_source, v_m, s_m, l_m):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="YouTube Strategic Content Audit", ln=True, align='C')
    
    # Executive Summary Section
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Format Efficiency Summary (2026)", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 7, txt=(
        f"Long-form: {v_m['Published']} posts | {v_m['Subscribers']} Subs | {v_m['Views']:,} Views | {v_m['CTR']:.2f}% Avg CTR\n"
        f"Shorts: {s_m['Published']} posts | {s_m['Subscribers']} Subs | {s_m['Views']:,} Views | {s_m['CTR']:.2f}% Avg CTR\n"
        f"Live Streams: {l_m['Published']} posts | {l_m['Subscribers']} Subs | {l_m['Views']:,} Views"
    ))

    def add_category_section(pdf_obj, data, title):
        if data.empty: return
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

    add_category_section(pdf, df_source[df_source['Category'] == 'Videos'], "Long-form Videos")
    add_category_section(pdf, df_source[df_source['Category'] == 'Shorts'], "Shorts")
    add_category_section(pdf, df_source[df_source['Category'] == 'Live Stream'], "Live Streams")
    
    return bytes(pdf.output())

# --- 4. SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("AI Strategy Config")
    if HAS_GENAI:
        api_key = st.text_input("Enter Gemini API Key", type="password")
        if api_key: genai.configure(api_key=api_key)
    else:
        st.warning("⚠️ AI Library missing. Using manual 'Copy-Paste' mode.")

# --- 5. FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload 'Table Data.csv' (Content Breakdown)", type="csv")

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
        # 6. DATA PROCESSING
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

        # Tabs
        tabs = st.tabs(["Performance Summary", "Audit Rankings", "📄 Export Audit PDF", "🤖 Strategic Roadmap"])

        with tabs[0]:
            def get_cat_metrics(cat_name):
                group = df_2026[df_2026['Category'] == cat_name]
                total_imps = group[imp_col].sum()
                avg_ctr = (group[ctr_col] * group[imp_col]).sum() / total_imps if total_imps > 0 else 0
                return {"Published": len(group), "Subscribers": group[subs_col].sum(), "Watch Time": group[watch_col].sum(), "CTR": avg_ctr, "Views": group[views_col].sum()}

            v_m = get_cat_metrics('Videos'); s_m = get_cat_metrics('Shorts'); l_m = get_cat_metrics('Live Stream')
            chan_subs = total_row[subs_col] if total_row is not None else (v_m['Subscribers'] + s_m['Subscribers'] + l_m['Subscribers'])
            other_subs = chan_subs - (v_m['Subscribers'] + s_m['Subscribers'] + l_m['Subscribers'])

            st.markdown("---")
            h1, h2, h3 = st.columns(3)
            h1.metric("Total Published (2026)", f"{v_m['Published'] + s_m['Published'] + l_m['Published']}")
            h2.metric("Total Subs Gained", f"{chan_subs:,.0f}")
            h3.metric("Other Subscribers", f"{max(0, other_subs):,.0f}")

            comparison_data = [
                {"Metric": "Published Count", "Videos": v_m['Published'], "Shorts": s_m['Published'], "Live Streams": l_m['Published']},
                {"Metric": "Subscribers", "Videos": f"{v_m['Subscribers']:,.0f}", "Shorts": f"{s_m['Subscribers']:,.0f}", "Live Streams": f"{l_m['Subscribers']:,.0f}"},
                {"Metric": "Views", "Videos": f"{v_m['Views']:,.0f}", "Shorts": f"{s_m['Views']:,.0f}", "Live Streams": f"{l_m['Views']:,.0f}"},
                {"Metric": "Watch Time (Hrs)", "Videos": f"{v_m['Watch Time']:,.1f}", "Shorts": f"{s_m['Watch Time']:,.1f}", "Live Streams": f"{l_m['Watch Time']:,.1f}"}
            ]
            st.table(pd.DataFrame(comparison_data).set_index("Metric"))

        with tabs[1]:
            def display_rankings(df, metric_col, label, is_ctr=False):
                sorted_df = df.sort_values(by=metric_col, ascending=False)[[title_col, metric_col, watch_col, ctr_col]].copy()
                sorted_df[ctr_col] = sorted_df[ctr_col].map("{:.2f}%".format)
                if not is_ctr: sorted_df[metric_col] = sorted_df[metric_col].map("{:,.0f}".format)
                c1, c2 = st.columns(2)
                c1.success(f"Top 5: {label}"); c1.table(sorted_df.head(5).reset_index(drop=True))
                c2.error(f"Bottom 5: {label}"); c2.table(sorted_df.tail(5).iloc[::-1].reset_index(drop=True))

            st.write("#### Long-Form Video Rankings")
            video_df = df_data[df_data['Category'] == 'Videos'].copy()
            display_rankings(video_df, views_col, "Videos by Views")
            
            st.write("#### Shorts Performance Rankings")
            shorts_df = df_data[df_data['Category'] == 'Shorts'].copy()
            display_rankings(shorts_df, views_col, "Shorts by Views")

        with tabs[2]:
            st.markdown("### 📄 Categorized Audit Export")
            st.info("Download a clinical, categorized list of all content for deep AI analysis.")
            pdf_bytes = create_categorized_pdf(df_2026, v_m, s_m, l_m)
            st.download_button(label="📥 Download Strategic Audit PDF", data=pdf_bytes, file_name="YouTube_Strategic_Audit.pdf", mime="application/pdf")

        with tabs[3]:
            st.markdown("### 🤖 Strategy Game Plan")
            best_v = video_df.nlargest(3, views_col)[title_col].tolist()
            v_roi = v_m['Subscribers'] / v_m['Published'] if v_m['Published'] > 0 else 0
            s_roi = s_m['Subscribers'] / s_m['Published'] if s_m['Published'] > 0 else 0

            analysis_context = f"""
            SYSTEM ROLE: Senior Strategy Consultant.
            DIAGNOSTIC DATA (2026):
            - Long-form Efficiency: {v_roi:.2f} subs/post | Shorts Efficiency: {s_roi:.2f} subs/post
            - Best Performers: {', '.join(best_v)}
            
            TASK: Using the full Categorized Audit PDF, identify specific fat to trim.
            - STOP: Content with low ROI relative to effort.
            - CONTINUE: Growth muscles.
            - GREY AREA: Neutral retention content.
            Objective reasoning only. No themed lingo.
            """
            st.info("Upload the PDF to Gemini and use this prompt:")
            st.code(analysis_context, language="markdown")

    else: st.error("CSV Mapping Failed.")
