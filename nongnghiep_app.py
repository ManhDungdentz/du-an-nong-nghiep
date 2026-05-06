import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="CỘNG CỤ PHÂN TÍCH DỮ LIỆU", layout="wide")
st.title("📈 CỘNG CỤ PHÂN TÍCH DỮ LIỆU")

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        # Xử lý định dạng thời gian đặc biệt từ file của bạn
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        # Loại bỏ các dòng lỗi thời gian và sắp xếp để không bị rối đường kẻ
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    
    for col in df.columns:
        if col not in ['Thời gian', '_id', 'Tên khu', 'Trạng thái', 'Người điều khiển', 'Phương thức hoạt động']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Sửa đơn vị PH và Nhiệt độ nếu cần
    if 'PH' in df.columns and df['PH'].max() > 20: df['PH'] = df['PH'] / 100
    if 'Nhiệt Độ' in df.columns and df['Nhiệt Độ'].max() > 100: df['Nhiệt Độ'] = df['Nhiệt Độ'] / 100
            
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # --- BỘ LỌC THỜI GIAN THEO DỮ LIỆU THẬT ---
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        st.sidebar.info(f"Dữ liệu thực tế: \n{min_dt} -> {max_dt}")

        col1, col2 = st.sidebar.columns(2)
        start_date = pd.to_datetime(col1.date_input("Từ ngày", min_dt.date()))
        end_date = pd.to_datetime(col2.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)
        
        # Lọc dữ liệu theo khoảng thời gian đã chọn
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)]

        # --- HIỂN THỊ THÔNG SỐ (METRICS) ---
        if not df_filtered.empty:
            # Ưu tiên các cột quan trọng bao gồm AS (Ánh sáng)
            display_cols = ['Nhiệt Độ', 'Độ ẩm', 'AS', 'soil_ASKK', 'PH', 'EC', 'N', 'P', 'K']
            metrics_available = [m for m in display_cols if m in df_filtered.columns]
            
            st.subheader("📋 Giá trị đo được mới nhất")
            cols = st.columns(len(metrics_available) if len(metrics_available) < 5 else 4)
            for i, m in enumerate(metrics_available):
                valid_val = df_filtered[m].dropna()
                if not valid_val.empty:
                    val = valid_val.iloc[-1] # Lấy giá trị mới nhất
                    cols[i % 4].metric(label=m, value=f"{val:.2f}")

            # --- PHẦN VẼ BIỂU ĐỒ ĐƯỜNG (KHÔNG PHẢI CỘT) ---
            st.markdown("---")
            numeric_cols = df_filtered.select_dtypes(include=['number']).columns.tolist()
            draw_cols = [c for c in numeric_cols if c not in ['STT']]
            
            selected_metrics = st.multiselect("Chọn thông số vẽ biểu đồ:", draw_cols, default=draw_cols[:min(2, len(draw_cols))])
            
            if selected_metrics:
                fig = go.Figure()
                for metric in selected_metrics:
                    # Loại bỏ NaN để đường kẻ nối liền mạch, không bị rời rạc như cột
                    clean_df = df_filtered[['Thời gian', metric]].dropna()
                    if not clean_df.empty:
                        fig.add_trace(go.Scatter(
                            x=clean_df['Thời gian'], 
                            y=clean_df[metric],
                            mode='lines+markers', # ÉP BUỘC VẼ ĐƯỜNG VÀ ĐIỂM
                            name=metric,
                            line=dict(width=1.5), # Đường mảnh
                            marker=dict(size=4)    # Điểm nhỏ
                        ))
                
                fig.update_layout(
                    hovermode="x unified",
                    template="plotly_white",
                    xaxis=dict(showgrid=True, nticks=10),
                    yaxis=dict(showgrid=True),
                    height=600,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Không có dữ liệu trong khoảng này. Hãy chỉnh lịch ở sidebar!")
else:
    st.info("Kéo thả file JSON vào để bắt đầu.")
