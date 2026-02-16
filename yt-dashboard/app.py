import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="YouTube Strategy Dashboard", layout="wide")
st.title("📊 YouTube Growth Strategy")
st.subheader("Professional Content Performance & Strategic Analysis")

# --- 2. CONFIG & HELPERS ---
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

        # Convert numeric columns immediately to ensure filtering works
        for col in [views_col, subs_col, watch_col, imp_col, ctr_col]:
            if col: df_data[col] = to_num(df_data[col])

        def categorize(row):
            title = str(row[title_col]).lower()
            duration = row[dur_col] if dur_col else 0
            if any(k in title for k in LIVE_KEYWORDS) and duration > 300:
                return 'Live Stream'
            if '#' in title or duration <= 60:
                return 'Shorts'
            return 'Videos'

        df_data['Category'] = df_data.apply(categorize, axis=1)
        df_data['Parsed_Date'] = pd.to_datetime(df_data[date_col], errors='coerce')
        
        # 2026 Filter for Summary
        df_main_2026 = df_data[df_data['Parsed_Date'].dt.year == 2026].copy()

        # Tabs for Navigation
        tab1, tab2, tab3 = st.tabs(["Performance Summary", "Video Deep Dive", "Shorts Performance"])

        with tab1:
            # 5. METRIC AGGREGATION
            def get_cat_metrics(cat_name):
                group = df_main_2026[df_main_2026['Category'] == cat_name]
                total_imps = group[imp_col].sum()
                avg_ctr = (group[ctr_col] * group[imp_col]).sum() / total_imps if total_imps > 0 else 0
                return {
                    "Published": len(group),
                    "Subscribers": group[subs_col].sum(),
                    "Watch Time": group[watch_col].sum(),
                    "Impressions": total_imps,
                    "CTR": avg_ctr
                }

            v_m = get_cat_metrics('Videos')
            s_m = get_cat_metrics('Shorts')
            l_m = get_cat_metrics('Live Stream')

            total_subs = total_row[subs_col] if total_row is not None else (v_m['Subscribers'] + s_m['Subscribers'] + l_m['Subscribers'])
            other_subs = total_subs - (v_m['Subscribers'] + s_m['Subscribers'] + l_m['Subscribers'])

            st.markdown("---")
            h1, h2, h3 = st.columns(3)
            h1.metric("Total Published (2026)", f"{v_m['Published'] + s_m['Published'] + l_m['Published']}")
            h2.metric("Total Subs Gained", f"{total_subs:,.0f}")
            h3.metric("Other Subscribers", f"{other_subs:,.0f}")

            comparison_data = [
                {"Metric": "Published Count", "Videos": v_m['Published'], "Shorts": s_m['Published'], "Live Streams": l_m['Published'], "Other": "—"},
                {"Metric": "Subscribers", "Videos": f"{v_m['Subscribers']:,.0f}", "Shorts": f"{s_m['Subscribers']:,.0f}", "Live Streams": f"{l_m['Subscribers']:,.0f}", "Other": f"{other_subs:,.0f}"},
                {"Metric": "Watch Time (Hrs)", "Videos": f"{v_m['Watch Time']:,.1f}", "Shorts": f"{s_m['Watch Time']:,.1f}", "Live Streams": f"{l_m['Watch Time']:,.1f}", "Other": "—"},
                {"Metric": "Impressions", "Videos": f"{v_m['Impressions']:,.0f}", "Shorts": f"{s_m['Impressions']:,.0f}", "Live Streams": f"{l_m['Impressions']:,.0f}", "Other": "—"}
            ]
            st.table(pd.DataFrame(comparison_data).set_index("Metric"))

        # Helper Function for Ranking Tables
        def display_rankings(df, metric_col, label, is_ctr=False):
            sorted_df = df.sort_values(by=metric_col, ascending=False)[[title_col, metric_col]].copy()
            
            # Formatting for display
            display_df = sorted_df.copy()
            if is_ctr:
                display_df[metric_col] = display_df[metric_col].map("{:.2f}%".format)
            else:
                display_df[metric_col] = display_df[metric_col].map("{:,.0f}".format)

            top_5 = display_df.head(5).reset_index(drop=True)
            top_5.index += 1
            bottom_5 = display_df.tail(5).iloc[::-1].reset_index(drop=True)
            bottom_5.index += 1
            
            c1, c2 = st.columns(2)
            with c1:
                st.success(f"Top 5: {label}")
                st.dataframe(top_5, use_container_width=True)
            with c2:
                st.error(f"Bottom 5: {label}")
                st.dataframe(bottom_5, use_container_width=True)

        with tab2:
            st.markdown("### 🔍 Video Analysis (Long-Form)")
            video_df = df_data[df_data['Category'] == 'Videos'].copy()
            
            # Standard Metrics
            for label, col in {"Views": views_col, "Subscribers": subs_col, "Watch Time": watch_col}.items():
                st.markdown(f"#### Rank by {label}")
                display_rankings(video_df, col, label)
                st.markdown("---")
            
            # CTR Metric with specific View Threshold
            st.markdown("#### Rank by Impressions CTR")
            st.caption("⚠️ Analysis limited to videos with a minimum of **500 views** to ensure statistical relevance.")
            ctr_filtered_df = video_df[video_df[views_col] >= 500].copy()
            
            if not ctr_filtered_df.empty:
                display_rankings(ctr_filtered_df, ctr_col, "CTR", is_ctr=True)
            else:
                st.warning("No videos found meeting the 500-view threshold for CTR analysis.")
            st.markdown("---")

        with tab3:
            st.markdown("### ⚡ Shorts Performance Analysis")
            shorts_df = df_data[df_data['Category'] == 'Shorts'].copy()
            for label, col in {"Views": views_col, "Subscribers": subs_col}.items():
                st.markdown(f"#### Rank by {label}")
                display_rankings(shorts_df, col, label)
                st.markdown("---")

    else:
        st.error("Missing required columns. Please ensure you are uploading the 'CONTENT' breakdown CSV.")
