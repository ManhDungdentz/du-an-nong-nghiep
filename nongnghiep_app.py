import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Cấu hình trang
st.set_page_config(page_title="Hệ thống Dashboard Nông nghiệp", layout="wide")

st.title("📊 Công cụ Phân tích Dữ liệu Nông nghiệp (Bản sửa lỗi)")

# 2. Hàm xử lý dữ liệu thông minh - ĐÃ SỬA LỖI VALUEERROR
def process_data(file):
    df = pd.read_json(file)
    
    # Chuẩn hóa cột Thời gian
    if 'Thời gian' in df.columns:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.sort_values('Thời gian')
    
    # Chuyển đổi số và xử lý giá trị rỗng (quan trọng để tránh lỗi vẽ biểu đồ)
    for col in df.columns:
        if col not in ['Thời gian', '_id', 'Tên khu', 'Người điều khiển', 'Trạng thái', 'Phương thức hoạt động']:
            # Chuyển về số, các giá trị rỗng "" hoặc text sẽ thành NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # Xử lý đặc biệt cho pH (nếu là số nguyên lớn thì chia 100)
    if 'PH' in df.columns:
        if df['PH'].max() > 20:
            df['PH'] = df['PH'] / 100
        
    return df

# 3. Giao diện chính
uploaded_files = st.sidebar.file_uploader("Tải lên các file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("Chọn file muốn xem:", list(all_data.keys()))
    df = all_data[selected_file]

    # Kiểm tra xem có dữ liệu không
    if df.empty:
        st.error("File này không có dữ liệu để hiển thị.")
    else:
        # Lấy danh sách các cột là số để vẽ biểu đồ
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        # Loại bỏ các cột không cần thiết khỏi danh sách vẽ
        numeric_cols = [c for c in numeric_cols if c not in ['STT']]

        st.subheader(f"📁 Dữ liệu: {selected_file}")

        # Vẽ biểu đồ động dựa trên các cột số tìm được
        if numeric_cols:
            selected_metrics = st.multiselect(
                "Chọn thông số muốn vẽ biểu đồ:", 
                numeric_cols, 
                default=numeric_cols[:min(3, len(numeric_cols))]
            )

            if selected_metrics:
                # LOẠI BỎ CÁC DÒNG RỖNG trước khi vẽ để tránh lỗi ValueError
                plot_df = df.dropna(subset=selected_metrics, how='all')
                
                if not plot_df.empty:
                    fig = px.line(plot_df, x='Thời gian', y=selected_metrics, 
                                 markers=True, title="Biến động chỉ số")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Các cột bạn chọn không có dữ liệu số để vẽ biểu đồ.")
        
        # Hiển thị bảng dữ liệu
        with st.expander("Xem bảng dữ liệu chi tiết"):
            st.dataframe(df)
else:
    st.info("Vui lòng tải file JSON lên để bắt đầu.")
