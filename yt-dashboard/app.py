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

# ENHANCED PDF GENERATOR: Includes Strategic Ranking Summary
def create_categorized_pdf(df_source, v_m, s_m, l_m, v_col, s_col, c_col):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="YouTube Strategic Content Audit", ln=True, align='C')
    
    # Format Efficiency Summary
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Format Efficiency Summary (2026)", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 7, txt=(
        f"Long-form: {v_m['Published']} posts | {v_m['Subscribers']} Subs | {v_m['Views']:,} Views | {v_m['CTR']:.2f}% Avg CTR\n"
        f"Shorts: {s_m['Published']} posts | {s_m['Subscribers']} Subs | {s_m['Views']:,} Views | {s_m['CTR']:.2f}% Avg CTR\n"
        f"Live Streams: {l_m['Published']} posts | {l_m['Subscribers']} Subs | {l_m['Views']:,} Views"
    ))

    # STRATEGIC RANKING OVERVIEW (Top/Bottom 5)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(200, 10, txt="Strategic Audit: High/Low Performers", ln=True)
    
    def add_rank_table(pdf_obj, data, title, is_top=True):
        if data.empty: return
        pdf_obj.set_font("Arial", 'B', 10)
        color = (0, 100, 0) if is_top else (150, 0, 0)
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
            t = str(row['Video title'])[:55].encode('latin-1', 'ignore').decode('latin-1')
            pdf_obj.cell(100, 6, t, 1)
            pdf_obj.cell(30, 6, f"{row[v_col]:,.0f}", 1)
            pdf_obj.cell(30, 6, f"{row[s_col]:,.0f}", 1)
            pdf_obj.cell(30, 6, f"{row[c_col]:.2f}%", 1, ln=True)
        pdf_obj.ln(4)

    v_data = df_source[df_source['Category'] == 'Videos'].sort_values(by=v_col, ascending=False)
    s_data = df_source[df_source['Category'] == 'Shorts'].sort_values(by=v_col, ascending=False)
    
    add_rank_table(pdf, v_data, "TOP 5 VIDEOS (Growth Muscle)", is_top=True)
    add_rank_table(pdf, v_data, "BOTTOM 5 VIDEOS (Potential Fat)", is_top=False)
    add_rank_table(pdf, s_data, "TOP 5 SHORTS (Reach Drivers)", is_top=True)
    add_rank_table(pdf, s_data, "BOTTOM 5 SHORTS (Low Engagement)", is_top=False)

    # FULL GRANULAR LIST
    pdf.add_page()
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(200, 10, txt="Full Content Inventory", ln=True)

    def add_category_section(pdf_obj, data, title):
        if data.empty: return
        pdf_obj.ln(5)
        pdf_obj.set_font("Arial", 'B', 11)
        pdf_obj.cell(200, 10, txt=f"Category: {title}", ln=True)
        pdf_obj.set_font("Arial", 'B', 9)
        pdf_obj.cell(85, 8, "Title", 1)
        pdf_obj.cell(25, 8, "Views", 1)
        pdf_obj.cell(20, 8, "Subs", 1)
        pdf_obj.cell(25, 8, "Watch Hrs", 1)
        pdf_obj.cell(20, 8, "CTR", 1, ln=True)
        pdf_obj.set_font("Arial", '', 8)
        for _, row in data.sort_values(by=v_col, ascending=False).iterrows():
            clean_title = str(row['Video title'])[:45].encode('latin-1', 'ignore').decode('latin-1')
            pdf_obj.cell(85, 7, clean_title, 1)
            pdf_obj.cell(25, 7, f"{row[v_col]:,.0f}", 1)
            pdf_obj.cell(20, 7, f"{row[s_col]:,.0f}", 1)
            pdf_obj.cell(25, 7, f"{row['Watch time (hours)']:,.1f}", 1)
            pdf_obj.cell(20, 7, f"{row[c_col]:.1f}%", 1, ln=True)

    add_category_section(pdf, v_data, "Long-form Videos")
    add_category_section(pdf, s_data, "Shorts")
    add_category_section(pdf, df_source[df_source['Category'] == 'Live Stream'], "Live Streams")
    
    return bytes(pdf.output())

# --- 4. FILE UPLOAD & PROCESSING ---
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
            def display_rankings(df, metric_col, label):
                sorted_df = df.sort_values(by=metric_col, ascending=False)[[title_col, metric_col, watch_col, ctr_col]].copy()
                sorted_df[ctr_col] = sorted_df[ctr_col].map("{:.2f}%".format)
                sorted_df[metric_col] = sorted_df[metric_col].map("{:,.0f}".format)
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
            st.info("The PDF now includes a Top/Bottom 5 priority summary on page 1.")
            pdf_bytes = create_categorized_pdf(df_2026, v_m, s_m, l_m, views_col, subs_col, ctr_col)
            st.download_button(label="📥 Download Strategic Audit PDF", data=pdf_bytes, file_name="YouTube_Strategic_Audit.pdf", mime="application/pdf")

        with tabs[3]:
            st.markdown("### 🤖 Strategy Game Plan")
            
            # ROI Stats for the Prompt
            v_roi = v_m['Subscribers'] / v_m['Published'] if v_m['Published'] > 0 else 0
            s_roi = s_m['Subscribers'] / s_m['Published'] if s_m['Published'] > 0 else 0
            
            consultant_prompt = f"""
            SYSTEM ROLE: Senior YouTube Strategy Consultant.
            OBJECTIVE: Perform a clinical audit of 2026 channel performance to maximize growth efficiency and advise on what to stop doing immediately in order to maximize ROI.
            
            DIAGNOSTIC DATA:
            - Long-form Efficiency: {v_roi:.2f} subscribers per post
            - Shorts Efficiency: {s_roi:.2f} subscribers per post
            
            REQUIRED ANALYSIS (Referencing the uploaded PDF):
            1. STOP: Identify specific content themes, formats, or categories that represent low ROI relative to production effort.
            2. CONTINUE: Identify the Growth — the styles that drive subscribers most effectively.
            3. GREY AREA: Identify stagnant content that provides views but fails to convert new audience members.
            4. ACTION PLAN: Provide 3-5 concrete, data-backed steps to increase subscriber acquisition while reducing wasted effort. You do not have to identify one for shorts, videos, and live events individually. You can speak to how one aspect is working but another is failing in the same content type.
            5. FOLLOW-UP: Based on the granular list in the PDF, which specific recurring keywords or topics in the titles are present in the best performing videos (CTR, Subs, Views) but missing from the lowest performing? Advise on which topics to continue, if they're TV shows or movies, understand that those are only relevant in the moment, they are not evergreen content. If the channel has evergreen content that's doing well, point it out and educate them on why it's succeeding. If the channel does not have any evergreen content, let them know the gap and suggest 3 potential evergreen options they could try based on their video titles (making content related to their niche will be easiest and the most passionate). 
            
            *Important: Maintain a professional, executive tone. Skip all themed lingo or metaphors. Provide objective, quantitative reasoning only.*
            """
            
            st.info("💡 **Next Step:** Upload the Categorized Audit PDF to Gemini and paste the prompt below for a professional breakdown.")
            st.code(consultant_prompt, language="markdown")
