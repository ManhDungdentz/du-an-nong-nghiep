import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import timedelta
import re

st.set_page_config(page_title="Dashboard AH4 Pro", layout="wide")
st.title("📊 Hệ Thống Dữ Liệu Tổng Hợp")

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
    else: return pd.DataFrame()
    
    skip_cols = ['Thời gian', '_id', 'STT', 'Tên khu', 'Trạng thái', 'Phương thức hoạt động', 'Người điều khiển', 'Bơm', 'Van', 'Ngưỡng tưới']
    for col in df.columns:
        if col not in skip_cols:
            df[col] = df[col].apply(clean_numeric)
            
    df = df.drop_duplicates(subset=['Thời gian', 'STT'] if 'STT' in df.columns else ['Thời gian'], keep='last')

    for col in df.columns:
        if col not in skip_cols and pd.api.types.is_numeric_dtype(df[col]):
            u_col = col.upper()
            max_val = df[col].max()
            if 'PH' in u_col and max_val > 14: df[col] = df[col] / (100 if max_val > 140 else 10)
            elif any(k in u_col for k in ['NHIỆT', 'TEMP', 'ẨM', 'HUMI']) and max_val > 100:
                df[col] = df[col] / (100 if max_val >= 1000 else 10)
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # --- BẢNG THỐNG KÊ ---
        st.sidebar.markdown("---")
        df['Tháng_năm'] = df['Thời gian'].dt.strftime('%m/%Y')
        st.sidebar.subheader("🗓️ Thống kê tháng")
        st.sidebar.dataframe(df['Tháng_năm'].value_counts().reset_index().rename(columns={'index':'Tháng', 'Tháng_năm':'Lượt'}), hide_index=True)

        # --- BỘ LỌC TỔNG HỢP (GOM VÀO 1 CHỖ) ---
        st.sidebar.markdown("---")
        st.sidebar.header("⚙️ Cấu hình hiển thị")
        
        # 1. Chọn kiểu dữ liệu
        data_type = st.sidebar.radio("Kiểu dữ liệu:", ["Dữ liệu thô", "Dữ liệu trung bình"], horizontal=True)
        
        # 2. Chọn mức độ gộp (Resample)
        group_options = {
            "Không gộp": None,
            "Theo Giờ": "1H",
            "Theo Ngày": "1D",
            "Theo Tuần": "1W",
            "Theo Tháng": "1M"
        }
        group_by = st.sidebar.selectbox("Gộp dữ liệu theo:", list(group_options.keys()), index=0 if data_type=="Dữ liệu thô" else 2)
        
        # 3. Lọc thời gian
        st.sidebar.markdown("---")
        filter_mode = st.sidebar.radio("Lọc theo:", ["Khoảng ngày", "Chọn tháng nhanh"], horizontal=True)
        if filter_mode == "Khoảng ngày":
            c1, c2 = st.sidebar.columns(2)
            start_dt = pd.to_datetime(c1.date_input("Từ", df['Thời gian'].min().date()))
            end_dt = pd.to_datetime(c2.date_input("Đến", df['Thời gian'].max().date())) + timedelta(days=1)
            df_filtered = df[(df['Thời gian'] >= start_dt) & (df['Thời gian'] < end_dt)].copy()
        else:
            sel_months = st.sidebar.multiselect("Chọn tháng:", df['Tháng_năm'].unique(), default=df['Tháng_năm'].unique()[-1])
            df_filtered = df[df['Tháng_năm'].isin(sel_months)].copy()

        # 4. Lọc STT
        if 'STT' in df_filtered.columns and len(df_filtered['STT'].unique()) > 1:
            sel_stt = st.sidebar.selectbox("📍 Trạm (STT):", ["Tất cả"] + sorted(df_filtered['STT'].unique().astype(str).tolist()))
            if sel_stt != "Tất cả":
                df_filtered = df_filtered[df_filtered['STT'].astype(str) == sel_stt]

        if not df_filtered.empty:
            # --- XỬ LÝ DỮ LIỆU BIỂU ĐỒ ---
            freq = group_options[group_by]
            if freq:
                # Gộp trung bình
                df_plot = df_filtered.set_index('Thời gian').resample(freq).mean(numeric_only=True).reset_index()
            else:
                # Dùng bước nhảy cho dữ liệu thô
                step = st.select_slider("Độ mảnh dữ liệu thô:", options=[1, 2, 5, 10, 50, 100], value=1)
                df_plot = df_filtered.iloc[::step]

            # --- VẼ BIỂU ĐỒ ---
            num_cols = [c for c in df_plot.select_dtypes(include=['number']).columns if c not in ['STT', 'index']]
            metrics = st.multiselect("Thông số vẽ:", num_cols, default=num_cols[:2])
            
            if metrics:
                fig = make_subplots(rows=len(metrics), cols=1, shared_xaxes=True, vertical_spacing=0.05, subplot_titles=metrics)
                for i, m in enumerate(metrics):
                    p_data = df_plot[['Thời gian', m]].dropna()
                    fig.add_trace(go.Scatter(
                        x=p_data['Thời gian'], y=p_data[m], 
                        mode='lines+markers' if freq else 'lines',
                        name=m, line=dict(shape='spline' if data_type=="Dữ liệu trung bình" else 'linear', width=2)
                    ), row=i+1, col=1)
                
                fig.update_layout(height=300*len(metrics), template="plotly_white", hovermode="x unified", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("🔍 Chi tiết bảng dữ liệu"):
                st.dataframe(df_plot, use_container_width=True)
        else:
            st.warning("Không có dữ liệu trong khoảng này.")
else:
    st.info("Vui lòng tải file JSON để bắt đầu.")
