import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Dashboard AH4 Pro", layout="wide")
st.title("📊 Hệ Thống Phân Tích Dữ Liệu")

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        # Chuẩn hóa thời gian
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    
    # Chuyển đổi số
    for col in df.columns:
        if col not in ['Thời gian', '_id', 'Tên khu', 'Trạng thái', 'Người điều khiển']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Chuẩn hóa PH và Nhiệt độ
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
        # --- BỘ LỌC THỜI GIAN ---
        st.sidebar.header("📅 Bộ lọc thời gian")
        min_dt = df['Thời gian'].min()
        max_dt = df['Thời gian'].max()

        filter_type = st.sidebar.selectbox("Xem theo:", ["Tùy chỉnh", "Toàn bộ dữ liệu", "7 ngày qua", "Tháng này"])
        
        if filter_type == "Toàn bộ dữ liệu":
            start_date, end_date = min_dt, max_dt
        elif filter_type == "7 ngày qua":
            start_date, end_date = max_dt - timedelta(days=7), max_dt
        elif filter_type == "Tháng này":
            start_date, end_date = max_dt.replace(day=1), max_dt
        else:
            col1, col2 = st.sidebar.columns(2)
            start_date = pd.to_datetime(col1.date_input("Từ ngày", min_dt))
            end_date = pd.to_datetime(col2.date_input("Đến ngày", max_dt)) + timedelta(days=1)

        # Lọc dữ liệu
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)]

        # --- HIỂN THỊ THÔNG SỐ (SỬA LỖI N/A) ---
        st.subheader(f"📝 Thông số trong khoảng: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")
        
        if not df_filtered.empty:
            cols = st.columns(4)
            # Những cột quan trọng cần ưu tiên hiển thị
            metrics_to_show = ['Nhiệt Độ', 'Độ ẩm', 'PH', 'EC', 'N', 'P', 'K', 'tempKK', 'humiKK', 'Lưu lượng m2/h']
            valid_metrics = [m for m in metrics_to_show if m in df_filtered.columns]
            
            for idx, m in enumerate(valid_metrics):
                # Lấy giá trị hợp lệ cuối cùng (không phải NaN) trong khoảng đã lọc
                last_valid_val = df_filtered[m].dropna().iloc[-1] if not df_filtered[m].dropna().empty else None
                
                if last_valid_val is not None:
                    cols[idx % 4].metric(m, f"{last_valid_val:.2f}")
                else:
                    cols[idx % 4].metric(m, "N/A")
        else:
            st.error("❌ Không có dữ liệu trong mốc thời gian này. Vui lòng chọn mốc khác!")

        # --- VẼ BIỂU ĐỒ ĐƯỜNG ---
        if not df_filtered.empty:
            numeric_cols = df_filtered.select_dtypes(include=['number']).columns.tolist()
            numeric_cols = [c for c in numeric_cols if c not in ['STT']]
            
            selected_metrics = st.multiselect("Chọn thông số vẽ biểu đồ:", numeric_cols, default=numeric_cols[:2])
            
            if selected_metrics:
                fig = go.Figure()
                for metric in selected_metrics:
                    clean_df = df_filtered.dropna(subset=[metric])
                    fig.add_trace(go.Scatter(
                        x=clean_df['Thời gian'], y=clean_df[metric],
                        mode='lines+markers', name=metric,
                        line=dict(width=2), marker=dict(size=4)
                    ))
                fig.update_layout(hovermode="x unified", template="plotly_white", height=500)
                st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Xem bảng dữ liệu chi tiết"):
            st.dataframe(df_filtered)
else:
    st.info("👋 Hãy tải file JSON lên.")
