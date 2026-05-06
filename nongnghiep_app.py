import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="CỘNG CỤ XEM DỮ LIỆU", layout="wide")
st.title("📈CỘNG CỤ XEM DỮ LIỆU ")

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        # Chuẩn hóa thời gian và sắp xếp cực kỳ quan trọng
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    
    # Chuyển đổi dữ liệu số
    for col in df.columns:
        if col not in ['Thời gian', '_id', 'Tên khu', 'Trạng thái', 'Người điều khiển']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Sửa đơn vị PH và Nhiệt độ
    if 'PH' in df.columns and df['PH'].max() > 20: df['PH'] = df['PH'] / 100
    if 'Nhiệt Độ' in df.columns and df['Nhiệt Độ'].max() > 100: df['Nhiệt Độ'] = df['Nhiệt Độ'] / 100
            
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # Lấy mốc thời gian trong file
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        
        st.sidebar.header("📅 Lọc thời gian")
        col1, col2 = st.sidebar.columns(2)
        start_date = pd.to_datetime(col1.date_input("Từ ngày", min_dt.date()))
        end_date = pd.to_datetime(col2.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)
        
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)]

        # --- HIỂN THỊ THÔNG SỐ (METRICS) ---
        if not df_filtered.empty:
            st.subheader("📋 Thông số mới nhất")
            important = ['Nhiệt Độ', 'Độ ẩm', 'AS', 'soil_ASKK', 'PH', 'EC', 'N', 'P', 'K']
            metrics_avail = [m for m in important if m in df_filtered.columns]
            
            cols = st.columns(min(len(metrics_avail), 4))
            for i, m in enumerate(metrics_avail):
                val = df_filtered[m].dropna()
                if not val.empty:
                    cols[i % 4].metric(label=m, value=f"{val.iloc[-1]:.2f}")

            # --- VẼ BIỂU ĐỒ ĐƯỜNG (KHÔNG CÓ CỘT, KHÔNG CÓ ĐIỂM RỜI) ---
            st.markdown("---")
            draw_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT']]
            selected_metrics = st.multiselect("Chọn thông số vẽ:", draw_cols, default=metrics_avail[:2])
            
            if selected_metrics:
                fig = go.Figure()
                for metric in selected_metrics:
                    # Lấy dữ liệu của riêng cột đó, bỏ qua dòng trống
                    plot_data = df_filtered[['Thời gian', metric]].dropna()
                    
                    if not plot_data.empty:
                        fig.add_trace(go.Scatter(
                            x=plot_data['Thời gian'], 
                            y=plot_data[metric],
                            mode='lines',            # CHỈ VẼ ĐƯỜNG (Giống hình mẫu bạn gửi)
                            name=metric,
                            connectgaps=True,       # Nối các điểm bị thiếu dữ liệu ở giữa
                            line=dict(width=2)       # Độ dày đường kẻ mảnh vừa phải
                        ))
                
                fig.update_layout(
                    hovermode="x unified",
                    template="plotly_white",
                    height=600,
                    xaxis=dict(showgrid=True, title="Thời gian"),
                    yaxis=dict(showgrid=True, title="Giá trị"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right")
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Khoảng thời gian này không có dữ liệu.")
else:
    st.info("Kéo thả file vào sidebar để bắt đầu.")
