import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="YouTube Strategy Dashboard", layout="wide")
st.title("📊 YouTube Growth Strategy")
st.subheader("Advanced Content Analytics & Strategic Planning")

# --- 2. CONFIG & HELPERS ---
# Using professional terminology as requested
LIVE_KEYWORDS = ['live!', 'watchalong', 'stream', "let's play", 'd&d', 'diablo', 'ready player nerd']

def load_yt_csv(file):
    raw_bytes = file.getvalue()
    try:
        content = raw_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        content = raw_bytes.decode("utf-16").splitlines()
    
    header_idx = 0
    for i, line in enumerate(content):
        if any(term in line for term in ["Content", "Video title", "Video publish time"]):
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
    return pd.to_numeric(series.astype(str).str.replace(',', '').str.replace('%', ''), errors='coerce').fillna(0)

# --- 3. FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload 'Table Data.csv' (Content Breakdown)", type="csv")

if uploaded_file:
    df_raw = load_yt_csv(uploaded_file)
    
    # Identify Columns
    title_col = find_column(df_raw, ['Video title', 'Title'])
    date_col = find_column(df_raw, ['Video publish time', 'Published', 'Date'])
    dur_col = find_column(df_raw, ['Duration'])
    views_col = find_column(df_raw, ['Views'])
    subs_col = find_column(df_raw, ['Subscribers'])
    watch_col = find_column(df_raw, ['Watch time (hours)', 'Watch time'])
    imp_col = find_column(df_raw, ['Impressions'])
    ctr_col = find_column(df_raw, ['Impressions click-through rate (%)', 'CTR'])

    if all([title_col, views_col, subs_col]):
        # 4. DATA PROCESSING
        total_mask = df_raw.iloc[:, 0].astype(str).str.contains('Total', case=False, na=False)
        total_row = df_raw[total_mask].iloc[0] if total_mask.any() else None
        df_data = df_raw[~total_mask].copy()

        def categorize(row):
            title = str(row[title_col]).lower()
            duration = to_num(pd.Series([row[dur_col]]))[0] if dur_col else 0
            if any(k in title for k in LIVE_KEYWORDS) and duration > 300:
                return 'Live Stream'
            if '#' in title or duration <= 60:
                return 'Shorts'
            return 'Videos'

        df_data['Category'] = df_data.apply(categorize, axis=1)
        df_data['Parsed_Date'] = pd.to_datetime(df_data[date_col], errors='coerce')
        
        # We will keep the main summary for 2026, but let's allow the Deep Dive 
        # to look at all data for broader strategic learning.
        df_main_2026 = df_data[df_data['Parsed_Date'].dt.year == 2026].copy()

        # Tabs for clean navigation
        tab1, tab2 = st.tabs(["Performance Summary", "Strategic Deep Dive (Videos)"])

        with tab1:
            # 5. METRIC AGGREGATION (Summary)
            def get_cat_metrics(cat_name):
                group = df_main_2026[df_main_2026['Category'] == cat_name]
                imps = to_num(group[imp_col])
                ctrs = to_num(group[ctr_col])
                total_imps = imps.sum()
                avg_ctr = (ctrs * imps).sum() / total_imps if total_imps > 0 else 0
                return {
                    "Published": len(group),
                    "Subscribers": to_num(group[subs_col]).sum(),
                    "Watch Time": to_num(group[watch_col]).sum(),
                    "Impressions": total_imps,
                    "CTR": avg_ctr
                }

            v_metrics = get_cat_metrics('Videos')
            s_metrics = get_cat_metrics('Shorts')
            l_metrics = get_cat_metrics('Live Stream')

            total_subs = to_num(pd.Series([total_row[subs_col]]))[0] if total_row is not None else (v_metrics['Subscribers'] + s_metrics['Subscribers'] + l_metrics['Subscribers'])
            other_subs = total_subs - (v_metrics['Subscribers'] + s_metrics['Subscribers'] + l_metrics['Subscribers'])

            st.markdown("---")
            h1, h2, h3 = st.columns(3)
            h1.metric("Total Published (2026)", f"{v_metrics['Published'] + s_metrics['Published'] + l_metrics['Published']}")
            h2.metric("Total Subs Gained", f"{total_subs:,.0f}")
            h3.metric("Other Subscribers", f"{other_subs:,.0f}")

            comparison_data = [
                {"Metric": "Videos Published", "Videos": v_metrics['Published'], "Shorts": s_metrics['Published'], "Live Streams": l_metrics['Published'], "Other": "—"},
                {"Metric": "Subscribers", "Videos": f"{v_metrics['Subscribers']:,.0f}", "Shorts": f"{s_metrics['Subscribers']:,.0f}", "Live Streams": f"{l_metrics['Subscribers']:,.0f}", "Other": f"{other_subs:,.0f}"},
                {"Metric": "Watch Time (Hours)", "Videos": f"{v_metrics['Watch Time']:,.1f}", "Shorts": f"{s_metrics['Watch Time']:,.1f}", "Live Streams": f"{l_metrics['Watch Time']:,.1f}", "Other": "—"},
                {"Metric": "Impressions", "Videos": f"{v_metrics['Impressions']:,.0f}", "Shorts": f"{s_metrics['Impressions']:,.0f}", "Live Streams": f"{l_metrics['Impressions']:,.0f}", "Other": "—"},
                {"Metric": "Impressions CTR", "Videos": f"{v_metrics['CTR']:.2f}%", "Shorts": f"{s_metrics['CTR']:.2f}%", "Live Streams": f"{l_metrics['CTR']:.2f}%", "Other": "—"}
            ]
            st.table(pd.DataFrame(comparison_data).set_index("Metric"))

        with tab2:
            st.markdown("### 🔍 Long-Form Video Analysis")
            st.info("This section analyzes only 'Videos' to identify content patterns that drive growth or hinder retention.")
            
            # Filter just for videos
            video_df = df_data[df_data['Category'] == 'Videos'].copy()
            
            # Ensure numbers are converted
            metrics_to_analyze = {
                "Views": views_col,
                "Subscribers": subs_col,
                "Watch Time": watch_col,
                "Impressions": imp_col,
                "CTR": ctr_col
            }

            for label, col_name in metrics_to_analyze.items():
                st.markdown(f"#### Rank by {label}")
                
                # Sort and clean data for display
                sorted_df = video_df.sort_values(by=col_name, ascending=False)[[title_col, col_name]].copy()
                
                # Top 5
                top_5 = sorted_df.head(5).reset_index(drop=True)
                top_5.index += 1
                
                # Bottom 5 (Filter > 0 to find the 'least performing active' content if possible)
                bottom_5 = sorted_df[sorted_df[col_name] >= 0].tail(5).iloc[::-1].reset_index(drop=True)
                bottom_5.index += 1

                c1, c2 = st.columns(2)
                with c1:
                    st.success(f"Top 5: {label}")
                    st.dataframe(top_5, use_container_width=True)
                with c2:
                    st.error(f"Bottom 5: {label}")
                    st.dataframe(bottom_5, use_container_width=True)
                st.markdown("---")

    else:
        st.error("Missing required columns. Please ensure you are uploading the 'CONTENT' breakdown CSV.")
