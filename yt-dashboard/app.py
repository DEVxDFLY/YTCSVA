import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="YouTube Metrics Fix", layout="wide")
st.title("📊 YouTube Performance Summary")
st.subheader("Strict Content Separation (Shorts vs. Videos vs. Live)")

# --- 2. HELPERS ---
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
        # 4. REMOVE TOTAL ROW (Value-based search)
        total_mask = df_raw.astype(str).apply(lambda x: x.str.contains('Total', case=False)).any(axis=1)
        total_row = df_raw[total_mask].iloc[[0]] if total_mask.any() else None
        df = df_raw[~total_mask].copy()

        # 5. STRICT CATEGORIZATION
        # Logic: We force three distinct buckets with no overlap.
        def strict_categorize(row):
            title = str(row[title_col]).lower() if title_col else ""
            # 1. Shorts (Priority 1: Hash tagging)
            if '#' in title:
                return 'Shorts'
            # 2. Live Streams (Priority 2: Your specific stream keywords)
            if any(k in title for k in ['live!', 'watchalong', 'stream', 'let\'s play', 'd&d', 'diablo', 'ready player nerd']):
                return 'Live Stream'
            # 3. Videos (The Remainder)
            return 'Videos'

        df['Category'] = df.apply(strict_categorize, axis=1)

        # 6. CALCULATIONS BY BUCKET
        # Published in 2026 filter for the "Published Counts"
        df_2026 = df[df[publish_col].astype(str).str.contains('2026', na=False)] if publish_col else df

        def get_stats(cat_name):
            group = df[df['Category'] == cat_name]
            # Count only videos published in 2026 for this specific category
            pub_count = len(df_2026[df_2026['Category'] == cat_name]) if not df_2026.empty else 0
            return {
                "views": to_num(group[views_col]).sum(),
                "subs": to_num(group[subs_col]).sum(),
                "watch": to_num(group[watch_col]).sum(),
                "imps": to_num(group[imp_col]).sum(),
                "published": pub_count
            }

        s_stats = get_stats('Shorts')
        v_stats = get_stats('Videos')
        l_stats = get_stats('Live Stream')

        # 7. CHANNEL-LEVEL METRICS
        total_channel_subs = to_num(total_row[subs_col]).sum() if total_row is not None else df[subs_col].sum()
        attributed_subs = s_stats['subs'] + v_stats['subs'] + l_stats['subs']
        other_subs = total_channel_subs - attributed_subs

        # 8. DISPLAY
        st.markdown("---")
        
        # Overview Stats
        top1, top2, top3 = st.columns(3)
        top1.metric("Total Published (2026)", f"{len(df_2026):,}")
        top2.metric("Total Channel Subs Gained", f"{total_channel_subs:,.0f}")
        top3.metric("Other (Non-Video) Subs", f"{other_subs:,.0f}")

        st.markdown("### 🎬 Performance by Content Type")
        
        # Creating three distinct columns for comparison
        col_v, col_s, col_l = st.columns(3)

        with col_v:
            st.info("**Videos**")
            st.write(f"Published in 2026: **{v_stats['published']}**")
            st.metric("Views", f"{v_stats['views']:,.0f}")
            st.metric("Subscribers", f"{v_stats['subs']:,.0f}")
            st.metric("Watch Hours", f"{v_stats['watch']:,.1f}")

        with col_s:
            st.warning("**Shorts**")
            st.write(f"Published in 2026: **{s_stats['published']}**")
            st.metric("Views", f"{s_stats['views']:,.0f}")
            st.metric("Subscribers", f"{s_stats['subs']:,.0f}")
            st.caption(f"Watch Hours: {s_stats['watch']:,.1f}")

        with col_l:
            st.error("**Live Streams**")
            st.write(f"Published in 2026: **{l_stats['published']}**")
            st.metric("Views", f"{l_stats['views']:,.0f}")
            st.metric("Subscribers", f"{l_stats['subs']:,.0f}")
            st.metric("Watch Hours", f"{l_stats['watch']:,.1f}")

    else:
        st.error("Essential columns (Views/Subscribers) not found. Check your CSV export.")
