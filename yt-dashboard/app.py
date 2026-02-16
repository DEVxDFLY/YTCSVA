import streamlit as st
import pandas as pd

# --- SAFE DEPENDENCY CHECK ---
try:
    import google.generativeapi as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

st.set_page_config(page_title="YouTube Strategy Dashboard", layout="wide")
st.title("📊 YouTube Growth Strategy")
st.subheader("Data-Driven Content Analysis & Strategic Planning")

# --- CONFIG & HELPERS ---
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

# --- SIDEBAR ---
with st.sidebar:
    st.header("AI Strategy Config")
    if HAS_GENAI:
        api_key = st.text_input("Enter Gemini API Key", type="password")
        if api_key: genai.configure(api_key=api_key)
    else:
        st.warning("Manual Mode: Copy the data package in Tab 4.")

# --- FILE UPLOAD & PROCESSING ---
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

        tabs = st.tabs(["Summary", "Videos", "Shorts", "🤖 AI Game Plan"])

        # DATA AGGREGATION FOR AI
        def get_stats(df_src, cat):
            group = df_src[df_src['Category'] == cat]
            pubs = len(group)
            subs = group[subs_col].sum()
            views = group[views_col].sum()
            watch = group[watch_col].sum()
            imps = group[imp_col].sum()
            ctr = (group[ctr_col] * group[imp_col]).sum() / imps if imps > 0 else 0
            # Efficiency Ratios
            sub_roi = subs / pubs if pubs > 0 else 0
            view_roi = views / pubs if pubs > 0 else 0
            return {"Pubs": pubs, "Subs": subs, "Views": views, "Watch": watch, "CTR": ctr, "Sub_ROI": sub_roi, "View_ROI": view_roi}

        v = get_stats(df_2026, 'Videos')
        s = get_stats(df_2026, 'Shorts')
        l = get_stats(df_2026, 'Live Stream')

        # AI TAB
        with tabs[3]:
            st.markdown("### 🎯 Executive Strategic Roadmap")
            
            # Construct a much more diagnostic payload
            analysis_context = f"""
            SYSTEM ROLE: Senior YouTube Strategist (Professional, Data-Driven, No Themed Lingo).
            
            CHANNEL PERFORMANCE DATA (2026):
            
            1. CONTENT EFFICIENCY (Subscribers gained per 1 video published):
            - Long-form Videos: {v['Sub_ROI']:.2f} subs/post
            - Shorts: {s['Sub_ROI']:.2f} subs/post
            - Live Streams: {l['Sub_ROI']:.2f} subs/post
            
            2. VIEW EFFICIENCY (Average views generated per 1 video published):
            - Long-form Videos: {v['View_ROI']:.1f} views/post
            - Shorts: {s['View_ROI']:.1f} views/post
            - Live Streams: {l['View_ROI']:.1f} views/post
            
            3. PACKAGING HEALTH:
            - Video CTR: {v['CTR']:.2f}%
            - Shorts CTR: {s['CTR']:.2f}%
            - Live CTR: {l['CTR']:.2f}%
            
            4. RAW TOTALS:
            - Videos: {v['Pubs']} posts, {v['Views']:,} views, {v['Subs']} subs, {v['Watch']:.1f} hrs.
            - Shorts: {s['Pubs']} posts, {s['Views']:,} views, {s['Subs']} subs.
            - Live: {l['Pubs']} posts, {l['Views']:,} views, {l['Subs']} subs, {l['Watch']:.1f} hrs.

            GOAL: Analyze this data to trim fat and maximize effort ROI.
            
            REQUIRED OUTPUT:
            - WHAT'S WORKING: Which category is your 'Growth Engine' (highest Sub ROI)?
            - WHAT TO STOP: Which category has high 'Published Count' but failing 'Sub ROI' or 'View ROI'?
            - GREY AREA: Content that generates views/watch time but zero subscribers (Retention vs Acquisition).
            - ACTION PLAN: Provide 3 concrete steps to get more results with less (or equal) effort.
            """

            if HAS_GENAI and api_key:
                if st.button("Generate Diagnostic Roadmap"):
                    with st.spinner("Calculating ROI..."):
                        try:
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            response = model.generate_content(analysis_context)
                            st.markdown(response.text)
                        except Exception as e:
                            st.error(f"AI Error: {e}")
            else:
                st.info("💡 Copy this diagnostic data package and paste it into Gemini:")
                st.code(analysis_context, language="markdown")

        # (Existing table/ranking code for Summary, Videos, and Shorts tabs goes here)
