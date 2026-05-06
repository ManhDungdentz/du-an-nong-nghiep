import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Cấu hình trang
st.set_page_config(page_title="Hệ thống Dashboard Nông nghiệp", layout="wide")

st.title("📊 Phân Tích Dữ Liệu & Lọc Thời Gian")

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        # Chuyển đổi thời gian và sắp xếp
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    
    for col in df.columns:
        if col not in ['Thời gian', '_id', 'Tên khu', 'Người điều khiển', 'Trạng thái', 'Phương thức hoạt động']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    if 'PH' in df.columns and df['PH'].max() > 20:
        df['PH'] = df['PH'] / 100
    return df

# 2. Tải file
uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("Chọn file:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # --- BỘ LỌC THỜI GIAN ---
        st.sidebar.header("📅 Lọc thời gian")
        min_date = df['Thời gian'].min().to_pydatetime()
        max_date = df['Thời gian'].max().to_pydatetime()
        
        # Chọn khoảng thời gian bằng Slider
        selected_range = st.sidebar.slider(
            "Chọn khoảng thời gian:",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            format="DD/MM HH:mm"
        )
        
        # Lọc dữ liệu theo thời gian đã chọn
        df_filtered = df[(df['Thời gian'] >= selected_range[0]) & (df['Thời gian'] <= selected_range[1])]

        # --- HIỂN THỊ BIỂU ĐỒ ---
        numeric_cols = df_filtered.select_dtypes(include=['number']).columns.tolist()
        numeric_cols = [c for c in numeric_cols if c not in ['STT']]

        if numeric_cols:
            selected_metrics = st.multiselect("Chọn thông số:", numeric_cols, default=numeric_cols[:min(3, len(numeric_cols))])
            
            if selected_metrics:
                # Biểu đồ đường (Line chart)
                fig = px.line(
                    df_filtered, 
                    x='Thời gian', 
                    y=selected_metrics,
                    markers=True,
                    title=f"Biểu đồ từ {selected_range[0].strftime('%d/%m %H:%M')} đến {selected_range[1].strftime('%d/%m %H:%M')}",
                    template="plotly_white"
                )
                
                # Cấu hình để biểu đồ hiển thị rõ ràng hơn
                fig.update_layout(
                    hovermode="x unified",
                    xaxis_title="Thời gian (Giờ:Phút)",
                    yaxis_title="Giá trị"
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        # Hiển thị bảng dữ liệu đã lọc
        with st.expander("Xem bảng dữ liệu đã lọc"):
            st.write(f"Đang hiển thị {len(df_filtered)} dòng dữ liệu.")
            st.dataframe(df_filtered)
else:
    st.info("Vui lòng tải file lên.")
