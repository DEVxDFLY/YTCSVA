import streamlit as st
import pandas as pd
try:
    import google.generativeapi as genai
except ImportError:
    st.error("Missing dependency: Please add 'google-generativeai' to your requirements.txt file.")

# --- 1. SETUP & API CONFIG ---
st.set_page_config(page_title="YouTube Strategy Dashboard", layout="wide")

with st.sidebar:
    st.title("Strategic Settings")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    if api_key:
        genai.configure(api_key=api_key)
    st.info("The AI Roadmap uses Gemini 1.5 Flash to analyze your specific metrics and provide actionable growth steps.")

st.title("📊 YouTube Growth Strategy")
st.subheader("Data-Driven Content Analysis & Strategic Planning")

# --- 2. CONFIG & HELPERS ---
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

# --- 3. FILE UPLOAD ---
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
        # 4. DATA PROCESSING
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

        # Tabs for Navigation
        tab1, tab2, tab3, tab4 = st.tabs(["Performance Summary", "Video Deep Dive", "Shorts Performance", "Strategic AI Roadmap"])

        with tab1:
            # Metric Aggregation
            def get_cat_metrics(df_src, cat_name):
                group = df_src[df_src['Category'] == cat_name]
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

            v_m = get_cat_metrics(df_2026, 'Videos')
            s_m = get_cat_metrics(df_2026, 'Shorts')
            l_m = get_cat_metrics(df_2026, 'Live Stream')

            total_subs = total_row[subs_col] if total_row is not None else (v_m['Subscribers'] + s_m['Subscribers'] + l_m['Subscribers'])
            other_subs = total_subs - (v_m['Subscribers'] + s_m['Subscribers'] + l_m['Subscribers'])

            st.markdown("---")
            h1, h2, h3 = st.columns(3)
            h1.metric("Total Published (2026)", f"{v_m['Published'] + s_m['Published'] + l_m['Published']}")
            h2.metric("Total Subs Gained", f"{total_subs:,.0f}")
            h3.metric("Other Subscribers", f"{other_subs:,.0f}")

            summary_df = pd.DataFrame([
                {"Metric": "Published Count", "Videos": v_m['Published'], "Shorts": s_m['Published'], "Live Streams": l_m['Published']},
                {"Metric": "Subscribers", "Videos": f"{v_m['Subscribers']:,.0f}", "Shorts": f"{s_m['Subscribers']:,.0f}", "Live Streams": f"{l_m['Subscribers']:,.0f}"},
                {"Metric": "Views", "Videos": f"{v_m['Views']:,.0f}", "Shorts": f"{s_m['Views']:,.0f}", "Live Streams": f"{l_m['Views']:,.0f}"},
                {"Metric": "Watch Time (Hrs)", "Videos": f"{v_m['Watch Time']:,.1f}", "Shorts": f"{s_m['Watch Time']:,.1f}", "Live Streams": f"{l_m['Watch Time']:,.1f}"},
                {"Metric": "Impressions", "Videos": f"{v_m['Impressions']:,.0f}", "Shorts": f"{s_m['Impressions']:,.0f}", "Live Streams": f"{l_m['Impressions']:,.0f}"}
            ]).set_index("Metric")
            st.table(summary_df)

        # Helper for Rankings
        def get_top_bottom(df, metric_col, n=5):
            top = df.nlargest(n, metric_col)[[title_col, metric_col]]
            bottom = df.nsmallest(n, metric_col)[[title_col, metric_col]]
            return top, bottom

        with tab2:
            st.markdown("### 🔍 Video Analysis (Long-Form)")
            video_df = df_data[df_data['Category'] == 'Videos'].copy()
            for label, col in {"Views": views_col, "Subscribers": subs_col, "Watch Time": watch_col}.items():
                st.write(f"#### Rank by {label}")
                t, b = get_top_bottom(video_df, col)
                c1, c2 = st.columns(2)
                c1.success(f"Top 5 {label}"); c1.table(t)
                c2.error(f"Bottom 5 {label}"); c2.table(b)

            st.write("#### Rank by Impressions CTR (Min 500 Views)")
            ctr_df = video_df[video_df[views_col] >= 500]
            if not ctr_df.empty:
                t, b = get_top_bottom(ctr_df, ctr_col)
                c1, c2 = st.columns(2)
                c1.success("Top 5 CTR"); c1.table(t)
                c2.error("Bottom 5 CTR"); c2.table(b)

        with tab3:
            st.markdown("### ⚡ Shorts Performance Analysis")
            shorts_df = df_data[df_data['Category'] == 'Shorts'].copy()
            for label, col in {"Views": views_col, "Subscribers": subs_col}.items():
                st.write(f"#### Rank by {label}")
                t, b = get_top_bottom(shorts_df, col)
                c1, c2 = st.columns(2)
                c1.success(f"Top 5 {label}"); c1.table(t)
                c2.error(f"Bottom 5 {label}"); c2.table(b)

        with tab4:
            st.markdown("### 🤖 Strategic AI Roadmap")
            if not api_key:
                st.warning("Please provide a Gemini API Key in the sidebar.")
            elif st.button("Generate Strategy"):
                with st.spinner("Analyzing metrics..."):
                    # Extract high-level context
                    best_v = video_df.nlargest(3, views_col)[title_col].tolist()
                    worst_ctr = ctr_df.nsmallest(3, ctr_col)[title_col].tolist()
                    best_s = shorts_df.nlargest(3, views_col)[title_col].tolist()

                    prompt = f"""
                    As a YouTube Growth Consultant, analyze this 2026 data. Skip all themed lingo; provide a professional executive summary.

                    METRICS:
                    - Videos: {v_m['Published']} posts, {v_m['Subscribers']} subs, {v_m['CTR']:.2f}% avg CTR.
                    - Shorts: {s_m['Published']} posts, {s_m['Subscribers']} subs.
                    - Live Streams: {l_m['Published']} posts, {l_m['Subscribers']} subs.

                    SPECIFIC DATA POINTS:
                    - High-Performing Titles: {', '.join(best_v)}
                    - High-Performing Shorts: {', '.join(best_s)}
                    - Low CTR Titles (500+ views): {', '.join(worst_ctr)}

                    STRUCTURE:
                    1. **STOP**: What content format or topic is yielding the lowest return on investment (ROI) in terms of subscribers or views?
                    2. **CONTINUE**: What specific content is successfully converting viewers to subscribers? 
                    3. **IMPROVE**: Where is the 'leak' in the funnel (e.g., high impressions but low CTR, or high views but low watch time)? 
                    4. **WHY**: Provide specific data-backed justifications for each point above.
                    """

                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
