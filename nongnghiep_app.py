import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Cấu hình giao diện
st.set_page_config(page_title="Hệ thống Quan trắc AH4", layout="wide")

st.title("📈 CÔNG CỤ XỬ LÝ DỮ LIỆU")

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        # Chuẩn hóa thời gian và sắp xếp để đường không bị đứt đoạn
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    
    # Chuyển đổi các cột dữ liệu sang dạng số
    for col in df.columns:
        if col not in ['Thời gian', '_id', 'Tên khu', 'Người điều khiển', 'Trạng thái', 'Phương thức hoạt động']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Sửa lỗi đơn vị PH (nếu cần)
    if 'PH' in df.columns and df['PH'].max() > 20:
        df['PH'] = df['PH'] / 100
    return df

# 2. Sidebar tải file và chọn file
uploaded_files = st.sidebar.file_uploader("Tải file JSON vào đây", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("Chọn file muốn xem:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # --- BỘ LỌC THỜI GIAN (DÙNG SLIDER) ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 Chọn mốc thời gian")
        min_date = df['Thời gian'].min().to_pydatetime()
        max_date = df['Thời gian'].max().to_pydatetime()
        
        # Thanh trượt chọn khoảng thời gian cụ thể
        start_time, end_time = st.sidebar.slider(
            "Chọn khoảng xem:",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            format="DD/MM HH:mm"
        )
        
        # Lọc dữ liệu theo lựa chọn
        df_filtered = df[(df['Thời gian'] >= start_time) & (df['Thời gian'] <= end_time)]

        # --- CHỌN THÔNG SỐ VÀ VẼ BIỂU ĐỒ ĐƯỜNG ---
        numeric_cols = df_filtered.select_dtypes(include=['number']).columns.tolist()
        numeric_cols = [c for c in numeric_cols if c not in ['STT']] # Loại bỏ cột STT

        if numeric_cols:
            selected_metrics = st.multiselect("Chọn thông số vẽ đường:", numeric_cols, default=numeric_cols[:min(3, len(numeric_cols))])
            
            if selected_metrics:
                # Ép kiểu px.line để đảm bảo ra biểu đồ đường
                fig = px.line(
                    df_filtered, 
                    x='Thời gian', 
                    y=selected_metrics,
                    markers=True, # Hiển thị nốt tròn tại các điểm dữ liệu
                    title=f"Biểu đồ diễn biến từ {start_time.strftime('%H:%M %d/%m')} đến {end_time.strftime('%H:%M %d/%m')}",
                    template="plotly_white"
                )
                
                # Làm mượt đường và tối ưu hiển thị ngang
                fig.update_traces(line=dict(width=2))
                fig.update_layout(
                    hovermode="x unified",
                    xaxis_title="Thời gian (Timeline)",
                    yaxis_title="Giá trị đo được"
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        # Bảng dữ liệu chi tiết
        with st.expander("Xem bảng dữ liệu chi tiết trong khoảng đã chọn"):
            st.dataframe(df_filtered)
else:
    st.info("💡 Hãy kéo thả file JSON vào Sidebar bên trái.")
