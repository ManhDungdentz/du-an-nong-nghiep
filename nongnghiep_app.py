import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots # THÊM THƯ VIỆN NÀY ĐỂ CHIA TẦNG BIỂU ĐỒ
from datetime import datetime, timedelta

st.set_page_config(page_title="Dashboard AH4 Pro", layout="wide")
st.title("📊 Hệ Thống Dữ Liệu (Biểu Đồ Tầng Chuyên Nghiệp)")

def process_data(file):
    try:
        df = pd.read_json(file)
    except: return pd.DataFrame()

    if 'Thời gian' in df.columns:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    else:
        return pd.DataFrame()
    
    for col in df.columns:
        if col != 'Thời gian':
            cleaned_str = df[col].astype(str).str.replace(',', '.')
            extracted_num = cleaned_str.str.extract(r'([-+]?(?:\d+\.\d+|\d+))')[0]
            df[col] = pd.to_numeric(extracted_num, errors='coerce')
            
    df = df.groupby('Thời gian').mean(numeric_only=True).reset_index()

    for col in df.columns:
        u_col = col.upper()
        if 'PH' in u_col and df[col].max() > 20: df[col] = df[col] / 100
        if ('NHIỆT' in u_col or 'TEMP' in u_col) and df[col].max() > 100: df[col] = df[col] / 100
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file đang xem:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        st.sidebar.header("📅 Lọc thời gian")
        start_date = pd.to_datetime(st.sidebar.date_input("Từ ngày", min_dt.date()))
        end_date = pd.to_datetime(st.sidebar.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)
        
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)].copy()

        if not df_filtered.empty:
            num_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT', 'index']]
            
            st.subheader("📋 Thông số tìm thấy")
            if num_cols:
                m_cols = st.columns(4)
                for i, col_name in enumerate(num_cols[:12]):
                    val = df_filtered[col_name].dropna()
                    if not val.empty:
                        m_cols[i % 4].metric(label=col_name, value=f"{val.iloc[-1]:.2f}")

            st.markdown("---")
            c1, c2 = st.columns([1, 2])
            chart_type = c1.radio("Kiểu vẽ:", ["Đường (Line)", "Cột (Bar)"], horizontal=True)
            step = c1.select_slider("Độ mảnh (Bước nhảy):", options=[1, 2, 5, 10, 50], value=1)
            
            selected_metrics = c2.multiselect("Bấm vào đây để THÊM thông số vẽ:", num_cols, default=num_cols[:min(3, len(num_cols))])
            
            if selected_metrics:
                # --- CHIA TẦNG BIỂU ĐỒ (SỬA LỖI ĐÈ BẸP NHAU) ---
                num_plots = len(selected_metrics)
                # Tạo khung chứa nhiều biểu đồ xếp dọc
                fig = make_subplots(rows=num_plots, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.05, subplot_titles=selected_metrics)
                
                display_df = df_filtered.iloc[::step]
                
                for i, m in enumerate(selected_metrics):
                    p_data = display_df[['Thời gian', m]].dropna()
                    
                    if not p_data.empty:
                        if "Đường" in chart_type:
                            fig.add_trace(go.Scatter(
                                x=p_data['Thời gian'], y
