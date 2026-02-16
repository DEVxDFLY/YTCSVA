import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="YouTube Growth Stats", layout="wide")
st.title("📊 YouTube Growth Strategy")
st.subheader("Data-driven reporting for Videos, Shorts, and Live Streams")

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
        # 4. REMOVE TOTAL ROW
        # We look at the first column specifically for the word "Total"
        total_mask = df_raw.iloc[:, 0].astype(str).str.contains('Total', case=False, na=False)
        total_row = df_raw[total_mask].iloc[[0]] if total_mask.any() else None
        df_data = df_raw[~total_mask].copy()

        # 5. STRICT CATEGORIZATION
        # Live Streams have priority keywords. Shorts are defined by #. Videos are the rest.
        def strict_categorize(row):
            title = str(row[title_col]).lower() if title_col else ""
            # Priority 1: Live Keywords (Locked in as perfect)
            if any(k in title for k in ['live!', 'watchalong', 'stream', 'let\'s play', 'd&d', 'diablo', 'ready player nerd']):
                return 'Live Stream'
            # Priority 2: Shorts Hashtag
            if '#' in title:
                return 'Shorts'
            # Priority 3: Remainder
            return 'Videos'

        df_data['Category'] = df_data.apply(strict_categorize, axis=1)

        # 6. TIME FILTER (Published in 2026)
        # Using datetime conversion to ensure the 107 count is accurate
        df_data['Date_Clean'] = pd.to_datetime(df_data[publish_col], errors='coerce')
        df_2026 = df_data[df_data['Date_Clean'].dt.year == 2026].copy()
        
        # Remove empty video artifacts (rows with 0 views and 0 impressions)
        df_2026_final = df_2026[(df_2026[views_col] > 0) | (df_2026[imp_col] > 0)]

        # 7. METRIC CALCULATIONS
        def get_stats(cat_name):
            group = df_data[df_data['Category'] == cat_name]
            # Counting published videos from the 2026 filtered list
            pub_count = len(df_2026_final[df_2026_final['Category'] == cat_name])
            return {
                "views": to_num(group[views_col]).sum(),
                "subs": to_num(group[subs_col]).sum(),
                "watch": to_num(group[watch_col]).sum(),
                "imps": to_num(group[imp_col]).sum(),
                "published": pub_count
            }

        s = get_stats('Shorts')
        v = get_stats('Videos')
        l = get_stats('Live Stream')

        # Totals for Ratio and Other
        total_channel_subs = to_num(total_row[subs_col]).sum() if total_row is not None else df_data[subs_col].sum()
        total_channel_views = to_num(total_row[views_col]).sum() if total_row is not None else df_data[views_col].sum()
        other_subs = total_channel_subs - (s['subs'] + v['subs'] + l['subs'])
        sub_ratio = (total_channel_subs / total_channel_views * 100) if total_channel_views > 0 else 0

        # 8. DISPLAY
        st.markdown("---")
        
        # Global Metrics
        top1, top2, top3, top4 = st.columns(4)
        top1.metric("Total Published (2026)", f"{len(df_2026_final)}")
        top2.metric("Sub-to-View Ratio", f"{sub_ratio:.2f}%")
        top3.metric("Other Subscribers", f"{other_subs:,.0f}")
        top4.metric("Total Subs Gained", f"{total_channel_subs:,.0f}")

        st.markdown("---")
        
        # Categories
        col_v, col_s, col_l = st.columns(3)

        with col_v:
            st.info("**Edited Videos**")
            st.write(f"Published (2026): **{v['published']}**")
            st.metric("Views", f"{v['views']:,.0f}")
            st.metric("Subscribers", f"{v['subs']:,.0f}")
            st.metric("Watch Hours", f"{v['watch']:,.1f}")
            st.metric("Impressions", f"{v['imps']:,.0f}")

        with col_s:
            st.warning("**Shorts**")
            st.write(f"Published (2026): **{s['published']}**")
            st.metric("Views", f"{s['views']:,.0f}")
            st.metric("Subscribers", f"{s['subs']:,.0f}")
            st.caption(f"Watch Hours ({s['watch']:.1f}) are excluded from totals.")
            st.metric("Impressions", f"{s['imps']:,.0f}")

        with col_l:
            st.error("**Live Streams**")
            st.write(f"Published (2026): **{l['published']}**")
            st.metric("Views", f"{l['views']:,.0f}")
            st.metric("Subscribers", f"{l['subs']:,.0f}")
            st.metric("Watch Hours", f"{l['watch']:,.1f}")
            st.metric("Impressions", f"{l['imps']:,.0f}")

    else:
        st.error("Column mapping failed. Please ensure the CSV contains 'Views' and 'Subscribers gained' columns.")
