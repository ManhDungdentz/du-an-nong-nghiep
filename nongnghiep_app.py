import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta
import re

st.set_page_config(page_title="Dashboard AH4 Pro", layout="wide")
st.title("📊 Hệ Thống Dữ Liệu")

def clean_numeric(x):
    if pd.isna(x): return None
    x = str(x).strip()
    if x == "": return None
    try:
        matches = re.findall(r'\d+-\d+-\d+/([-+]?(?:\d+\.\d+|\d+))', x)
        if matches: return float(matches[-1])
    except: pass
    try:
        match = re.search(r'[-+]?(?:\d+\.\d+|\d+)', x.replace(',', '.'))
        if match: return float(match.group(0))
    except: pass
    return None

def process_data(file):
    try:
        df = pd.read_json(file)
    except: return pd.DataFrame()

    if 'Thời gian' in df.columns:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    else:
        return pd.DataFrame()
    
    skip_cols = ['Thời gian', '_id', 'STT', 'Tên khu', 'Trạng thái', 'Phương thức hoạt động', 'Người điều khiển', 'Bơm', 'Van', 'Ngưỡng tưới']
    for col in df.columns:
        if col not in skip_cols:
            df[col] = df[col].apply(clean_numeric)
            
    subset = ['Thời gian', 'STT'] if 'STT' in df.columns else ['Thời gian']
    df = df.drop_duplicates(subset=subset, keep='last')

    for col in df.columns:
        if col not in skip_cols and pd.api.types.is_numeric_dtype(df[col]):
            u_col = col.upper()
            max_val = df[col].max()
            if 'PH' in u_col and max_val > 14:
                df[col] = df[col] / (100 if max_val > 140 else 10)
            elif ('NHIỆT' in u_col or 'TEMP' in u_col) and max_val > 100:
                df[col] = df[col] / (100 if max_val >= 1000 else 10)
            elif ('ẨM' in u_col or 'HUMI' in u_col) and max_val > 100:
                df[col] = df[col] / (100 if max_val >= 1000 else 10)
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file đang xem:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # --- Sidebar ---
        st.sidebar.markdown("---")
        view_mode = st.sidebar.selectbox("Chế độ gom nhóm dữ liệu:", 
                                         ["Dữ liệu gốc (Dùng bước nhảy)", 
                                          "Trung bình theo Giờ", 
                                          "Trung bình theo Ngày"])

        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        
        st.sidebar.markdown("---")
        st.sidebar.header("📅 Lọc thời gian")
        c1, c2 = st.sidebar.columns(2)
        start_date = c1.date_input("Từ ngày", min_dt.date())
        end_date = c2.date_input("Đến ngày", max_dt.date())
        
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date) + timedelta(days=1) - timedelta(seconds=1)
        df_filtered = df[(df['Thời gian'] >= start_dt) & (df['Thời gian'] <= end_dt)].copy()

        if not df_filtered.empty:
            # --- Xử lý dữ liệu (Fix lỗi TypeError ở đây) ---
            if "Trung bình" in view_mode:
                freq = '1h' if "Giờ" in view_mode else '1D'
                # QUAN TRỌNG: Thêm numeric_only=True để không lỗi cột chữ
                df_plot = df_filtered.set_index('Thời gian').resample(freq).mean(numeric_only=True).reset_index()
                step = 1
            else:
                col_step, _ = st.columns([1, 2])
                step = col_step.select_slider("Bước nhảy (Độ mảnh):", options=[1, 2, 5, 10, 50, 100], value=1)
                df_plot = df_filtered.iloc[::step]

            num_cols = [c for c in df_plot.select_dtypes(include=['number']).columns if c not in ['STT', 'index']]
            valid_cols = [c for c in num_cols if not df_plot[c].dropna().empty]

            st.subheader(f"📊 Biểu đồ xu hướng ({view_mode})")
            selected_metrics = st.multiselect("Chọn thông số muốn vẽ:", valid_cols, default=valid_cols[:min(2, len(valid_cols))])

            if selected_metrics:
                num_plots = len(selected_metrics)
                fig = make_subplots(rows=num_plots, cols=1, shared_xaxes=True, vertical_spacing=0.05, subplot_titles=selected_metrics)
                
                for i, m in enumerate(selected_metrics):
                    p_data = df_plot[['Thời gian', m]].dropna()
                    shape = 'spline' if "Trung bình" in view_mode else 'linear'
                    fig.add_trace(go.Scatter(x=p_data['Thời gian'], y=p_data[m], mode='lines+markers', name=m, line=dict(shape=shape, width=2)), row=i+1, col=1)
                
                fig.update_layout(height=350 * num_plots, template="plotly_white", hovermode="x unified", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("🔍 Xem bảng dữ liệu chi tiết"):
                st.dataframe(df_plot, use_container_width=True)
        else:
            st.warning("⚠️ Không có dữ liệu trong khoảng thời gian đã chọn.")
else:
    st.info("Hãy tải file JSON lên sidebar để bắt đầu.")
