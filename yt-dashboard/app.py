import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="YouTube Metrics Fix", layout="wide")
st.title("📊 YouTube Performance Summary")

# --- 2. HELPERS (ROBUST) ---
def load_yt_csv(file):
    raw_bytes = file.getvalue()
    try:
        content = raw_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        content = raw_bytes.decode("utf-16").splitlines()
    
    header_idx = 0
    for i, line in enumerate(content):
        # Hunt for headers based on standard YouTube terms
        if any(term in line for term in ["Views", "Video title", "Subscribers", "Impressions"]):
            header_idx = i
            break
            
    file.seek(0)
    df = pd.read_csv(file, skiprows=header_idx, sep=None, engine='python')
    df.columns = df.columns.str.strip().str.replace('"', '')
    return df

def find_column(df, possible_names):
    """Finds a column even if the name varies slightly."""
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
    
    # 4. DYNAMIC COLUMN MAPPING
    title_col = find_column(df_raw, ['Video title', 'Title', 'Content'])
    views_col = find_column(df_raw, ['Views'])
    subs_col = find_column(df_raw, ['Subscribers gained', 'Subscribers'])
    watch_col = find_column(df_raw, ['Watch time (hours)', 'Watch time'])
    imp_col = find_column(df_raw, ['Impressions'])
    ctr_col = find_column(df_raw, ['Impressions click-through rate (%)', 'CTR'])
    publish_col = find_column(df_raw, ['Video publish time', 'Published'])

    if views_col and subs_col:
        # 5. ROBUST TOTAL ROW DETECTION (Fixed the KeyError)
        # Instead of looking for a 'Content' column, we scan every column for the word 'Total'
        total_mask = df_raw.stack().str.contains('Total', case=False, na=False).unstack().any(axis=1)
        total_row = df_raw[total_mask].iloc[[0]] if total_mask.any() else None
        
        # Individual videos (everything that isn't the Total row)
        df = df_raw[~total_mask].copy()

        # 6. CATEGORIZATION LOGIC
        def categorize(row):
            title = str(row[title_col]).lower() if title_col else ""
            if '#' in title:
                return 'Shorts'
            if any(k in title for k in ['live!', 'watchalong', 'stream', 'let\'s play', 'd&d', 'diablo', 'ready player nerd']):
                return 'Live Stream'
            return 'Videos'

        df['Category'] = df.apply(categorize, axis=1)

        # 7. METRICS CALCULATION
        # Published in 2026 filter
        df_2026 = df[df[publish_col].astype(str).str.contains('2026', na=False)] if publish_col else df

        def get_group_stats(category_name):
            group = df[df['Category'] == category_name]
            pub_count = len(df_2026[df_2026['Category'] == category_name]) if not df_2026.empty else 0
            return {
                "views": to_num(group[views_col]).sum(),
                "watch": to_num(group[watch_col]).sum(),
                "subs": to_num(group[subs_col]).sum(),
                "imps": to_num(group[imp_col]).sum(),
                "ctr": to_num(group[ctr_col]).mean() if ctr_col else 0,
                "published": pub_count
            }

        s = get_group_stats('Shorts')
        v = get_group_stats('Videos')
        l = get_group_stats('Live Stream')

        # 'Other' subscribers calculation
        total_channel_subs = to_num(total_row[subs_col]).sum() if total_row is not None else df[subs_col].sum()
        attributed_subs = df[subs_col].sum()
        other_subs = total_channel_subs - attributed_subs

        total_v = s['views'] + v['views'] + l['views']
        sub_ratio = (total_channel_subs / total_v * 100) if total_v > 0 else 0

        # 8. DISPLAY
        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Overall Sub-to-View Ratio", f"{sub_ratio:.2f}%")
        c2.metric("Total Impressions", f"{to_num(total_row[imp_col]).sum() if total_row is not None else 0:,.0f}")
        c3.metric("Other Subscribers", f"{other_subs:,.0f}")
        c4.metric("Total Sub-Gain", f"{total_channel_subs:,.0f}")

        col_v, col_s, col_l = st.columns(3)

        with col_v:
            st.info("**Videos**")
            st.write(f"Published: **{v['published']}**")
            st.metric("Views", f"{v['views']:,.0f}")
            st.metric("Watch Hours", f"{v['watch']:,.1f}")
            st.metric("Subs Gained", f"{v['subs']:,.0f}")

        with col_s:
            st.warning("**Shorts**")
            st.write(f"Published: **{s['published']}**")
            st.metric("Views", f"{s['views']:,.0f}")
            st.metric("Watch Hours", f"{s['watch']:,.1f}")
            st.metric("Subs Gained", f"{s['subs']:,.0f}")

        with col_l:
            st.error("**Live Streams**")
            st.write(f"Published: **{l['published']}**")
            st.metric("Views", f"{l['views']:,.0f}")
            st.metric("Watch Hours", f"{l['watch']:,.1f}")
            st.metric("Subs Gained", f"{l['subs']:,.0f}")

    else:
        st.error("Column mapping failed. Please check your CSV format.")
