import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Hệ Thống Phân Tích Dữ Liệu", layout="wide")
st.title("📊 Hệ Thống Phân Tích Dữ Liệu ")

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        # Chuẩn hóa thời gian từ định dạng file
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    
    # Chuyển đổi tất cả cột số, thay "" bằng NaN
    for col in df.columns:
        if col not in ['Thời gian', '_id', 'Tên khu', 'Trạng thái', 'Người điều khiển', 'Phương thức hoạt động']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Chuẩn hóa PH và Nhiệt độ nếu dữ liệu bị nhân 100
    if 'PH' in df.columns and df['PH'].max() > 50:
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
        # --- BỘ LỌC THỜI GIAN THÔNG MINH ---
        st.sidebar.header("📅 Bộ lọc thời gian")
        min_dt = df['Thời gian'].min()
        max_dt = df['Thời gian'].max()

        # Hiển thị mốc dữ liệu có sẵn trong file để người dùng biết
        st.sidebar.info(f"Dữ liệu từ: {min_dt.strftime('%d/%m/%Y')} \nĐến: {max_dt.strftime('%d/%m/%Y')}")

        filter_type = st.sidebar.selectbox("Lọc nhanh:", 
            ["Toàn bộ dữ liệu", "Tùy chỉnh ngày", "7 ngày cuối của dữ liệu", "Tháng cuối của dữ liệu"])
        
        if filter_type == "Toàn bộ dữ liệu":
            start_date, end_date = min_dt, max_dt
        elif filter_type == "7 ngày cuối của dữ liệu":
            start_date, end_date = max_dt - timedelta(days=7), max_dt
        elif filter_type == "Tháng cuối của dữ liệu":
            start_date, end_date = max_dt - timedelta(days=30), max_dt
        else:
            col1, col2 = st.sidebar.columns(2)
            # Mặc định ngày bắt đầu là ngày nhỏ nhất trong file
            start_date = pd.to_datetime(col1.date_input("Từ ngày", min_dt))
            end_date = pd.to_datetime(col2.date_input("Đến ngày", max_dt)) + timedelta(days=1)

        # Áp dụng bộ lọc
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)]

        # --- HIỂN THỊ THÔNG SỐ (METRICS) ---
        st.subheader("📝 Thông số đo được")
        
        if not df_filtered.empty:
            cols = st.columns(4)
            # Danh sách các cột muốn hiển thị thông số nhanh
            metrics_list = ['Nhiệt Độ', 'Độ ẩm', 'PH', 'EC', 'N', 'P', 'K', 'tempKK', 'humiKK', 'Lưu lượng m2/h']
            
            # Lọc ra những cột thực sự có trong file
            available_metrics = [m for m in metrics_list if m in df_filtered.columns]
            
            for idx, m in enumerate(available_metrics):
                # Tìm giá trị cuối cùng KHÔNG RỖNG trong cột đó
                valid_series = df_filtered[m].dropna()
                if not valid_series.empty:
                    last_val = valid_series.iloc[-1]
                    cols[idx % 4].metric(label=m, value=f"{last_val:.2f}")
                else:
                    cols[idx % 4].metric(label=m, value="N/A")
        else:
            st.error(f"⚠️ Không có dữ liệu từ {start_date.date()} đến {end_date.date()}. Hãy chọn mốc thời gian khác!")

        # --- BIỂU ĐỒ ĐƯỜNG NỐI LIỀN ---
        if not df_filtered.empty:
            st.markdown("---")
            numeric_cols = df_filtered.select_dtypes(include=['number']).columns.tolist()
            # Bỏ STT và các cột ID khỏi danh sách vẽ
            draw_cols = [c for c in numeric_cols if c not in ['STT']]
            
            selected_metrics = st.multiselect("Chọn thông số vẽ biểu đồ:", draw_cols, default=draw_cols[:min(2, len(draw_cols))])
            
            if selected_metrics:
                fig = go.Figure()
                for metric in selected_metrics:
                    # Loại bỏ giá trị rỗng để đường kẻ được nối liền (không bị đứt đoạn)
                    clean_df = df_filtered[['Thời gian', metric]].dropna()
                    if not clean_df.empty:
                        fig.add_trace(go.Scatter(
                            x=clean_df['Thời gian'], 
                            y=clean_df[metric],
                            mode='lines+markers', 
                            name=metric,
                            line=dict(width=2),
                            marker=dict(size=4)
                        ))
                
                fig.update_layout(
                    hovermode="x unified", 
                    template="plotly_white", 
                    height=500,
                    xaxis_title="Thời gian",
                    yaxis_title="Giá trị"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("🔍 Xem bảng dữ liệu chi tiết"):
            st.dataframe(df_filtered)
else:
    st.info("👋 Chào bạn! Hãy tải các file JSON (Quan trắc, Lịch sử...) vào để bắt đầu.")
