import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="YouTube Metrics Fix", layout="wide")
st.title("📊 YouTube Performance Summary")
st.subheader("Final Pathing: Hash & Keyword Categorization")

# --- 2. HELPERS ---
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

def to_num(series):
    return pd.to_numeric(series.astype(str).str.replace(',', ''), errors='coerce').fillna(0)

# --- 3. FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload Table Data.csv", type="csv")

if uploaded_file:
    df_raw = load_yt_csv(uploaded_file)
    
    # Identify Columns
    title_col = find_column(df_raw, ['Video title', 'Title', 'Content'])
    views_col = find_column(df_raw, ['Views', 'views'])
    subs_col = find_column(df_raw, ['Subscribers gained', 'Subscribers'])
    watch_col = find_column(df_raw, ['Watch time (hours)', 'Watch time'])
    imp_col = find_column(df_raw, ['Impressions'])
    ctr_col = find_column(df_raw, ['Impressions click-through rate (%)', 'CTR'])
    publish_col = find_column(df_raw, ['Video publish time', 'Published'])

    if views_col and subs_col:
        # --- 4. DATA SPLITTING ---
        # Get the Total row for the 'Other' subscriber calculation
        total_row = df_raw[df_raw['Content'] == 'Total']
        # Remove Total row for individual calculations
        df = df_raw[df_raw['Content'] != 'Total'].copy()

        # --- 5. CATEGORIZATION LOGIC (The Pathing) ---
        def categorize(row):
            title = str(row[title_col]).lower()
            if '#' in title:
                return 'Shorts'
            if any(k in title for k in ['live!', 'watchalong', 'stream', 'let\'s play', 'd&d', 'diablo']):
                return 'Live Stream'
            return 'Videos'

        df['Category'] = df.apply(categorize, axis=1)

        # Filter for 2026 for the "Published" counts
        df_2026 = df[df[publish_col].astype(str).str.contains('2026', na=False)]

        # --- 6. METRICS CALCULATION ---
        def get_group_stats(category_name):
            group = df[df['Category'] == category_name]
            pub_count = len(df_2026[df_2026['Category'] == category_name])
            return {
                "views": to_num(group[views_col]).sum(),
                "watch": to_num(group[watch_col]).sum(),
                "subs": to_num(group[subs_col]).sum(),
                "imps": to_num(group[imp_col]).sum(),
                "ctr": to_num(group[ctr_col]).mean(), # Average CTR for the group
                "published": pub_count
            }

        s = get_group_stats('Shorts')
        v = get_group_stats('Videos')
        l = get_group_stats('Live Stream')

        # Calculate "Other" subscribers
        total_channel_subs = to_num(total_row[subs_col]).sum()
        attributed_subs = df[subs_col].sum()
        other_subs = total_channel_subs - attributed_subs

        # Global Sub-to-View Ratio
        total_v = s['views'] + v['views'] + l['views']
        sub_ratio = (total_channel_subs / total_v * 100) if total_v > 0 else 0

        # --- 7. DISPLAY ---
        st.markdown("---")
        
        # Top Row Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Overall Sub-to-View Ratio", f"{sub_ratio:.2f}%")
        c2.metric("Total Impressions", f"{to_num(total_row[imp_col]).sum():,.0f}")
        c3.metric("Other Subscribers", f"{other_subs:,.0f}")
        c4.metric("Total Sub-Gain", f"{total_channel_subs:,.0f}")

        # Detail Columns
        col_v, col_s, col_l = st.columns(3)

        with col_v:
            st.info("**Videos**")
            st.write(f"Published: **{v['published']}**")
            st.metric("Views", f"{v['views']:,.0f}")
            st.metric("Watch Hours", f"{v['watch']:,.1f}")
            st.metric("Subs Gained", f"{v['subs']:,.0f}")
            st.metric("CTR", f"{v['ctr']:.1f}%")

        with col_s:
            st.warning("**Shorts**")
            st.write(f"Published: **{s['published']}**")
            st.metric("Views", f"{s['views']:,.0f}")
            st.metric("Watch Hours", f"{s['watch']:,.1f}")
            st.metric("Subs Gained", f"{s['subs']:,.0f}")
            st.metric("CTR", f"{s['ctr']:.1f}%")

        with col_l:
            st.error("**Live Streams**")
            st.write(f"Published: **{l['published']}**")
            st.metric("Views", f"{l['views']:,.0f}")
            st.metric("Watch Hours", f"{l['watch']:,.1f}")
            st.metric("Subs Gained", f"{l['subs']:,.0f}")
            st.metric("CTR", f"{l['ctr']:.1f}%")

    else:
        st.error("Column mapping failed. Please check your CSV headers.")
