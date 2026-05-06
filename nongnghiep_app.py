import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Cấu hình trang
st.set_page_config(page_title="Hệ thống Dashboard AH4", layout="wide")

st.title("📈 CỘNG CỤ XỬ LÝ DỮ LIỆU")

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        # Chuẩn hóa thời gian: thay '-' bằng ':' để format chuẩn YYYY-MM-DD HH:MM:SS
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        # Sắp xếp thời gian là bước QUAN TRỌNG NHẤT để ra biểu đồ đường
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    
    # Ép kiểu số cho tất cả cột dữ liệu, lỗi sẽ thành NaN
    for col in df.columns:
        if col not in ['Thời gian', '_id', 'Tên khu', 'Người điều khiển', 'Trạng thái', 'Phương thức hoạt động']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Xử lý PH (chia 100 nếu dữ liệu là số nguyên)
    if 'PH' in df.columns and df['PH'].max() > 20:
        df['PH'] = df['PH'] / 100
        
    return df

# 2. Sidebar
uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("Chọn file hiển thị:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # --- BỘ LỌC THỜI GIAN ---
        st.sidebar.markdown("---")
        min_dt = df['Thời gian'].min().to_pydatetime()
        max_dt = df['Thời gian'].max().to_pydatetime()
        
        start_time, end_time = st.sidebar.slider(
            "Lọc mốc thời gian:",
            min_value=min_dt, max_value=max_dt,
            value=(min_dt, max_dt),
            format="DD/MM HH:mm"
        )
        
        mask = (df['Thời gian'] >= start_time) & (df['Thời gian'] <= end_time)
        df_filtered = df.loc[mask]

        # --- VẼ BIỂU ĐỒ ĐƯỜNG ---
        numeric_cols = df_filtered.select_dtypes(include=['number']).columns.tolist()
        numeric_cols = [c for c in numeric_cols if c not in ['STT']]

        if numeric_cols:
            selected_metrics = st.multiselect("Chọn thông số vẽ đường:", numeric_cols, default=numeric_cols[:min(2, len(numeric_cols))])
            
            if selected_metrics:
                # Dùng go.Figure để kiểm soát đường nối tốt hơn px.line
                fig = go.Figure()
                
                for metric in selected_metrics:
                    # Loại bỏ các giá trị NaN để đường không bị đứt
                    clean_df = df_filtered.dropna(subset=[metric])
                    
                    fig.add_trace(go.Scatter(
                        x=clean_df['Thời gian'],
                        y=clean_df[metric],
                        mode='lines+markers', # ĐƯỜNG + NỐT TRÒN giống hình 2
                        name=metric,
                        line=dict(width=2),
                        marker=dict(size=6)
                    ))

                fig.update_layout(
                    title=f"Biểu đồ diễn biến mốc: {start_time.strftime('%d/%m')} - {end_time.strftime('%d/%m')}",
                    xaxis_title="Thời gian",
                    yaxis_title="Giá trị",
                    hovermode="x unified",
                    template="plotly_white",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df_filtered)
else:
    st.info("Kéo thả file JSON vào để xem biểu đồ đường.")
