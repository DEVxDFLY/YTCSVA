import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="YouTube Growth Basics", layout="wide")
st.title("📊 YouTube Performance Basics")
st.subheader("Accurate separation of Shorts, Videos, and Live Streams")

# --- 2. HELPERS (ROBUST) ---
def load_yt_csv(file):
    raw_bytes = file.getvalue()
    try:
        content = raw_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        content = raw_bytes.decode("utf-16").splitlines()
    
    header_idx = 0
    for i, line in enumerate(content):
        if any(term in line for term in ["Views", "Video title", "Subscribers", "Impressions"]):
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
    return pd.to_numeric(series.astype(str).str.replace(',', ''), errors='coerce').fillna(0)

# --- 3. FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload Table Data.csv", type="csv")

if uploaded_file:
    df_raw = load_yt_csv(uploaded_file)
    
    # Identify Columns
    title_col = find_column(df_raw, ['Video title', 'Title', 'Content'])
    views_col = find_column(df_raw, ['Views'])
    subs_col = find_column(df_raw, ['Subscribers gained', 'Subscribers'])
    watch_col = find_column(df_raw, ['Watch time (hours)', 'Watch time'])
    imp_col = find_column(df_raw, ['Impressions'])
    publish_col = find_column(df_raw, ['Video publish time', 'Published'])

    if views_col and subs_col:
        # 4. ROBUST TOTAL DETECTION (Prevents KeyError)
        # Search every row to find the one that contains "Total"
        total_mask = df_raw.astype(str).apply(lambda x: x.str.contains('Total', case=False)).any(axis=1)
        total_row = df_raw[total_mask].iloc[[0]] if total_mask.any() else None
        
        # Individual videos (Everything NOT in the total row)
        df = df_raw[~total_mask].copy()

        # 5. CATEGORIZATION LOGIC (The Pathing)
        def categorize(row):
            title = str(row[title_col]).lower() if title_col else ""
            if '#' in title:
                return 'Shorts'
            # Keywords that define your Live Streams
            if any(k in title for k in ['live!', 'watchalong', 'stream', 'let\'s play', 'd&d', 'diablo', 'ready player nerd']):
                return 'Live Stream'
            return 'Videos'

        df['Category'] = df.apply(categorize, axis=1)

        # 6. CALCULATIONS
        def get_stats(cat):
            group = df[df['Category'] == cat]
            return {
                "views": to_num(group[views_col]).sum(),
                "subs": to_num(group[subs_col]).sum(),
                "watch": to_num(group[watch_col]).sum(),
                "imps": to_num(group[imp_col]).sum(),
                "count": len(group)
            }

        shorts = get_stats('Shorts')
        videos = get_stats('Videos')
        lives = get_stats('Live Stream')

        # Global Metrics
        total_channel_subs = to_num(total_row[subs_col]).sum() if total_row is not None else df[subs_col].sum()
        total_channel_views = to_num(total_row[views_col]).sum() if total_row is not None else df[views_col].sum()
        sub_view_ratio = (total_channel_subs / total_channel_views * 100) if total_channel_views > 0 else 0
        
        # Other Subs (Channel-level, not video-level)
        other_subs = total_channel_subs - (shorts['subs'] + videos['subs'] + lives['subs'])

        # 7. DISPLAY
        st.markdown("---")
        
        # Header Stats
        h1, h2, h3 = st.columns(3)
        h1.metric("Total Videos Posted", f"{len(df):,}")
        h2.metric("Sub-to-View Ratio", f"{sub_view_ratio:.2f}%")
        h3.metric("Other Subscribers", f"{other_subs:,.0f}")

        # Three-Way Split
        col_v, col_s, col_l = st.columns(3)

        with col_v:
            st.info("**Edited Videos**")
            st.metric("Views", f"{videos['views']:,.0f}")
            st.metric("Subscribers", f"{videos['subs']:,.0f}")
            st.metric("Watch Hours", f"{videos['watch']:,.1f}")
            st.metric("Impressions", f"{videos['imps']:,.0f}")

        with col_s:
            st.warning("**Shorts**")
            st.metric("Views", f"{shorts['views']:,.0f}")
            st.metric("Subscribers", f"{shorts['subs']:,.0f}")
            st.caption(f"Watch Hours ({shorts['watch']:.1f}) are excluded from totals.")
            st.metric("Impressions", f"{shorts['imps']:,.0f}")

        with col_l:
            st.error("**Live Streams**")
            st.metric("Views", f"{lives['views']:,.0f}")
            st.metric("Subscribers", f"{lives['subs']:,.0f}")
            st.metric("Watch Hours", f"{lives['watch']:,.1f}")
            st.metric("Impressions", f"{lives['imps']:,.0f}")

    else:
        st.error("Missing essential columns. Please ensure your 'Table Data' export includes Views and Subscribers.")
