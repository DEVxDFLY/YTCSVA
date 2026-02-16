import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="YouTube Growth Stats", layout="wide")
st.title("📊 YouTube Growth Strategy")
st.subheader("Official Data Reporting (Videos, Shorts, Live, & Other)")

# --- 2. HELPERS ---
def load_yt_csv(file):
    raw_bytes = file.getvalue()
    try:
        content = raw_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        content = raw_bytes.decode("utf-16").splitlines()
    
    header_idx = 0
    for i, line in enumerate(content):
        if any(term in line for term in ["Views", "Video title", "Subscribers", "Impressions", "Content type"]):
            header_idx = i
            break
            
    file.seek(0)
    df = pd.read_csv(file, skiprows=header_idx, sep=None, engine='python')
    df.columns = df.columns.str.strip().str.replace('"', '')
    return df

def to_num(series):
    return pd.to_numeric(series.astype(str).str.replace(',', ''), errors='coerce').fillna(0)

# --- 3. FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload Table Data.csv", type="csv")

if uploaded_file:
    df_raw = load_yt_csv(uploaded_file)
    
    # Identify Columns
    type_col = next((c for c in df_raw.columns if "Content type" in c or "Video type" in c), None)
    pub_col = next((c for c in df_raw.columns if "Videos published" in c), None)
    views_col = next((c for c in df_raw.columns if "Views" in c), None)
    subs_col = next((c for c in df_raw.columns if "Subscribers gained" in c or "Subscribers" in c), None)
    watch_col = next((c for c in df_raw.columns if "Watch time" in c), None)
    imp_col = next((c for c in df_raw.columns if "Impressions" in c), None)

    if views_col and subs_col:
        # 4. CLEAN DATA
        total_mask = df_raw.iloc[:, 0].astype(str).str.contains('Total', case=False, na=False)
        total_row = df_raw[total_mask]
        df_data = df_raw[~total_mask].copy()

        # 5. EXTRACTION (Strictly following the CSV Rows)
        def get_row_stats(category_name):
            # We look for the exact string in the 'Content type' column
            row = df_data[df_data[type_col].str.lower() == category_name.lower()]
            if not row.empty:
                return {
                    "published": int(to_num(row[pub_col]).sum()) if pub_col else 0,
                    "views": to_num(row[views_col]).sum(),
                    "subs": to_num(row[subs_col]).sum(),
                    "watch": to_num(row[watch_col]).sum(),
                    "imps": to_num(row[imp_col]).sum()
                }
            return {"published": 0, "views": 0, "subs": 0, "watch": 0, "imps": 0}

        # Categories mapping to your CSV values
        s = get_row_stats('Shorts')
        v = get_row_stats('Videos')
        l = get_row_stats('Live stream')
        o = get_row_stats('Other')

        # Global Metrics
        total_subs = to_num(total_row[subs_col]).sum() if not total_row.empty else (s['subs']+v['subs']+l['subs']+o['subs'])
        total_views = to_num(total_row[views_col]).sum() if not total_row.empty else (s['views']+v['views']+l['views']+o['views'])
        sub_ratio = (total_subs / total_views * 100) if total_views > 0 else 0

        # --- 6. DISPLAY ---
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Published", f"{s['published'] + v['published'] + l['published']}")
        m2.metric("Sub-to-View Ratio", f"{sub_ratio:.2f}%")
        m3.metric("Total Subs Gained", f"{total_subs:,.0f}")
        m4.metric("Other Subs", f"{o['subs']:,.0f}", help="Subs from channel page or other non-video sources")

        st.markdown("### 📊 Metric Comparison")
        
        comparison_data = [
            {"Metric": "Count", "Videos": v['published'], "Shorts": s['published'], "Live Streams": l['published'], "Other": "N/A"},
            {"Metric": "Views", "Videos": f"{v['views']:,.0f}", "Shorts": f"{s['views']:,.0f}", "Live Streams": f"{l['views']:,.0f}", "Other": f"{o['views']:,.0f}"},
            {"Metric": "Subscribers", "Videos": f"{v['subs']:,.0f}", "Shorts": f"{s['subs']:,.0f}", "Live Streams": f"{l['subs']:,.0f}", "Other": f"{o['subs']:,.0f}"},
            {"Metric": "Watch Time", "Videos": f"{v['watch']:,.1f}", "Shorts": f"{s['watch']:,.1f}", "Live Streams": f"{l['watch']:,.1f}", "Other": f"{o['watch']:,.1f}"},
        ]
        
        st.table(pd.DataFrame(comparison_data).set_index("Metric"))
        
        st.info("💡 **Note:** 'Other' captures subscribers gained from your Channel Page, Search, or deleted content. This explains why the category totals might differ slightly from your manual counts.")

    else:
        st.error("Missing required columns in CSV.")
