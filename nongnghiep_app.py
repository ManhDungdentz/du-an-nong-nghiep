import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="CÔNG CỤ PHÂN TÍCH", layout="wide")
st.title("📈 CÔNG CỤ PHÂN TÍCH")

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        # 1. Chuẩn hóa thời gian
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian'])
        
        # 2. CHỐNG LỖI CỘT: Gộp nhóm các dữ liệu trùng giây và lấy trung bình
        # Điều này xóa bỏ việc một thời điểm có nhiều điểm dữ liệu gây ra vạch dọc
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
        # Lấy mốc thực tế
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        
        st.sidebar.header("📅 Lọc thời gian")
        col1, col2 = st.sidebar.columns(2)
        start_date = pd.to_datetime(col1.date_input("Từ ngày", min_dt.date()))
        end_date = pd.to_datetime(col2.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)
        
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)]

        if not df_filtered.empty:
            # --- HIỂN THỊ THÔNG SỐ (METRICS) ---
            st.subheader("📋 Thông số mới nhất")
            important = ['Nhiệt Độ', 'Độ ẩm', 'AS', 'soil_ASKK', 'PH', 'EC', 'N', 'P', 'K']
            metrics_avail = [m for m in important if m in df_filtered.columns]
            
            cols = st.columns(4)
            for i, m in enumerate(metrics_avail):
                val = df_filtered[m].dropna()
                if not val.empty:
                    cols[i % 4].metric(label=m, value=f"{val.iloc[-1]:.2f}")

            # --- VẼ BIỂU ĐỒ ĐƯỜNG (FIX CỘT) --
            st.markdown("---")
            draw_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT']]
            selected_metrics = st.multiselect("Chọn thông số:", draw_cols, default=metrics_avail[:2])
            
            if selected_metrics:
                fig = go.Figure()
                for metric in selected_metrics:
                    # Lấy dữ liệu sạch
                    plot_data = df_filtered[['Thời gian', metric]].dropna()
                    
                    if not plot_data.empty:
                        fig.add_trace(go.Scatter(
                            x=plot_data['Thời gian'], 
                            y=plot_data[metric],
                            mode='lines',           # CHỈ VẼ ĐƯỜNG
                            name=metric,
                            connectgaps=True,      # NỐI KHOẢNG TRỐNG
                            line=dict(width=2, shape='linear') # Đường thẳng nối các điểm
                        ))
                
                fig.update_layout(
                    hovermode="x unified",
                    template="plotly_white",
                    height=600,
                    xaxis=dict(showgrid=True, title="Thời gian"),
                    yaxis=dict(showgrid=True, title="Giá trị")
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Không có dữ liệu trong khoảng này.")
else:
    st.info("Kéo thả file vào sidebar.")
