import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="cộng cụ phân tích dữ liệu", layout="wide")
st.title("cộng cụ phân tích dữ liệu")

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    
    # Chuyển đổi dữ liệu số
    for col in df.columns:
        if col not in ['Thời gian', '_id', 'Tên khu', 'Trạng thái', 'Người điều khiển', 'Phương thức hoạt động']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Chuẩn hóa đơn vị (pH chia 100, Nhiệt độ chia 100 nếu là số nguyên lớn)
    if 'PH' in df.columns and df['PH'].max() > 20:
        df['PH'] = df['PH'] / 100
    if 'Nhiệt Độ' in df.columns and df['Nhiệt Độ'].max() > 100:
        df['Nhiệt Độ'] = df['Nhiệt Độ'] / 100
            
    return df

uploaded_files = st.sidebar.file_uploader("Tải lên file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file dữ liệu:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # --- TÍNH TOÁN KHOẢNG THỜI GIAN THỰC TẾ TRONG FILE ---
        min_dt = df['Thời gian'].min()
        max_dt = df['Thời gian'].max()

        st.sidebar.header("📅 Bộ lọc thời gian")
        st.sidebar.info(f"Dữ liệu có từ: {min_dt.strftime('%d/%m/%Y')}\nĐến: {max_dt.strftime('%d/%m/%Y')}")

        # Cho phép người dùng chọn khoảng bằng Calendar, mặc định lấy theo mốc trong file
        col1, col2 = st.sidebar.columns(2)
        start_date = pd.to_datetime(col1.date_input("Từ ngày", min_dt.date()))
        end_date = pd.to_datetime(col2.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)

        # Lọc dữ liệu
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)]

        # --- HIỂN THỊ THÔNG SỐ CHI TIẾT (METRICS) ---
        st.subheader("📋 Thông số hiện tại (Giá trị mới nhất)")
        
        if not df_filtered.empty:
            # Ưu tiên các cột quan trọng bao gồm AS (Ánh sáng)
            important_cols = {
                'Nhiệt Độ': '🌡️ Nhiệt độ',
                'Độ ẩm': '💧 Độ ẩm',
                'AS': '☀️ Ánh sáng',
                'soil_ASKK': '☀️ Ánh sáng (KK)',
                'PH': '🧪 pH',
                'EC': '⚡ EC',
                'tempKK': '🌡️ Nhiệt độ KK',
                'humiKK': '💧 Độ ẩm KK'
            }
            
            # Tạo các ô hiển thị số
            metrics_to_show = [c for c in important_cols.keys() if c in df_filtered.columns]
            if metrics_to_show:
                cols = st.columns(len(metrics_to_show))
                for i, m in enumerate(metrics_to_show):
                    # Lấy giá trị cuối cùng không bị rỗng
                    valid_val = df_filtered[m].dropna()
                    if not valid_val.empty:
                        val = valid_val.iloc[-1]
                        cols[i].metric(label=important_cols[m], value=f"{val:.2f}")
                    else:
                        cols[i].metric(label=important_cols[m], value="N/A")
            
            # --- VẼ BIỂU ĐỒ ĐƯỜNG Nối Liền ---
            st.markdown("---")
            numeric_cols = df_filtered.select_dtypes(include=['number']).columns.tolist()
            draw_cols = [c for c in numeric_cols if c not in ['STT']]
            
            selected_metrics = st.multiselect("Chọn thông số vẽ biểu đồ:", draw_cols, default=metrics_to_show[:2])
            
            if selected_metrics:
                fig = go.Figure()
                for metric in selected_metrics:
                    clean_df = df_filtered[['Thời gian', metric]].dropna()
                    if not clean_df.empty:
                        fig.add_trace(go.Scatter(
                            x=clean_df['Thời gian'], 
                            y=clean_df[metric],
                            mode='lines+markers', 
                            name=metric,
                            line=dict(width=2.5),
                            marker=dict(size=6)
                        ))
                
                fig.update_layout(
                    hovermode="x unified",
                    template="plotly_white",
                    height=550,
                    xaxis_title="Thời gian",
                    yaxis_title="Giá trị"
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"Chưa có dữ liệu trong khoảng từ {start_date.date()} đến {end_date.date()}. Vui lòng chỉnh lại lịch ở bên trái.")

        with st.expander("🔍 Chi tiết bảng dữ liệu"):
            st.dataframe(df_filtered)
else:
    st.info("👋 Hãy tải các file JSON lên để hệ thống phân tích ánh sáng và cảm biến.")
