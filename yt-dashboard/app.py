import streamlit as st
import pandas as pd

# --- 1. SETUP & UI ---
st.set_page_config(page_title="YouTube Quick Metrics", layout="wide")
st.title("📊 YouTube Performance Summary")
st.subheader("Splitting content by duration (Shorts < 60s)")

# --- 2. HELPERS: ROBUST DATA LOADING ---
def load_yt_csv(file):
    raw_bytes = file.getvalue()
    try:
        content = raw_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        content = raw_bytes.decode("utf-16").splitlines()
    
    header_idx = 0
    for i, line in enumerate(content):
        if "Views" in line or "Video title" in line or "Subscribers" in line:
            header_idx = i
            break
            
    file.seek(0)
    df = pd.read_csv(file, skiprows=header_idx, sep=None, engine='python')
    df.columns = df.columns.str.strip().str.replace('"', '')
    return df

def find_column(df, possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None

# --- 3. FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload Table Data.csv", type="csv")

if uploaded_file:
    df = load_yt_csv(uploaded_file)
    
    # Map required columns
    views_col = find_column(df, ['Views', 'views'])
    subs_col = find_column(df, ['Subscribers', 'subscribers', 'Subscribers gained'])
    watch_col = find_column(df, ['Watch time (hours)', 'Watch time'])
    imp_col = find_column(df, ['Impressions', 'impressions'])
    dur_col = find_column(df, ['Duration', 'Video duration']) # Actual length of the video

    if views_col and subs_col and dur_col:
        # --- 4. DATA PROCESSING ---
        # Ensure numbers are treated as numbers
        def to_num(series):
            return pd.to_numeric(series, errors='coerce').fillna(0)

        # Split logic: Under 60 seconds = Short Form
        # Note: If duration is in HH:MM:SS format, this will need a string parser.
        # Assuming numeric seconds based on previous data samples.
        df[dur_col] = to_num(df[dur_col])
        is_shorts = df[dur_col] < 60
        
        shorts_df = df[is_shorts]
        long_df = df[~is_shorts]

        # Metric Calculations
        long_views = to_num(long_df[views_col]).sum()
        short_views = to_num(shorts_df[views_col]).sum()
        long_subs = to_num(long_df[subs_col]).sum()
        short_subs = to_num(shorts_df[subs_col]).sum()
        
        total_views = long_views + short_views
        total_subs = long_subs + short_subs
        
        sub_view_ratio = (total_subs / total_views * 100) if total_views > 0 else 0
        watch_hours = to_num(long_df[watch_col]).sum()
        total_impressions = to_num(df[imp_col]).sum()

        # --- 5. REPORTING ---
        st.markdown("---")
        
        # High Level Overview
        col_top1, col_top2, col_top3 = st.columns(3)
        col_top1.metric("Total Videos Posted", f"{len(df):,}")
        col_top2.metric("Overall Sub-to-View Ratio", f"{sub_view_ratio:.2f}%")
        col_top3.metric("Total Impressions", f"{total_impressions:,.0f}")

        st.markdown("### 🎬 Performance by Format")
        
        col_l, col_s = st.columns(2)
        
        with col_l:
            st.info("**Long Form Content (60s+)**")
            st.metric("Views", f"{long_views:,.0f}")
            st.metric("Subscribers Gained", f"{long_subs:,.0f}")
            st.metric("Watch Hours", f"{watch_hours:,.1f}")

        with col_s:
            st.warning("**Short Form Content (< 60s)**")
            st.metric("Views", f"{short_views:,.0f}")
            st.metric("Subscribers Gained", f"{short_subs:,.0f}")
            st.caption("Includes all content under 60 seconds duration.")

    else:
        st.error("Missing columns. Ensure your 'Table Data' export includes: Views, Subscribers, and Duration.")
