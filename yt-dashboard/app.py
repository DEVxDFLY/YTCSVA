import streamlit as st
import pandas as pd
import google.generativeapi as genai

# --- 1. SETUP & API CONFIG ---
st.set_page_config(page_title="YouTube Strategy Dashboard", layout="wide")

# Securely handle API Key (Best practice: use st.secrets or an environment variable)
# For this implementation, we add a sidebar input for the key
with st.sidebar:
    st.title("Settings")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    if api_key:
        genai.configure(api_key=api_key)

st.title("📊 YouTube Growth Strategy")
st.subheader("Data-Driven Strategic Roadmap")

# --- 2. HELPERS ---
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

        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Performance Summary", "Video Deep Dive", "Shorts Performance", "Strategic AI Roadmap"])

        with tab1:
            # Summary Logic
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

            comparison_data = [
                {"Metric": "Published Count", "Videos": v_m['Published'], "Shorts": s_m['Published'], "Live Streams": l_m['Published'], "Other": "—"},
                {"Metric": "Subscribers", "Videos": f"{v_m['Subscribers']:,.0f}", "Shorts": f"{s_m['Subscribers']:,.0f}", "Live Streams": f"{l_m['Subscribers']:,.0f}", "Other": f"{other_subs:,.0f}"},
                {"Metric": "Watch Time (Hrs)", "Videos": f"{v_m['Watch Time']:,.1f}", "Shorts": f"{s_m['Watch Time']:,.1f}", "Live Streams": f"{l_m['Watch Time']:,.1f}", "Other": "—"},
                {"Metric": "Impressions", "Videos": f"{v_m['Impressions']:,.0f}", "Shorts": f"{s_m['Impressions']:,.0f}", "Live Streams": f"{l_m['Impressions']:,.0f}", "Other": "—"}
            ]
            st.table(pd.DataFrame(comparison_data).set_index("Metric"))

        # ... (Video Deep Dive and Shorts tabs remain the same as previous step) ...

        with tab4:
            st.markdown("### 🤖 Strategic AI Game Plan")
            if not api_key:
                st.warning("Please enter your Gemini API Key in the sidebar to generate the roadmap.")
            else:
                if st.button("Generate Strategic Analysis"):
                    with st.spinner("Analyzing channel data..."):
                        # Prepare context for Gemini
                        # We extract top/bottom performers to give the AI specific data points
                        top_videos = df_data[df_data['Category'] == 'Videos'].nlargest(3, views_col)[title_col].tolist()
                        low_ctr_videos = df_data[(df_data['Category'] == 'Videos') & (df_data[views_col] >= 500)].nsmallest(3, ctr_col)[title_col].tolist()
                        
                        channel_context = f"""
                        Analyze this YouTube Channel data and provide a professional game plan.
                        
                        DATA SUMMARY (2026):
                        - Long-form Videos: {v_m['Published']} published, {v_m['Views']} views, {v_m['Subscribers']} subs, {v_m['CTR']:.2f}% avg CTR.
                        - Shorts: {s_m['Published']} published, {s_m['Views']} views, {s_m['Subscribers']} subs.
                        - Live Streams: {l_m['Published']} published, {l_m['Views']} views, {l_m['Subscribers']} subs.
                        
                        TOP PERFORMERS (By Views): {', '.join(top_videos)}
                        LOWEST CTR (Min 500 views): {', '.join(low_ctr_videos)}
                        
                        REQUESTED STRUCTURE:
                        1. STOP: What content types or topics are underperforming significantly relative to effort?
                        2. CONTINUE: What is working best for subscriber conversion and retention?
                        3. IMPROVE: Which content has high potential but needs packaging (CTR) or retention (Watch Time) fixes?
                        4. WHY: Back up every claim with the numbers provided above.
                        """

                        try:
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            response = model.generate_content(channel_context)
                            st.markdown(response.text)
                        except Exception as e:
                            st.error(f"Error generating analysis: {e}")

    else:
        st.error("Missing required columns.")
