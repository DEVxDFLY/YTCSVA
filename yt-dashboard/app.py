import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="YouTube Metrics Fix", layout="wide")
st.title("📊 YouTube Performance Summary")
st.subheader("Corrected Content Type Reporting")

# --- 2. HELPERS ---
def load_yt_csv(file):
    raw_bytes = file.getvalue()
    try:
        content = raw_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        content = raw_bytes.decode("utf-16").splitlines()
    
    header_idx = 0
    for i, line in enumerate(content):
        if "Views" in line or "Video title" in line or "Content type" in line:
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

def to_num(series):
    return pd.to_numeric(series.astype(str).str.replace(',', ''), errors='coerce').fillna(0)

# --- 3. FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload Table Data.csv", type="csv")

if uploaded_file:
    df = load_yt_csv(uploaded_file)
    
    # Identify Columns
    title_col = find_column(df, ['Video title', 'Title', 'Content type', 'Content'])
    type_col = find_column(df, ['Content type', 'Video type'])
    views_col = find_column(df, ['Views', 'views'])
    subs_col = find_column(df, ['Subscribers', 'Subscribers gained'])
    watch_col = find_column(df, ['Watch time (hours)', 'Watch time'])
    imp_col = find_column(df, ['Impressions'])
    dur_col = find_column(df, ['Duration', 'Video duration'])

    if views_col and subs_col:
        # --- 4. DATA CLEANING ---
        # CRITICAL: Remove the "Total" row to prevent double-counting
        if title_col:
            df = df[~df[title_col].str.contains('Total', case=False, na=False)]

        # --- 5. CATEGORIZATION ---
        # We prioritize the "Content type" column from YouTube. 
        # If missing, we fall back to the 60s duration rule.
        if type_col:
            long_df = df[df[type_col].str.contains('Video', case=False, na=False)]
            shorts_df = df[df[type_col].str.contains('Short', case=False, na=False)]
            live_df = df[df[type_col].str.contains('Live', case=False, na=False)]
        elif dur_col:
            df[dur_col] = to_num(df[dur_col])
            long_df = df[df[dur_col] >= 60]
            shorts_df = df[df[dur_col] < 60]
            live_df = pd.DataFrame()
        else:
            long_df = df
            shorts_df = pd.DataFrame()
            live_df = pd.DataFrame()

        # --- 6. METRICS CALCULATION ---
        l_views = to_num(long_df[views_col]).sum()
        s_views = to_num(shorts_df[views_col]).sum()
        live_views = to_num(live_df[views_col]).sum() if not live_df.empty else 0
        
        l_subs = to_num(long_df[subs_col]).sum()
        s_subs = to_num(shorts_df[subs_col]).sum()
        live_subs = to_num(live_df[subs_col]).sum() if not live_df.empty else 0
        
        watch_hours = to_num(long_df[watch_col]).sum() + (to_num(live_df[watch_col]).sum() if not live_df.empty else 0)
        total_impressions = to_num(long_df[imp_col]).sum() + (to_num(live_df[imp_col]).sum() if not live_df.empty else 0)
        
        total_all_views = l_views + s_views + live_views
        total_all_subs = l_subs + s_subs + live_subs
        sub_ratio = (total_all_subs / total_all_views * 100) if total_all_views > 0 else 0

        # --- 7. DISPLAY ---
        st.markdown("---")
        
        # Overview Row
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Videos Posted", f"{len(df):,}")
        c2.metric("Sub-to-View Ratio", f"{sub_ratio:.2f}%")
        c3.metric("Total Impressions", f"{total_impressions:,.0f}")

        # Production Split
        col_long, col_short = st.columns(2)
        
        with col_long:
            st.info("**Long Form Content (Videos & Live)**")
            st.metric("Views", f"{l_views + live_views:,.0f}")
            st.metric("Subscribers", f"{l_subs + live_subs:,.0f}")
            st.metric("Watch Hours", f"{watch_hours:,.1f}")

        with col_short:
            st.warning("**Short Form Content**")
            st.metric("Views", f"{s_views:,.0f}")
            st.metric("Subscribers", f"{s_subs:,.0f}")
            st.caption("Shorts views are correctly excluded from Watch Hours.")

    else:
        st.error("Essential columns missing. Check your 'Table Data' export.")
