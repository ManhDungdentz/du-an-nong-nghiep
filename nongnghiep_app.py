import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Dashboard AH4 Pro", layout="wide")
st.title("📊 Hệ Thống Phân Tích Dữ Liệu ")

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        # Chuẩn hóa thời gian
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian'])
        # Gộp nhóm để tránh lỗi trùng lặp gây ra vạch dọc
        df = df.groupby('Thời gian').mean(numeric_only=True).reset_index()
        df = df.sort_values('Thời gian')
    
    # Chuẩn hóa đơn vị
    if 'PH' in df.columns and df['PH'].max() > 20: df['PH'] = df['PH'] / 100
    if 'Nhiệt Độ' in df.columns and df['Nhiệt Độ'].max() > 100: df['Nhiệt Độ'] = df['Nhiệt Độ'] / 100
            
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # --- BỘ LỌC THỜI GIAN ---
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        st.sidebar.header("📅 Lọc thời gian")
        col1, col2 = st.sidebar.columns(2)
        start_date = pd.to_datetime(col1.date_input("Từ ngày", min_dt.date()))
        end_date = pd.to_datetime(col2.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)
        
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)]

        if not df_filtered.empty:
            # --- THÔNG SỐ NHANH ---
            st.subheader("📋 Thông số mới nhất")
            important = ['Nhiệt Độ', 'Độ ẩm', 'AS', 'soil_ASKK', 'PH', 'EC', 'N', 'P', 'K']
            metrics_avail = [m for m in important if m in df_filtered.columns]
            
            cols = st.columns(4)
            for i, m in enumerate(metrics_avail):
                val = df_filtered[m].dropna()
                if not val.empty:
                    cols[i % 4].metric(label=m, value=f"{val.iloc[-1]:.2f}")

            # --- CHỌN LOẠI BIỂU ĐỒ ---
            st.markdown("---")
            st.subheader("📈 Tùy chỉnh biểu đồ")
            c1, c2 = st.columns([1, 2])
            chart_type = c1.selectbox("Chọn loại biểu đồ:", ["Biểu đồ Đường (Line)", "Biểu đồ Cột (Bar)"])
            
            numeric_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT']]
            selected_metrics = c2.multiselect("Chọn thông số vẽ:", numeric_cols, default=metrics_avail[:2] if metrics_avail else numeric_cols[:1])
            
            if selected_metrics:
                fig = go.Figure()
                for metric in selected_metrics:
                    plot_data = df_filtered[['Thời gian', metric]].dropna()
                    if not plot_data.empty:
                        if chart_type == "Biểu đồ Đường (Line)":
                            fig.add_trace(go.Scatter(
                                x=plot_data['Thời gian'], y=plot_data[metric],
                                mode='lines', name=metric, connectgaps=True, line=dict(width=2.5)
                            ))
                        else:
                            fig.add_trace(go.Bar(
                                x=plot_data['Thời gian'], y=plot_data[metric], name=metric
                            ))
                
                fig.update_layout(hovermode="x unified", template="plotly_white", height=500)
                st.plotly_chart(fig, use_container_width=True)

            # --- BẢNG DỮ LIỆU HIỆN LUÔN ---
            st.markdown("---")
            st.subheader("🔍 Chi tiết bảng dữ liệu")
            st.dataframe(df_filtered, use_container_width=True)
        else:
            st.warning("Khoảng thời gian này không có dữ liệu.")
else:
    st.info("Kéo thả file vào sidebar để bắt đầu.")
