import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. Cấu hình trang
st.set_page_config(page_title="Dashboard AH4 Pro", layout="wide")

st.title("📊 Hệ Thống Phân Tích Dữ Liệu Nông Nghiệp")

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        # Chuẩn hóa thời gian và sắp xếp
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    
    # Chuyển đổi số
    for col in df.columns:
        if col not in ['Thời gian', '_id', 'Tên khu', 'Trạng thái', 'Người điều khiển']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Chuẩn hóa PH và Nhiệt độ (chia 100 nếu là số nguyên lớn)
    for col in ['PH', 'Nhiệt Độ']:
        if col in df.columns and df[col].max() > 50:
            df[col] = df[col] / 100
            
    return df

# 2. Tải và chọn file
uploaded_files = st.sidebar.file_uploader("Tải lên file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file dữ liệu:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # --- BỘ LỌC THỜI GIAN THEO NGÀY/TUẦN/THÁNG/NĂM ---
        st.sidebar.header("📅 Bộ lọc thời gian")
        filter_type = st.sidebar.radio("Xem theo:", ["Tùy chọn", "Hôm nay", "7 ngày qua", "Tháng này", "Năm nay"])
        
        max_dt = df['Thời gian'].max()
        min_dt = df['Thời gian'].min()

        if filter_type == "Hôm nay":
            start_date = max_dt.replace(hour=0, minute=0, second=0)
            end_date = max_dt
        elif filter_type == "7 ngày qua":
            start_date = max_dt - timedelta(days=7)
            end_date = max_dt
        elif filter_type == "Tháng này":
            start_date = max_dt.replace(day=1, hour=0, minute=0)
            end_date = max_dt
        elif filter_type == "Năm nay":
            start_date = max_dt.replace(month=1, day=1, hour=0, minute=0)
            end_date = max_dt
        else:
            # Tùy chọn thủ công bằng lịch
            col_d1, col_d2 = st.sidebar.columns(2)
            start_date = col_d1.date_input("Từ ngày", min_dt)
            end_date = col_d2.date_input("Đến ngày", max_dt)
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date) + timedelta(days=1)

        # Lọc dữ liệu theo thời gian
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)]

        # --- HIỂN THỊ THÔNG SỐ CHI TIẾT TRƯỚC KHI VẼ ---
        st.subheader("📝 Thông số đo được (Mới nhất trong khoảng lọc)")
        if not df_filtered.empty:
            latest = df_filtered.iloc[-1]
            cols = st.columns(4)
            
            # Hiển thị linh hoạt các thông số hiện có trong file
            idx = 0
            important_metrics = ['Nhiệt Độ', 'Độ ẩm', 'PH', 'EC', 'N', 'P', 'K', 'tempKK', 'humiKK']
            for m in important_metrics:
                if m in df_filtered.columns:
                    val = latest[m]
                    cols[idx % 4].metric(m, f"{val:.2f}" if pd.notnull(val) else "N/A")
                    idx += 1
        else:
            st.warning("Không có dữ liệu trong khoảng thời gian này.")

        # --- VẼ BIỂU ĐỒ ĐƯỜNG (LINE CHART) ---
        st.markdown("---")
        numeric_cols = df_filtered.select_dtypes(include=['number']).columns.tolist()
        numeric_cols = [c for c in numeric_cols if c not in ['STT']]

        if numeric_cols:
            selected_metrics = st.multiselect("Chọn các thông số muốn vẽ biểu đồ:", numeric_cols, default=numeric_cols[:2])
            
            if selected_metrics:
                fig = go.Figure()
                for metric in selected_metrics:
                    clean_df = df_filtered.dropna(subset=[metric])
                    fig.add_trace(go.Scatter(
                        x=clean_df['Thời gian'],
                        y=clean_df[metric],
                        mode='lines+markers', # ĐÚNG KIỂU HÌNH 2: ĐƯỜNG + CHẤM
                        name=metric,
                        line=dict(width=2.5),
                        marker=dict(size=7, symbol='circle')
                    ))

                fig.update_layout(
                    title="Biểu đồ diễn biến thông số",
                    xaxis_title="Thời gian",
                    yaxis_title="Giá trị",
                    hovermode="x unified",
                    template="plotly_white",
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Xem bảng dữ liệu chi tiết"):
            st.dataframe(df_filtered)
else:
    st.info("👋 Chào mừng! Hãy tải file JSON lên để bắt đầu xem thông số và biểu đồ.")
