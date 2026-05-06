import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Hệ Thống AH4 - Sửa lỗi hiển thị", layout="wide")
st.title("📊 hệ thống phân tích dữ liệu")

def process_data(file):
    try:
        df = pd.read_json(file)
    except: return pd.DataFrame()

    if 'Thời gian' in df.columns:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    
    # ÉP KIỂU SỐ TOÀN BỘ CỘT - BẤT KỂ TÊN LÀ GÌ
    for col in df.columns:
        if col != 'Thời gian':
            # Xử lý cả trường hợp số có dấu phẩy hoặc khoảng trắng
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.strip(), errors='coerce')
            
    # Gộp dữ liệu để làm mượt
    df = df.groupby('Thời gian').mean(numeric_only=True).reset_index()

    # Tự động chia 100 cho PH/Nhiệt độ nếu dữ liệu thô bị nhân 100
    for col in df.columns:
        u_col = col.upper()
        if 'PH' in u_col and df[col].max() > 20: df[col] = df[col] / 100
        if 'NHIỆT' in u_col and df[col].max() > 100: df[col] = df[col] / 100
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file đang xem:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # Tự động lấy mốc thời gian từ file (Tránh lỗi lọc sai năm dẫn đến trắng biểu đồ)
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        st.sidebar.header("📅 Lọc thời gian")
        start_date = pd.to_datetime(st.sidebar.date_input("Từ ngày", min_dt.date()))
        end_date = pd.to_datetime(st.sidebar.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)
        
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)].copy()

        if not df_filtered.empty:
            # Lấy tất cả cột có chứa dữ liệu số (Trừ cột STT, index)
            numeric_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT', 'index']]
            
            # --- HIỂN THỊ METRICS ---
            st.subheader("📋 Các thông số tìm thấy trong file")
            m_cols = st.columns(4)
            for i, col_name in enumerate(numeric_cols[:12]): # Hiện tối đa 12 cái
                val = df_filtered[col_name].dropna()
                if not val.empty:
                    m_cols[i % 4].metric(label=col_name, value=f"{val.iloc[-1]:.2f}")

            # --- BIỂU ĐỒ ---
            st.markdown("---")
            c1, c2 = st.columns([1, 2])
            chart_type = c1.radio("Kiểu biểu đồ:", ["Đường (Line)", "Cột (Bar)"], horizontal=True)
            step = c1.select_slider("Độ mảnh (Bước nhảy):", options=[1, 2, 5, 10, 50], value=1)
            
            # Ép buộc hiển thị tất cả các cột số để người dùng chọn
            selected_metrics = c2.multiselect("Bấm vào đây để chọn thêm thông số vẽ (PH, EC, N, P, K...):", 
                                              numeric_cols, 
                                              default=numeric_cols[:1])
            
            if selected_metrics:
                fig = go.Figure()
                display_df = df_filtered.iloc[::step]
                for m in selected_metrics:
                    p_data = display_df[['Thời gian', m]].dropna()
                    if not p_data.empty:
                        fig.add_trace(go.Scatter(x=p_data['Thời gian'], y=p_data[m], mode='lines' if "Đường" in chart_type else 'markers', name=m))
                
                fig.update_layout(hovermode="x unified", template="plotly_white", height=500)
                st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("🔍 Xem bảng dữ liệu thô để đối chiếu")
            st.dataframe(df_filtered, use_container_width=True)
else:
    st.info("Hãy tải file lên.")
