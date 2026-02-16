import streamlit as st
import pandas as pd
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

# --- 4. SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("Strategic Tools")
    if HAS_GENAI:
        api_key = st.text_input("Enter Gemini API Key", type="password")
        if api_key:
            genai.configure(api_key=api_key)
    else:
        st.warning("⚠️ AI Library missing. Using 'Manual Data Dump' mode.")

# --- 5. FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload 'Table Data.csv' (Content Breakdown)", type="csv")

if uploaded_file:
    df_raw = load_yt_csv(uploaded_file)
    
    # Identify Columns
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
            if any(k in title for k in LIVE_KEYWORDS) and duration > 300:
                return 'Live Stream'
            if '#' in title or duration <= 60:
                return 'Shorts'
            return 'Videos'

        df_data['Category'] = df_data.apply(categorize, axis=1)
        df_data['Parsed_Date'] = pd.to_datetime(df_data[date_col], errors='coerce')
        df_2026 = df_data[df_data['Parsed_Date'].dt.year == 2026].copy()

        # Download Button in Sidebar for the "Massive List"
        with st.sidebar:
            st.markdown("---")
            st.subheader("Data Export")
            export_df = df_data[[title_col, 'Category', date_col, views_col, subs_col, watch_col, imp_col, ctr_col]].copy()
            csv = export_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Full Processed List",
                data=csv,
                file_name='categorized_youtube_analytics.csv',
                mime='text/csv',
                help="Download a clean, categorized list of all videos and their metrics for advanced AI analysis."
            )

        # Tabs
        tabs = st.tabs(["Performance Summary", "Deep Dive Rankings", "🤖 AI Strategy Roadmap"])

        with tabs[0]:
            def get_cat_metrics(cat_name):
                group = df_2026[df_2026['Category'] == cat_name]
                total_imps = group[imp_col].sum()
                avg_ctr = (group[ctr_col] * group[imp_col]).sum() / total_imps if total_imps > 0 else 0
                return {
                    "Published": len(group),
                    "Subscribers": group[subs_col].sum(),
                    "Watch Time": group[watch_col].sum(),
                    "Impressions": total_imps,
                    "CTR": avg_ctr,
                    "Views": group[views_col].sum()
                }

            v_m = get_cat_metrics('Videos')
            s_m = get_cat_metrics('Shorts')
            l_m = get_cat_metrics('Live Stream')

            chan_subs = total_row[subs_col] if total_row is not None else (v_m['Subscribers'] + s_m['Subscribers'] + l_m['Subscribers'])
            other_subs = chan_subs - (v_m['Subscribers'] + s_m['Subscribers'] + l_m['Subscribers'])

            st.markdown("---")
            h1, h2, h3 = st.columns(3)
            h1.metric("Total Published (2026)", f"{v_m['Published'] + s_m['Published'] + l_m['Published']}")
            h2.metric("Total Subs Gained", f"{chan_subs:,.0f}")
            h3.metric("Other Subscribers", f"{max(0, other_subs):,.0f}")

            summary_df = pd.DataFrame([
                {"Metric": "Published Count", "Videos": v_m['Published'], "Shorts": s_m['Published'], "Live Streams": l_m['Published']},
                {"Metric": "Subscribers", "Videos": f"{v_m['Subscribers']:,.0f}", "Shorts": f"{s_m['Subscribers']:,.0f}", "Live Streams": f"{l_m['Subscribers']:,.0f}"},
                {"Metric": "Views", "Videos": f"{v_m['Views']:,.0f}", "Shorts": f"{s_m['Views']:,.0f}", "Live Streams": f"{l_m['Views']:,.0f}"},
                {"Metric": "Watch Time (Hrs)", "Videos": f"{v_m['Watch Time']:,.1f}", "Shorts": f"{s_m['Watch Time']:,.1f}", "Live Streams": f"{l_m['Watch Time']:,.1f}"}
            ]).set_index("Metric")
            st.table(summary_df)

        with tabs[1]:
            col_v, col_s = st.columns(2)
            with col_v:
                st.subheader("Long-Form Video Rankings")
                video_df = df_data[df_data['Category'] == 'Videos']
                st.write("**Top 5 by Views**")
                st.dataframe(video_df.nlargest(5, views_col)[[title_col, views_col]], use_container_width=True)
                st.write("**Top 5 by Subscribers**")
                st.dataframe(video_df.nlargest(5, subs_col)[[title_col, subs_col]], use_container_width=True)
            with col_s:
                st.subheader("Shorts Performance")
                shorts_df = df_data[df_data['Category'] == 'Shorts']
                st.write("**Top 5 by Views**")
                st.dataframe(shorts_df.nlargest(5, views_col)[[title_col, views_col]], use_container_width=True)
                st.write("**Top 5 by Subscribers**")
                st.dataframe(shorts_df.nlargest(5, subs_col)[[title_col, subs_col]], use_container_width=True)

        with tabs[2]:
            st.markdown("### 🤖 Strategic Executive Roadmap")
            
            # Construct Detailed Context
            best_v = video_df.nlargest(3, views_col)[title_col].tolist()
            worst_v = video_df.nsmallest(3, views_col)[title_col].tolist()
            
            v_roi = v_m['Subscribers'] / v_m['Published'] if v_m['Published'] > 0 else 0
            s_roi = s_m['Subscribers'] / s_m['Published'] if s_m['Published'] > 0 else 0
            l_roi = l_m['Subscribers'] / l_m['Published'] if l_m['Published'] > 0 else 0

            analysis_context = f"""
            ROLE: Senior YouTube Strategy Consultant.
            DIAGNOSTIC DATA (2026):
            
            1. EFFICIENCY (Subs per post):
            - Videos: {v_roi:.2f} | Shorts: {s_roi:.2f} | Live: {l_roi:.2f}
            
            2. TOTALS:
            - Videos: {v_m['Published']} posts, {v_m['Views']:,} views, {v_m['Subscribers']} subs.
            - Shorts: {s_m['Published']} posts, {s_m['Views']:,} views, {s_m['Subscribers']} subs.
            - Live: {l_m['Published']} posts, {l_m['Views']:,} views, {l_m['Subscribers']} subs.
            
            3. PACKAGING:
            - Video CTR: {v_m['CTR']:.2f}% (Average across all content).
            
            4. SPECIFIC PERFORMERS:
            - High Performance: {', '.join(best_v)}
            - Low Performance: {', '.join(worst_v)}

            TASK:
            I am attaching a full CSV of every video and its individual metrics. 
            Using that data plus the summaries above, provide a clinical audit:
            
            - STOP: Which content formats or topics are 'Fat' (High effort, low ROI)?
            - CONTINUE: Which specific content styles are your 'Growth Muscle'?
            - GREY AREA: Which content is neutral (keeps audience but doesn't grow)?
            - ACTION PLAN: 3 steps to increase efficiency immediately.
            
            *Important: Objective reasoning only. No themed lingo.*
            """

            st.info("💡 **Instructions for Deep Audit:**\n1. Download the **Processed List** from the sidebar.\n2. Upload that CSV to Gemini.\n3. Copy the prompt below and paste it in with the file.")
            st.code(analysis_context, language="markdown")

            if HAS_GENAI and api_key:
                if st.button("Generate Immediate Summary Plan (API)"):
                    with st.spinner("Analyzing..."):
                        try:
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            response = model.generate_content(analysis_context)
                            st.markdown(response.text)
                        except Exception as e:
                            st.error(f"AI Error: {e}")
    else:
        st.error("CSV Mapping Failed.")
