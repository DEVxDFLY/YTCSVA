import streamlit as st
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="YouTube Strategy Dashboard", layout="wide")
st.title("📊 YouTube Growth Strategy")
st.subheader("Advanced Content Analytics (Videos, Shorts, & Live)")

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
        # We look for "Content" which is the ID column in the detailed report
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
    
    # Identify Columns Robustly
    title_col = find_column(df_raw, ['Video title', 'Title'])
    date_col = find_column(df_raw, ['Video publish time', 'Published', 'Date'])
    dur_col = find_column(df_raw, ['Duration'])
    views_col = find_column(df_raw, ['Views'])
    subs_col = find_column(df_raw, ['Subscribers'])
    watch_col = find_column(df_raw, ['Watch time (hours)', 'Watch time'])
    imp_col = find_column(df_raw, ['Impressions'])
    ctr_col = find_column(df_raw, ['Impressions click-through rate (%)', 'CTR'])

    if all([title_col, views_col, subs_col]):
        # 4. SEPARATE TOTALS & DATA
        # In detailed reports, 'Total' is often the first row
        total_mask = df_raw.iloc[:, 0].astype(str).str.contains('Total', case=False, na=False)
        total_row = df_raw[total_mask].iloc[0] if total_mask.any() else None
        df_data = df_raw[~total_mask].copy()

        # 5. CATEGORIZATION LOGIC
        def categorize(row):
            title = str(row[title_col]).lower()
            duration = to_num(pd.Series([row[dur_col]]))[0] if dur_col else 0
            
            # Live Streams: Keywords + must be longer than 5 mins to exclude clips
            if any(k in title for k in LIVE_KEYWORDS) and duration > 300:
                return 'Live Stream'
            # Shorts: Has hashtag OR is 60 seconds or less
            if '#' in title or duration <= 60:
                return 'Shorts'
            # Everything else is a Video
            return 'Videos'

        df_data['Category'] = df_data.apply(categorize, axis=1)
        
        # Filter for 2026 data specifically (Optional: remove filter to see all time)
        df_data['Parsed_Date'] = pd.to_datetime(df_data[date_col], errors='coerce')
        df_main = df_data[df_data['Parsed_Date'].dt.year == 2026].copy()

        # 6. METRIC AGGREGATION
        def get_cat_metrics(cat_name):
            group = df_main[df_main['Category'] == cat_name]
            
            # Weighted CTR Calculation: (Sum of CTR * Impressions) / Sum of Impressions
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

        v = get_cat_metrics('Videos')
        s = get_cat_metrics('Shorts')
        l = get_cat_metrics('Live Stream')

        # 7. CALCULATE "OTHER"
        # Total row represents the whole channel state, including non-video subs
        total_subs = to_num(pd.Series([total_row[subs_col]]))[0] if total_row is not None else (v['Subscribers'] + s['Subscribers'] + l['Subscribers'])
        other_subs = total_subs - (v['Subscribers'] + s['Subscribers'] + l['Subscribers'])

        # --- 8. DISPLAY TABLE ---
        st.markdown("---")
        
        # Key Highlights
        h1, h2, h3 = st.columns(3)
        h1.metric("Total Published (2026)", f"{v['Published'] + s['Published'] + l['Published']}")
        h2.metric("Total Subs Gained", f"{total_subs:,.0f}")
        h3.metric("Other Subscribers", f"{other_subs:,.0f}")

        # Summary Table
        comparison_data = [
            {
                "Metric": "Videos Published",
                "Videos": v['Published'],
                "Shorts": s['Published'],
                "Live Streams": l['Published'],
                "Other": "—"
            },
            {
                "Metric": "Subscribers",
                "Videos": f"{v['Subscribers']:,.0f}",
                "Shorts": f"{s['Subscribers']:,.0f}",
                "Live Streams": f"{l['Subscribers']:,.0f}",
                "Other": f"{other_subs:,.0f}"
            },
            {
                "Metric": "Watch Time (Hours)",
                "Videos": f"{v['Watch Time']:,.1f}",
                "Shorts": f"{s['Watch Time']:,.1f}",
                "Live Streams": f"{l['Watch Time']:,.1f}",
                "Other": "—"
            },
            {
                "Metric": "Impressions",
                "Videos": f"{v['Impressions']:,.0f}",
                "Shorts": f"{s['Impressions']:,.0f}",
                "Live Streams": f"{l['Impressions']:,.0f}",
                "Other": "—"
            },
            {
                "Metric": "Impressions CTR",
                "Videos": f"{v['CTR']:.2f}%",
                "Shorts": f"{s['CTR']:.2f}%",
                "Live Streams": f"{l['CTR']:.2f}%",
                "Other": "—"
            }
        ]

        st.table(pd.DataFrame(comparison_data).set_index("Metric"))
        st.info("💡 **Logic:** Content is categorized as a **Live Stream** if the title contains stream keywords and is > 5 minutes long. **Shorts** are identified by '#' or a duration of 60 seconds or less.")

    else:
        st.error("Missing required columns. Please ensure you are uploading the 'CONTENT' breakdown CSV.")
