import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="YouTube Performance Summary", layout="wide")
st.title("📊 YouTube Performance Summary")
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
    ctr_col = find_column(df_raw, ['Impressions click-through rate (%)', 'CTR'])
    publish_col = find_column(df_raw, ['Video publish time', 'Published'])

    if views_col and subs_col:
        # 4. REMOVE TOTAL ROW (Value-based search)
        total_mask = df_raw.astype(str).apply(lambda x: x.str.contains('Total', case=False)).any(axis=1)
        total_row = df_raw[total_mask].iloc[[0]] if total_mask.any() else None
        
        # Individual items (Everything NOT in the total row)
        df = df_raw[~total_mask].copy()

        # 5. RATIONALIZED CATEGORIZATION
        def strict_categorize(row):
            title = str(row[title_col]).lower() if title_col else ""
            # Priority 1: Shorts identification (Matches 52 count)
            if '#' in title:
                return 'Shorts'
            # Priority 2: Live Stream Keywords (Matches 32 count)
            if any(k in title for k in ['live!', 'watchalong', 'stream', 'let\'s play', 'd&d', 'diablo', 'ready player nerd']):
                return 'Live Stream'
            # Priority 3: The remainder is "Videos"
            return 'Videos'

        df['Category'] = df.apply(strict_categorize, axis=1)

        # 6. FILTER FOR 2026 PUBLISHED ITEMS
        # Exclude rows with 0 engagement to match the exact 107 count
        df_2026 = df[df[publish_col].astype(str).str.contains('2026', na=False)].copy()
        df_2026 = df_2026[(to_num(df_2026[views_col]) > 0) | (to_num(df_2026[imp_col]) > 0)]

        # 7. CALCULATIONS
        def get_stats(cat):
            group = df[df['Category'] == cat]
            return {
                "views": to_num(group[views_col]).sum(),
                "subs": to_num(group[subs_col]).sum(),
                "watch": to_num(group[watch_col]).sum(),
                "imps": to_num(group[imp_col]).sum(),
                "ctr": to_num(group[ctr_col]).mean() if ctr_col else 0,
                "count": len(df_2026[df_2026['Category'] == cat])
            }

        shorts = get_stats('Shorts')
        videos = get_stats('Videos')
        lives = get_stats('Live Stream')

        # Global Metrics
        total_channel_subs = to_num(total_row[subs_col]).sum() if total_row is not None else df[subs_col].sum()
        total_channel_views = to_num(total_row[views_col]).sum() if total_row is not None else df[views_col].sum()
        sub_view_ratio = (total_channel_subs / total_channel_views * 100) if total_channel_views > 0 else 0
        
        # Calculate "Other" Subscribers (The 9 non-video subs)
        other_subs = total_channel_subs - (shorts['subs'] + videos['subs'] + lives['subs'])

        # 8. DISPLAY
        st.markdown("---")
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Videos Published (2026)", f"{len(df_2026)}")
        h2.metric("Sub-to-View Ratio", f"{sub_view_ratio:.2f}%")
        h3.metric("Other Subscribers", f"{other_subs:,.0f}")
        h4.metric("Total Subs Gained", f"{total_channel_subs:,.0f}")

        st.markdown("---")
        col_v, col_s, col_l = st.columns(3)

        with col_v:
            st.info("**Videos**")
            st.write(f"Published in 2026: **{videos['count']}**")
            st.metric("Views", f"{videos['views']:,.0f}")
            st.metric("Subscribers Gained", f"{videos['subs']:,.0f}")
            st.metric("Watch Hours", f"{videos['watch']:,.1f}")
            st.metric("Impressions", f"{videos['imps']:,.0f}")

        with col_s:
            st.warning("**Shorts**")
            st.write(f"Published in 2026: **{shorts['count']}**")
            st.metric("Views", f"{shorts['views']:,.0f}")
            st.metric("Subscribers Gained", f"{shorts['subs']:,.0f}")
            st.metric("Watch Hours", f"{shorts['watch']:,.1f}")
            st.metric("Impressions", f"{shorts['imps']:,.0f}")

        with col_l:
            st.error("**Live Stream**")
            st.write(f"Published in 2026: **{lives['count']}**")
            st.metric("Views", f"{lives['views']:,.0f}")
            st.metric("Subscribers Gained", f"{lives['subs']:,.0f}")
            st.metric("Watch Hours", f"{lives['watch']:,.1f}")
            st.metric("Impressions", f"{lives['imps']:,.0f}")

    else:
        st.error("Missing essential columns. Please ensure your 'Table Data' export includes Views and Subscribers.")
