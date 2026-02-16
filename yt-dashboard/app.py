import streamlit as st
import pandas as pd

# --- 1. SAFE DEPENDENCY CHECK ---
# This prevents the app from crashing if the library isn't found
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
    st.header("AI Strategy Config")
    if HAS_GENAI:
        api_key = st.text_input("Enter Gemini API Key", type="password")
        if api_key:
            genai.configure(api_key=api_key)
    else:
        st.warning("⚠️ AI Library missing from environment. Using manual data-package mode.")

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

        # Tabs for Navigation
        tabs = st.tabs(["Performance Summary", "Video Deep Dive", "Shorts Performance", "🤖 AI Strategy Roadmap"])

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

            comparison_data = [
                {"Metric": "Published Count", "Videos": v_m['Published'], "Shorts": s_m['Published'], "Live Streams": l_m['Published']},
                {"Metric": "Subscribers", "Videos": f"{v_m['Subscribers']:,.0f}", "Shorts": f"{s_m['Subscribers']:,.0f}", "Live Streams": f"{l_m['Subscribers']:,.0f}"},
                {"Metric": "Views", "Videos": f"{v_m['Views']:,.0f}", "Shorts": f"{s_m['Views']:,.0f}", "Live Streams": f"{l_m['Views']:,.0f}"},
                {"Metric": "Watch Time (Hrs)", "Videos": f"{v_m['Watch Time']:,.1f}", "Shorts": f"{s_m['Watch Time']:,.1f}", "Live Streams": f"{l_m['Watch Time']:,.1f}"}
            ]
            st.table(pd.DataFrame(comparison_data).set_index("Metric"))

        # Ranking Logic
        def display_rankings(df, metric_col, label, is_ctr=False):
            sorted_df = df.sort_values(by=metric_col, ascending=False)[[title_col, metric_col]].copy()
            if is_ctr: sorted_df[metric_col] = sorted_df[metric_col].map("{:.2f}%".format)
            else: sorted_df[metric_col] = sorted_df[metric_col].map("{:,.0f}".format)
            
            c1, c2 = st.columns(2)
            c1.success(f"Top 5: {label}"); c1.dataframe(sorted_df.head(5).reset_index(drop=True), use_container_width=True)
            c2.error(f"Bottom 5: {label}"); c2.dataframe(sorted_df.tail(5).iloc[::-1].reset_index(drop=True), use_container_width=True)

        with tabs[1]:
            video_df = df_data[df_data['Category'] == 'Videos'].copy()
            for label, col in {"Views": views_col, "Subscribers": subs_col, "Watch Time": watch_col}.items():
                st.write(f"#### Rank by {label}")
                display_rankings(video_df, col, label)
            st.write("#### Rank by Impressions CTR (Min 500 Views)")
            ctr_df = video_df[video_df[views_col] >= 500]
            if not ctr_df.empty: display_rankings(ctr_df, ctr_col, "CTR", is_ctr=True)

        with tabs[2]:
            shorts_df = df_data[df_data['Category'] == 'Shorts'].copy()
            for label, col in {"Views": views_col, "Subscribers": subs_col}.items():
                st.write(f"#### Rank by {label}")
                display_rankings(shorts_df, col, label)

        with tabs[3]:
            st.markdown("### 🤖 Strategy Game Plan")
            
            # 7. CONSTRUCT DATA PAYLOAD
            best_v = video_df.nlargest(3, views_col)[title_col].tolist()
            worst_v = video_df.nsmallest(3, views_col)[title_col].tolist()
            low_ctr = ctr_df.nsmallest(3, ctr_col)[title_col].tolist() if not ctr_df.empty else ["N/A"]

            analysis_context = f"""
            YouTube Analytics Breakdown (Executive Summary):
            
            1. CORE STATS:
            - Videos: {v_m['Published']} posts, {v_m['Views']:,} views, {v_m['Subscribers']} subs.
            - Shorts: {s_m['Published']} posts, {s_m['Views']:,} views, {s_m['Subscribers']} subs.
            - Live Streams: {l_m['Published']} posts, {l_m['Views']:,} views, {l_m['Subscribers']} subs.
            
            2. TOP PERFORMERS: {', '.join(best_v)}
            3. UNDERPERFORMERS: {', '.join(worst_v)}
            4. PACKAGE ALERT (Low CTR with 500+ views): {', '.join(low_ctr)}
            
            TASK: Provide a professional YouTube Consultant Roadmap.
            - STOP: What content types/topics have low ROI?
            - CONTINUE: What is driving subscribers most efficiently?
            - IMPROVE: Identify leaks in the funnel (e.g., low CTR despite high potential).
            - WHY: Back up reasoning with the data provided. Skip themed lingo.
            """

            if HAS_GENAI and api_key:
                if st.button("Generate AI Game Plan"):
                    with st.spinner("Analyzing data..."):
                        try:
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            response = model.generate_content(analysis_context)
                            st.markdown(response.text)
                        except Exception as e:
                            st.error(f"AI Error: {e}")
            else:
                st.info("💡 Copy the box below and paste it into Gemini for your Strategic Breakdown:")
                st.code(analysis_context, language="markdown")

    else:
        st.error("Missing required columns. Please ensure you are uploading the 'CONTENT' breakdown CSV.")
