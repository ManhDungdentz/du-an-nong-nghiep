import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Dashboard AH4 Full Options", layout="wide")
st.title("📊 CÔNG CỤ PHÂN TÍCH DỮ LIỆU")

def clean_numeric(x):
    try:
        if isinstance(x, str):
            x = x.replace(',', '.')
        return pd.to_numeric(x, errors='coerce')
    except:
        return None

def process_data(file):
    df = pd.read_json(file)
    if 'Thời gian' in df.columns:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    
    # Ép kiểu số cho tất cả cột để không sót thông số nào (N, P, K, AS, Nhiệt độ...)
    for col in df.columns:
        if col != 'Thời gian':
            df[col] = df[col].apply(clean_numeric)
            
    # Gộp dữ liệu trùng giây
    df = df.groupby('Thời gian').mean(numeric_only=True).reset_index()

    # Tự động sửa đơn vị PH/Nhiệt độ nếu dữ liệu thô bị nhân 100
    for col in df.columns:
        u_col = col.upper()
        if 'PH' in u_col and df[col].max() > 20: df[col] = df[col] / 100
        if ('NHIỆT' in u_col or 'TEMP' in u_col) and df[col].max() > 100: df[col] = df[col] / 100
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        # Bộ lọc thời gian
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        st.sidebar.header("📅 Lọc thời gian")
        start_date = pd.to_datetime(st.sidebar.date_input("Từ ngày", min_dt.date()))
        end_date = pd.to_datetime(st.sidebar.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)
        
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)].copy()

        if not df_filtered.empty:
            # --- HIỂN THỊ METRICS (QUÉT TẤT CẢ THÔNG SỐ CÓ THỂ) ---
            st.subheader("📋 Thông số đo được")
            
            # Danh sách các nhóm từ khóa để hiển thị lên bảng Metric
            target_groups = {
                "Nhiệt Độ": ["Nhiệt Độ", "Temp"],
                "Độ Ẩm": ["Độ ẩm", "Humi"],
                "Ánh Sáng": ["AS", "Light"],
                "PH": ["PH", "TBPH"],
                "EC": ["EC", "TBEC"],
                "Lưu Lượng": ["Lưu lượng", "m2/h"],
                "Nitơ (N)": ["N", "Nitrogen"],
                "Phốt pho (P)": ["P", "Phosphorus"],
                "Kali (K)": ["K", "Potassium"]
            }

            # Tìm và hiển thị các cột khớp với nhóm trên
            found_cols = []
            for label, keys in target_groups.items():
                for col in df_filtered.columns:
                    if any(k.upper() in col.upper() for k in keys):
                        found_cols.append((label, col))
                        break # Chỉ lấy 1 cột đại diện cho mỗi nhóm

            if found_cols:
                m_cols = st.columns(min(len(found_cols), 4))
                for i, (label, col_name) in enumerate(found_cols):
                    val = df_filtered[col_name].dropna()
                    if not val.empty:
                        m_cols[i % 4].metric(label=f"{label}", value=f"{val.iloc[-1]:.2f}")

            # --- TÙY CHỈNH BIỂU ĐỒ ---
            st.markdown("---")
            c1, c2 = st.columns([1, 2])
            chart_type = c1.radio("Loại biểu đồ:", ["Đường (Line)", "Cột (Bar)"], horizontal=True)
            step = c1.select_slider("Độ chi tiết (Bước nhảy):", options=[1, 2, 5, 10, 50], value=1)
            
            # Lấy tất cả các cột có kiểu số (trừ STT) để cho người dùng chọn vẽ
            all_numeric = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT']]
            selected_metrics = c2.multiselect("Chọn thông số muốn xem trên biểu đồ:", all_numeric, default=all_numeric[:2] if len(all_numeric)>1 else all_numeric)
            
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
                fig.update_layout(hovermode="x unified", template="plotly_white", height=500, xaxis_title="Thời gian", yaxis_title="Giá trị")
                st.plotly_chart(fig, use_container_width=True)

            # --- BẢNG DỮ LIỆU GỐC ---
            st.subheader("🔍 Toàn bộ bảng dữ liệu chi tiết")
            st.dataframe(df_filtered, use_container_width=True)
        else:
            st.warning("Không có dữ liệu trong khoảng thời gian này.")
else:
    st.info("Kéo thả file JSON vào sidebar để bắt đầu.")
