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
        # Chế độ xem biểu đồ
        st.sidebar.markdown("---")
        view_mode = st.sidebar.selectbox("Chế độ hiển thị:", ["Gốc (Dùng bước nhảy)", "Trung bình theo Giờ", "Trung bình theo Ngày"])

        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        
        st.sidebar.markdown("---")
        st.sidebar.header("🗓️ Thống kê")
        df_temp = df.copy()
        df_temp['Tháng'] = df_temp['Thời gian'].dt.strftime('%m/%Y')
        thong_ke = df_temp['Tháng'].value_counts().reset_index()
        thong_ke.columns = ['Tháng', 'Số lượt đo']
        st.sidebar.dataframe(thong_ke, hide_index=True)

        st.sidebar.header("📅 Lọc thời gian")
        c1, c2 = st.sidebar.columns(2)
        start_date = c1.date_input("Từ ngày", min_dt.date())
        end_date = c2.date_input("Đến ngày", max_dt.date())
        
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date) + timedelta(days=1) - timedelta(seconds=1)
        df_filtered = df[(df['Thời gian'] >= start_dt) & (df['Thời gian'] <= end_dt)].copy()

        if not df_filtered.empty:
            st.subheader(f"📋 Dữ liệu ({view_mode})")
            
            # --- Xử lý dữ liệu theo chế độ xem ---
            if view_mode == "Trung bình theo Giờ":
                df_plot = df_filtered.set_index('Thời gian').resample('1h').mean().reset_index()
                step = 1 # Không dùng bước nhảy khi đã lấy trung bình
            elif view_mode == "Trung bình theo Ngày":
                df_plot = df_filtered.set_index('Thời gian').resample('1D').mean().reset_index()
                step = 1
            else:
                # Chế độ Gốc: Hiện thanh Bước nhảy (Độ mảnh)
                col_step, _ = st.columns([1, 2])
                step = col_step.select_slider("Bước nhảy (Độ mảnh):", options=[1, 2, 5, 10, 50], value=1)
                df_plot = df_filtered.iloc[::step]

            num_cols = [c for c in df_plot.select_dtypes(include=['number']).columns if c not in ['STT', 'index']]
            valid_cols = [c for c in num_cols if not df_plot[c].dropna().empty]

            selected_metrics = st.multiselect("Bấm để chọn thông số vẽ:", valid_cols, default=valid_cols[:min(2, len(valid_cols))])

            if selected_metrics:
                num_plots = len(selected_metrics)
                fig = make_subplots(rows=num_plots, cols=1, shared_xaxes=True, vertical_spacing=0.05, subplot_titles=selected_metrics)
                
                for i, m in enumerate(selected_metrics):
                    p_data = df_plot[['Thời gian', m]].dropna()
                    # Dùng spline cho đẹp ở chế độ trung bình, linear cho chế độ gốc
                    line_shape = 'spline' if "Trung bình" in view_mode else 'linear'
                    fig.add_trace(go.Scatter(x=p_data['Thời gian'], y=p_data[m], mode='lines+markers', name=m, line=dict(shape=line_shape)), row=i+1, col=1)
                
                fig.update_layout(height=300 * num_plots, template="plotly_white", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("🔍 Xem bảng dữ liệu"):
                st.dataframe(df_plot, use_container_width=True)
else:
    st.info("Hãy tải file JSON lên sidebar.")
