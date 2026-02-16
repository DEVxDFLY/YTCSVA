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
    # Search for the row containing actual data headers
    for i, line in enumerate(content):
        if any(term in line for term in ["Views", "Video title", "Subscribers", "Impressions", "Content"]):
            header_idx = i
            break
            
    file.seek(0)
    df = pd.read_csv(file, skiprows=header_idx, sep=None, engine='python')
    # Clean headers of whitespace and quotes
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
    
    # Robust Column Mapping
    type_col = find_column(df_raw, ['Content type', 'Video type', 'Content'])
    pub_col = find_column(df_raw, ['Videos published', 'Published', 'Video publish time'])
    views_col = find_column(df_raw, ['Views'])
    subs_col = find_column(df_raw, ['Subscribers gained', 'Subscribers'])
    watch_col = find_column(df_raw, ['Watch time (hours)', 'Watch time'])
    imp_col = find_column(df_raw, ['Impressions'])

    if views_col and subs_col:
        # 4. DATA CLEANING
        # Identify the Total row to exclude it from category math
        total_mask = df_raw.iloc[:, 0].astype(str).str.contains('Total', case=False, na=False)
        total_row = df_raw[total_mask]
        df_data = df_raw[~total_mask].copy()

        # 5. DATA EXTRACTION
        def get_stats(category_search_term):
            if type_col is None:
                return {"published": 0, "views": 0, "subs": 0, "watch": 0, "imps": 0}
            
            # Find the row where the type matches our target
            mask = df_data[type_col].astype(str).str.lower().str.contains(category_search_term.lower(), na=False)
            row = df_data[mask]
            
            if not row.empty:
                return {
                    "published": int(to_num(row[pub_col]).sum()) if pub_col else 0,
                    "views": to_num(row[views_col]).sum(),
                    "subs": to_num(row[subs_col]).sum(),
                    "watch": to_num(row[watch_col]).sum(),
                    "imps": to_num(row[imp_col]).sum()
                }
            return {"published": 0, "views": 0, "subs": 0, "watch": 0, "imps": 0}

        # Pull stats for each official category
        s = get_stats('Shorts')
        v = get_stats('Videos')
        l = get_stats('Live stream')
        o = get_stats('Other')

        # Global Calculations
        # Total Published = sum of categorized video types
        total_pub = s['published'] + v['published'] + l['published']
        
        # Total Subs = use the "Total" row from CSV if available, otherwise sum all (including Other)
        total_channel_subs = to_num(total_row[subs_col]).sum() if not total_row.empty else (s['subs'] + v['subs'] + l['subs'] + o['subs'])
        total_channel_views = to_num(total_row[views_col]).sum() if not total_row.empty else (s['views'] + v['views'] + l['views'] + o['views'])
        
        sub_ratio = (total_channel_subs / total_channel_views * 100) if total_channel_views > 0 else 0

        # --- 6. DISPLAY ---
        st.markdown("---")
        top1, top2, top3, top4 = st.columns(4)
        top1.metric("Total Published", f"{total_pub}")
        top2.metric("Sub-to-View Ratio", f"{sub_ratio:.2f}%")
        top3.metric("Total Subs Gained", f"{total_channel_subs:,.0f}")
        top4.metric("Other Sources", f"{o['subs']:,.0f}")

        st.markdown("### 📊 Metric Comparison")
        
        comparison_data = [
            {"Metric": "Count", "Videos": v['published'], "Shorts": s['published'], "Live Streams": l['published'], "Other": "—"},
            {"Metric": "Views", "Videos": f"{v['views']:,.0f}", "Shorts": f"{s['views']:,.0f}", "Live Streams": f"{l['views']:,.0f}", "Other": f"{o['views']:,.0f}"},
            {"Metric": "Subscribers", "Videos": f"{v['subs']:,.0f}", "Shorts": f"{s['subs']:,.0f}", "Live Streams": f"{l['subs']:,.0f}", "Other": f"{o['subs']:,.0f}"},
            {"Metric": "Watch Time (Hrs)", "Videos": f"{v['watch']:,.1f}", "Shorts": f"{s['watch']:,.1f}", "Live Streams": f"{l['watch']:,.1f}", "Other": f"{o['watch']:,.1f}"},
        ]
        
        st.table(pd.DataFrame(comparison_data).set_index("Metric"))
        
        st.caption("Note: 'Other' includes subscribers gained from your Channel Page, Search, or removed content.")

    else:
        st.error("Could not find necessary columns (Views/Subscribers). Check CSV format.")
