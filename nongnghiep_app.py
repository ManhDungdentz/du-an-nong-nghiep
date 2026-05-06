import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Hệ Thống AH4 - Fix Biểu Đồ", layout="wide")
st.title("📈 Hệ Thống Phân Tích Dữ Liệu")

def process_data(file):
    try:
        df = pd.read_json(file)
    except: return pd.DataFrame()

    if 'Thời gian' in df.columns:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    
    # --- CHIẾN THUẬT ÉP SỐ MẠNH ---
    for col in df.columns:
        if col != 'Thời gian':
            # Loại bỏ khoảng trắng, đổi dấu phẩy thành dấu chấm, ép về số
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.strip(), errors='coerce')
            
    # Gộp dữ liệu để tránh bị trùng lặp gây lỗi biểu đồ
    df = df.groupby('Thời gian').mean(numeric_only=True).reset_index()

    # Sửa đơn vị tự động cho PH/Nhiệt độ
    for col in df.columns:
        u_col = col.upper()
        if 'PH' in u_col and df[col].max() > 20: df[col] = df[col] / 100
        if ('NHIỆT' in u_col or 'TEMP' in u_col) and df[col].max() > 100: df[col] = df[col] / 100
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file dữ liệu:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # Tự động khớp thời gian theo file
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        st.sidebar.header("📅 Lọc thời gian")
        start_date = pd.to_datetime(st.sidebar.date_input("Từ ngày", min_dt.date()))
        end_date = pd.to_datetime(st.sidebar.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)
        
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)].copy()

        if not df_filtered.empty:
            # Lấy tất cả cột có dữ liệu thực (loại bỏ cột toàn NaN hoặc 0)
            numeric_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT', 'index']]
            
            # --- HIỂN THỊ METRICS ---
            st.subheader("📋 Thông số khả dụng")
            m_cols = st.columns(4)
            for i, col_name in enumerate(numeric_cols[:12]):
                val = df_filtered[col_name].dropna()
                if not val.empty:
                    m_cols[i % 4].metric(label=col_name, value=f"{val.iloc[-1]:.2f}")

            # --- BIỂU ĐỒ ---
            st.markdown("---")
            c1, c2 = st.columns([1, 2])
            chart_type = c1.radio("Kiểu vẽ:", ["Đường (Line)", "Cột (Bar)"], horizontal=True)
            step = c1.select_slider("Độ chi tiết:", options=[1, 2, 5, 10, 50], value=1)
            
            # QUAN TRỌNG: Cho phép chọn bất kỳ cột nào có trong file
            selected_metrics = c2.multiselect("Bấm vào đây để chọn thông số (Nhiệt độ, Độ ẩm, N, P, K...):", 
                                              numeric_cols, 
                                              default=numeric_cols[:2] if len(numeric_cols) > 1 else numeric_cols)
            
            if selected_metrics:
                fig = go.Figure()
                display_df = df_filtered.iloc[::step]
                for m in selected_metrics:
                    p_data = display_df[['Thời gian', m]].dropna()
                    # Bỏ qua các hàng có giá trị = 0 nếu nó làm bẹt biểu đồ (tùy chọn)
                    if not p_data.empty:
                        fig.add_trace(go.Scatter(
                            x=p_data['Thời gian'], 
                            y=p_data[m], 
                            mode='lines+markers' if len(p_data) < 100 else 'lines',
                            name=m,
                            connectgaps=True # Nối các điểm bị thiếu dữ liệu
                        ))
                
                fig.update_layout(hovermode="x unified", template="plotly_white", height=600)
                st.plotly_chart(fig, use_container_width=True)
            
            # Bảng dữ liệu để kiểm tra xem cột đó có thực sự có số hay không
            st.subheader("🔍 Kiểm tra bảng dữ liệu thô")
            st.dataframe(df_filtered, use_container_width=True)
        else:
            st.warning("Không có dữ liệu trong khoảng thời gian này. Kiểm tra lại năm trong file!")
else:
    st.info("Kéo thả file JSON vào sidebar.")
