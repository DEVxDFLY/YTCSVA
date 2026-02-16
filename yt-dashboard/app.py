import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="YouTube Growth Stats", layout="wide")
st.title("📊 YouTube Growth Strategy")
st.subheader("Reporting for Videos, Shorts, and Live Streams")

# --- 2. HELPERS ---
def load_yt_csv(file):
    raw_bytes = file.getvalue()
    try:
        content = raw_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        content = raw_bytes.decode("utf-16").splitlines()
    
    header_idx = 0
    for i, line in enumerate(content):
        if any(term in line for term in ["Views", "Video title", "Subscribers", "Impressions", "Content type", "Content"]):
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
    # Added 'Content' here to catch detailed reports
    title_col = find_column(df_raw, ['Video title', 'Title', 'Content']) 
    type_col = find_column(df_raw, ['Content type', 'Video type'])
    pub_count_col = find_column(df_raw, ['Videos published'])
    views_col = find_column(df_raw, ['Views'])
    subs_col = find_column(df_raw, ['Subscribers gained', 'Subscribers'])
    watch_col = find_column(df_raw, ['Watch time (hours)', 'Watch time'])
    imp_col = find_column(df_raw, ['Impressions'])
    publish_time_col = find_column(df_raw, ['Video publish time', 'Published'])

    if views_col and subs_col:
        # 4. REMOVE TOTAL ROW
        total_mask = df_raw.iloc[:, 0].astype(str).str.contains('Total', case=False, na=False)
        total_row = df_raw[total_mask]
        df_data = df_raw[~total_mask].copy()

        # 5. DATA EXTRACTION LOGIC
        def get_stats(cat_name):
            yt_names = {
                'Shorts': ['shorts'],
                'Videos': ['videos', 'video'],
                'Live Stream': ['live stream', 'live']
            }
            targets = yt_names.get(cat_name, [cat_name.lower()])

            # SCENARIO A: Summary File (The one you uploaded)
            if type_col and pub_count_col:
                mask = df_data[type_col].str.lower().isin(targets)
                row = df_data[mask]
                if not row.empty:
                    return {
                        "views": to_num(row[views_col]).sum(),
                        "subs": to_num(row[subs_col]).sum(),
                        "watch": to_num(row[watch_col]).sum(),
                        "imps": to_num(row[imp_col]).sum(),
                        "published": int(to_num(row[pub_count_col]).sum())
                    }

            # SCENARIO B: Detailed Video List (Individual videos)
            if title_col:
                def categorize(r):
                    t = str(r[title_col]).lower()
                    if any(k in t for k in ['live!', 'watchalong', 'stream', 'let\'s play', 'd&d', 'diablo', 'ready player nerd']):
                        return 'Live Stream'
                    if '#' in t: return 'Shorts'
                    return 'Videos'
                
                df_data['Category'] = df_data.apply(categorize, axis=1)
                group = df_data[df_data['Category'] == cat_name]
                
                pub_count = 0
                if publish_time_col:
                    # Filter for 2026 if the date column exists
                    dates = pd.to_datetime(df_data[publish_time_col], errors='coerce')
                    pub_count = len(df_data[(df_data['Category'] == cat_name) & (dates.dt.year == 2026)])
                else:
                    # If no date column, just count all rows in this category
                    pub_count = len(group)
                
                return {
                    "views": to_num(group[views_col]).sum(),
                    "subs": to_num(group[subs_col]).sum(),
                    "watch": to_num(group[watch_col]).sum(),
                    "imps": to_num(group[imp_col]).sum(),
                    "published": pub_count
                }
            
            return {"views": 0, "subs": 0, "watch": 0, "imps": 0, "published": 0}

        # Calculations
        s = get_stats('Shorts')
        v = get_stats('Videos')
        l = get_stats('Live Stream')

        # Global Metrics
        total_channel_subs = to_num(total_row[subs_col]).sum() if not total_row.empty else (s['subs'] + v['subs'] + l['subs'])
        total_channel_views = to_num(total_row[views_col]).sum() if not total_row.empty else (s['views'] + v['views'] + l['views'])
        sub_ratio = (total_channel_subs / total_channel_views * 100) if total_channel_views > 0 else 0

        # --- 6. DISPLAY ---
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Published", f"{s['published'] + v['published'] + l['published']}")
        m2.metric("Sub-to-View Ratio", f"{sub_ratio:.2f}%")
        m3.metric("Total Subs Gained", f"{total_channel_subs:,.0f}")

        st.markdown("### 📈 Metric Comparison by Category")
        
        comparison_data = [
            {"Metric": "Videos Published", "Videos": v['published'], "Shorts": s['published'], "Live Streams": l['published']},
            {"Metric": "Views", "Videos": f"{v['views']:,.0f}", "Shorts": f"{s['views']:,.0f}", "Live Streams": f"{l['views']:,.0f}"},
            {"Metric": "Subscribers Gained", "Videos": f"{v['subs']:,.0f}", "Shorts": f"{s['subs']:,.0f}", "Live Streams": f"{l['subs']:,.0f}"},
            {"Metric": "Watch Time (Hours)", "Videos": f"{v['watch']:,.1f}", "Shorts": f"{s['watch']:,.1f}", "Live Streams": f"{l['watch']:,.1f}"},
            {"Metric": "Impressions", "Videos": f"{v['imps']:,.0f}", "Shorts": f"{s['imps']:,.0f}", "Live Streams": f"{l['imps']:,.0f}"},
        ]
        
        st.table(pd.DataFrame(comparison_data).set_index("Metric"))

    else:
        st.error("Column mapping failed. Please ensure the CSV contains 'Views' and 'Subscribers' columns.")
