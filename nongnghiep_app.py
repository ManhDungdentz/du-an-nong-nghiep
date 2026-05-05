import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Cấu hình trang Dashboard
st.set_page_config(page_title="Hệ thống Dashboard Nông nghiệp", layout="wide")

st.title("📊 Công cụ Phân tích Dữ liệu Nông nghiệp Tổng hợp")
st.markdown("Hỗ trợ: *Lịch tưới, Lịch sử nhỏ giọt AH4, Quan trắc thực địa*")

# 2. Hàm xử lý dữ liệu thông minh
def process_data(file):
    df = pd.read_json(file)
    
    # Chuẩn hóa cột Thời gian (xử lý định dạng 2025-04-14 09-31-51)
    if 'Thời gian' in df.columns:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
    
    # Chuyển các cột có giá trị số từ text sang dạng số để vẽ biểu đồ
    for col in df.columns:
        if col not in ['Thời gian', '_id', 'Tên khu', 'Người điều khiển', 'Trạng thái', 'Phương thức hoạt động']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # Xử lý đặc biệt cho pH (trong file của bạn 452 tương đương pH 4.52)
    if 'PH' in df.columns and df['PH'].max() > 14:
        df['PH'] = df['PH'] / 100
        
    return df

# 3. Giao diện tải file
uploaded_files = st.sidebar.file_uploader("Tải lên các file JSON (có thể chọn nhiều file cùng lúc)", type=['json'], accept_multiple_files=True)

if uploaded_files:
    # Gom dữ liệu từ các file vào một Dictionary
    all_data = {f.name: process_data(f) for f in uploaded_files}
    
    # Chọn file để xem dữ liệu
    selected_file = st.sidebar.selectbox("Chọn file bạn muốn xem biểu đồ:", list(all_data.keys()))
    df = all_data[selected_file]

    # --- HIỂN THỊ THEO LOẠI FILE ---
    
    # Trường hợp 1: File Quan trắc (Có chỉ số NPK, EC)
    if 'N' in df.columns or 'EC' in df.columns:
        st.subheader(f"📈 Chỉ số quan trắc: {selected_file}")
        
        # Chỉ số mới nhất
        c1, c2, c3, c4 = st.columns(4)
        latest = df.iloc[-1]
        c1.metric("Nitơ (N)", f"{latest.get('N', 0)}")
        c2.metric("Kali (K)", f"{latest.get('K', 0)}")
        c3.metric("EC (Độ dẫn điện)", f"{latest.get('EC', 0)}")
        c4.metric("pH (Độ chua)", f"{latest.get('PH', 0):.2f}")

        # Biểu đồ diễn biến
        metrics = st.multiselect("Chọn thông số cần vẽ:", 
                                 ['N', 'P', 'K', 'EC', 'PH', 'Nhiệt Độ', 'tempKK', 'humiKK'],
                                 default=['N', 'P', 'K'])
        if metrics:
            fig = px.line(df, x='Thời gian', y=metrics, markers=True, title="Biểu đồ biến động theo thời gian")
            st.plotly_chart(fig, use_container_width=True)

    # Trường hợp 2: File Lịch sử/Lịch tưới (Có lưu lượng, trạng thái)
    elif 'Lưu lượng m2/h' in df.columns:
        st.subheader(f"💧 Vận hành hệ thống: {selected_file}")
        
        col_a, col_b = st.columns([2, 1])
        with col_a:
            fig_flow = px.area(df, x='Thời gian', y='Lưu lượng m2/h', title="Biểu đồ lưu lượng tưới")
            st.plotly_chart(fig_flow, use_container_width=True)
        with col_b:
            # Thống kê ai là người điều khiển nhiều nhất
            if 'Người điều khiển' in df.columns:
                fig_user = px.pie(df, names='Người điều khiển', title="Tỷ lệ người điều khiển")
                st.plotly_chart(fig_user)

    # Xem bảng dữ liệu gốc
    with st.expander("Xem bảng dữ liệu chi tiết (Excel style)"):
        st.dataframe(df)

else:
    st.info("👈 Vui lòng kéo và thả các file JSON của bạn vào thanh bên trái để bắt đầu.")
    st.warning("Bạn có thể tải lên cùng lúc cả 3 file 'Lich nho giotj.json', 'Lịch sử nhỏ giọt AH4.json' và 'Quan trắc thực địa.json'.")
