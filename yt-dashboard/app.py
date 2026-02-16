import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="YouTube Growth Stats", layout="wide")
st.title("📊 YouTube Growth Strategy")
st.subheader("Data-driven reporting for Videos, Shorts, and Live Streams")

# --- 2. HELPERS ---
def load_yt_csv(file):
    raw_bytes = file.getvalue()
    try:
        content = raw_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        content = raw_bytes.decode("utf-16").splitlines()
    
    header_idx = 0
    for i, line in enumerate(content):
        # Added 'Content type' to the header detection list
        if any(term in line for term in ["Views", "Video title", "Subscribers", "Impressions", "Content type"]):
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
    type_col = find_column(df_raw, ['Content type', 'Video type']) # New: Look for YouTube's Type column
    views_col = find_column(df_raw, ['Views'])
    subs_col = find_column(df_raw, ['Subscribers gained', 'Subscribers'])
    watch_col = find_column(df_raw, ['Watch time (hours)', 'Watch time'])
    imp_col = find_column(df_raw, ['Impressions'])
    publish_col = find_column(df_raw, ['Video publish time', 'Published'])

    if views_col and subs_col:
        # 4. REMOVE TOTAL ROW
        total_mask = df_raw.iloc[:, 0].astype(str).str.contains('Total', case=False, na=False)
        total_row = df_raw[total_mask].iloc[[0]] if total_mask.any() else None
        df_data = df_raw[~total_mask].copy()

        # 5. IMPROVED CATEGORIZATION
        def strict_categorize(row):
            # If the CSV has a 'Content type' column, use it first (Direct from YT)
            if type_col:
                ctype = str(row[type_col]).lower()
                if 'video' in ctype: return 'Videos'
                if 'short' in ctype: return 'Shorts'
                if 'live' in ctype: return 'Live Stream'

            # Fallback to your keyword logic if 'Content type' isn't in the CSV
            title = str(row[title_col]).lower() if title_col else ""
            if any(k in title for k in ['live!', 'watchalong', 'stream', 'let\'s play', 'd&d', 'diablo', 'ready player nerd']):
                return 'Live Stream'
            if '#' in title:
                return 'Shorts'
            return 'Videos'

        df_data['Category'] = df_data.apply(strict_categorize, axis=1)

        # 6. TIME FILTER (Published in 2026)
        df_data['Date_Clean'] = pd.to_datetime(df_data[publish_col], errors='coerce')
        df_2026 = df_data[df_data['Date_Clean'].dt.year == 2026].copy()
        
        # Clean numeric columns to ensure math works
        for col in [views_col, subs_col, watch_col, imp_col]:
            df_data[col] = to_num(df_data[col])
            df_2026[col] = to_num(df_2026[col])

        # Remove empty artifacts
        df_2026_final = df_2026[(df_2026[views_col] > 0) | (df_2026[imp_col] > 0)]

        # 7. METRIC CALCULATIONS
        def get_stats(cat_name):
            group = df_data[df_data['Category'] == cat_name]
            pub_count = len(df_2026_final[df_2026_final['Category'] == cat_name])
            return {
                "views": group[views_col].sum(),
                "subs": group[subs_col].sum(),
                "watch": group[watch_col].sum(),
                "imps": group[imp_col].sum(),
                "published": pub_count
            }

        s = get_stats('Shorts')
        v = get_stats('Videos')
        l = get_stats('Live Stream')

        # Totals logic
        total_channel_subs = to_num(total_row[subs_col]).sum() if total_row is not None else df_data[subs_col].sum()
        total_channel_views = to_num(total_row[views_col]).sum() if total_row is not None else df_data[views_col].sum()
        other_subs = total_channel_subs - (s['subs'] + v['subs'] + l['subs'])
        sub_ratio = (total_channel_subs / total_channel_views * 100) if total_channel_views > 0 else 0

        # 8. DISPLAY (Keep your existing display logic here...)
        # [Remaining Streamlit UI code goes here]
        st.write("Processing Complete.") # Placeholder for your UI columns
