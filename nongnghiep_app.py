import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Dashboard AH4 Pro", layout="wide")
st.title("📈 CỘNG CỤ PHÂN TÍCH")

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
        
        # Gộp các điểm trùng khít thời gian (giây) để tránh vạch dọc
        df = df.groupby('Thời gian').mean(numeric_only=True).reset_index()
    
    for col in df.columns:
        if col not in ['Thời gian', '_id', 'Tên khu', 'Trạng thái', 'Người điều khiển']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # Chuẩn hóa đơn vị
    if 'PH' in df.columns and df['PH'].max() > 20: df['PH'] = df['PH'] / 100
    if 'Nhiệt Độ' in df.columns and df['Nhiệt Độ'].max() > 100: df['Nhiệt Độ'] = df['Nhiệt Độ'] / 100
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # Lọc thời gian
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        st.sidebar.header("📅 Lọc thời gian")
        start_date = pd.to_datetime(st.sidebar.date_input("Từ ngày", min_dt.date()))
        end_date = pd.to_datetime(st.sidebar.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)
        
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)].copy()

        if not df_filtered.empty:
            # --- TÙY CHỈNH BIỂU ĐỒ ---
            st.markdown("---")
            c1, c2, c3 = st.columns([1, 1, 2])
            chart_choice = c1.radio("Loại biểu đồ:", ["Đường (Line)", "Cột (Bar)"], horizontal=True)
            
            # Thêm nút chọn độ thưa để làm mảnh biểu đồ nếu quá đặc
            step = c2.select_slider("Độ chi tiết (Bước nhảy):", options=[1, 2, 5, 10, 20], value=1, help="Số càng cao biểu đồ càng mảnh")
            
            draw_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT']]
            selected_metrics = c3.multiselect("Thông số:", draw_cols, default=draw_cols[:1])
            
            if selected_metrics:
                fig = go.Figure()
                # Lấy mẫu dữ liệu theo bước nhảy để giảm độ đặc nhưng vẫn giữ hình dáng
                display_df = df_filtered.iloc[::step] 
                
                for metric in selected_metrics:
                    plot_data = display_df[['Thời gian', metric]].dropna()
                    if not plot_data.empty:
                        if "Đường" in chart_choice:
                            fig.add_trace(go.Scatter(
                                x=plot_data['Thời gian'], 
                                y=plot_data[metric],
                                mode='lines', 
                                name=metric,
                                connectgaps=True,
                                line=dict(width=1) # Nét vẽ siêu mảnh
                            ))
                        else:
                            fig.add_trace(go.Bar(x=plot_data['Thời gian'], y=plot_data[metric], name=metric))
                
                fig.update_layout(
                    hovermode="x unified",
                    template="plotly_white",
                    height=600,
                    xaxis=dict(showgrid=True, title="Thời gian"),
                    yaxis=dict(showgrid=True, title="Giá trị")
                )
                st.plotly_chart(fig, use_container_width=True)

            # Bảng dữ liệu luôn hiện
            st.subheader("🔍 Chi tiết bảng dữ liệu")
            st.dataframe(df_filtered, use_container_width=True)
else:
    st.info("Kéo thả file vào sidebar.")
