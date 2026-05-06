import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Hệ Thống AH4 - Full Charts", layout="wide")
st.title("📊 hệ thống phân tích dữ liệu")

def process_data(file):
    try:
        df = pd.read_json(file)
    except: return pd.DataFrame()

    if 'Thời gian' in df.columns:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    
    # Ép kiểu số cho TẤT CẢ các cột (đặc biệt là TBPH, TBEC, Lưu lượng)
    for col in df.columns:
        if col != 'Thời gian':
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
            
    # Gộp dữ liệu trùng để biểu đồ mượt hơn
    df = df.groupby('Thời gian').mean(numeric_only=True).reset_index()

    # Tự động sửa đơn vị PH/Nhiệt độ (nếu số quá lớn thì chia 100)
    for col in df.columns:
        u_col = col.upper()
        if 'PH' in u_col and df[col].max() > 20: df[col] = df[col] / 100
        if 'NHIỆT' in u_col and df[col].max() > 100: df[col] = df[col] / 100
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # Lọc thời gian: Mặc định lấy toàn bộ dữ liệu trong file
        st.sidebar.header("📅 Lọc thời gian")
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        start_date = pd.to_datetime(st.sidebar.date_input("Từ ngày", min_dt.date()))
        end_date = pd.to_datetime(st.sidebar.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)
        
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)].copy()

        if not df_filtered.empty:
            # --- HIỂN THỊ METRICS ---
            st.subheader("📋 Thông số đo được")
            # Tìm tất cả các cột có số (loại bỏ STT)
            num_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT', 'index']]
            
            if num_cols:
                m_cols = st.columns(min(len(num_cols), 4))
                for i, col_name in enumerate(num_cols[:8]):
                    val = df_filtered[col_name].dropna()
                    if not val.empty:
                        m_cols[i % 4].metric(label=col_name, value=f"{val.iloc[-1]:.2f}")

            # --- BIỂU ĐỒ (SỬA LỖI CHỈ HIỆN LƯU LƯỢNG) ---
            st.markdown("---")
            c1, c2 = st.columns([1, 2])
            chart_type = c1.radio("Kiểu biểu đồ:", ["Đường (Line)", "Cột (Bar)"], horizontal=True)
            step = c1.select_slider("Độ mảnh:", options=[1, 2, 5, 10, 50], value=1)
            
            # QUAN TRỌNG: Mặc định chọn TBPH và TBEC nếu có để người dùng thấy ngay
            default_selection = [c for c in num_cols if any(k in c.upper() for k in ['TBPH', 'TBEC', 'PH', 'EC'])]
            if not default_selection: default_selection = num_cols[:1]

            selected_metrics = c2.multiselect("Chọn thông số vẽ biểu đồ:", num_cols, default=default_selection)
            
            if selected_metrics:
                fig = go.Figure()
                display_df = df_filtered.iloc[::step]
                for m in selected_metrics:
                    p_data = display_df[['Thời gian', m]].dropna()
                    if not p_data.empty:
                        if "Đường" in chart_type:
                            fig.add_trace(go.Scatter(x=p_data['Thời gian'], y=p_data[m], mode='lines', name=m, line=dict(width=1.5)))
                        else:
                            fig.add_trace(go.Bar(x=p_data['Thời gian'], y=p_data[m], name=m))
                
                fig.update_layout(hovermode="x unified", template="plotly_white", height=500)
                st.plotly_chart(fig, use_container_width=True)
            
            # Hiện bảng để kiểm tra dữ liệu
            st.subheader("🔍 Chi tiết dữ liệu")
            st.dataframe(df_filtered, use_container_width=True)
else:
    st.info("Kéo thả file JSON vào sidebar.")
