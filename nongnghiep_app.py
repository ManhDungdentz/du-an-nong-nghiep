import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Dashboard AH4 Pro", layout="wide")
st.title("📊 Hệ Thống Dữ Liệu ")

def process_data(file):
    try:
        df = pd.read_json(file)
    except: return pd.DataFrame()

    if 'Thời gian' in df.columns:
        df['Thời gian'] = pd.to_datetime(df['Thời gian'].astype(str).str.replace('-', ' ', n=2).str.replace('-', ':'), errors='coerce')
        df = df.dropna(subset=['Thời gian']).sort_values('Thời gian')
    else:
        return pd.DataFrame()
    
    # --- CƠ CHẾ BỐC TÁCH SỐ XUYÊN QUA CHỮ ---
    for col in df.columns:
        if col != 'Thời gian':
            # 1. Biến tất cả thành chữ. 2. Đổi phẩy thành chấm. 
            # 3. Dùng Regex moi con số đầu tiên tìm thấy ra khỏi chữ.
            cleaned_str = df[col].astype(str).str.replace(',', '.')
            extracted_num = cleaned_str.str.extract(r'([-+]?(?:\d+\.\d+|\d+))')[0]
            df[col] = pd.to_numeric(extracted_num, errors='coerce')
            
    # Gộp dữ liệu trùng giây
    df = df.groupby('Thời gian').mean(numeric_only=True).reset_index()

    # Tự động sửa đơn vị
    for col in df.columns:
        u_col = col.upper()
        if 'PH' in u_col and df[col].max() > 20: df[col] = df[col] / 100
        if ('NHIỆT' in u_col or 'TEMP' in u_col) and df[col].max() > 100: df[col] = df[col] / 100
    return df

uploaded_files = st.sidebar.file_uploader("Tải file JSON", type=['json'], accept_multiple_files=True)

if uploaded_files:
    all_data = {f.name: process_data(f) for f in uploaded_files}
    selected_file = st.sidebar.selectbox("📁 Chọn file đang xem:", list(all_data.keys()))
    df = all_data[selected_file]

    if not df.empty:
        min_dt, max_dt = df['Thời gian'].min(), df['Thời gian'].max()
        st.sidebar.header("📅 Lọc thời gian")
        start_date = pd.to_datetime(st.sidebar.date_input("Từ ngày", min_dt.date()))
        end_date = pd.to_datetime(st.sidebar.date_input("Đến ngày", max_dt.date())) + timedelta(days=1)
        
        df_filtered = df[(df['Thời gian'] >= start_date) & (df['Thời gian'] <= end_date)].copy()

        if not df_filtered.empty:
            num_cols = [c for c in df_filtered.select_dtypes(include=['number']).columns if c not in ['STT', 'index']]
            
            # --- HIỂN THỊ METRICS ---
            st.subheader("📋 Thông số tìm thấy")
            if num_cols:
                m_cols = st.columns(4)
                for i, col_name in enumerate(num_cols[:12]):
                    val = df_filtered[col_name].dropna()
                    if not val.empty:
                        m_cols[i % 4].metric(label=col_name, value=f"{val.iloc[-1]:.2f}")

            # --- BIỂU ĐỒ ---
            st.markdown("---")
            c1, c2 = st.columns([1, 2])
            chart_type = c1.radio("Kiểu vẽ:", ["Đường (Line)", "Cột (Bar)"], horizontal=True)
            step = c1.select_slider("Độ mảnh (Bước nhảy):", options=[1, 2, 5, 10, 50], value=1)
            
            selected_metrics = c2.multiselect("Bấm vào đây để THÊM thông số vẽ:", num_cols, default=num_cols[:min(3, len(num_cols))])
            
            if selected_metrics:
                fig = go.Figure()
                display_df = df_filtered.iloc[::step]
                
                for m in selected_metrics:
                    p_data = display_df[['Thời gian', m]].dropna()
                    
                    if not p_data.empty:
                        # ĐÃ KHÔI PHỤC LẠI NÚT CHỌN CỘT/ĐƯỜNG
                        if "Đường" in chart_type:
                            fig.add_trace(go.Scatter(
                                x=p_data['Thời gian'], 
                                y=p_data[m], 
                                mode='lines+markers', # LUÔN CÓ ĐIỂM CHẤM (Để 1 ngày gửi 1 dữ liệu vẫn hiện ra)
                                name=m,
                                connectgaps=True,
                                line=dict(width=1.5)
                            ))
                        else:
                            fig.add_trace(go.Bar(
                                x=p_data['Thời gian'], 
                                y=p_data[m], 
                                name=m
                            ))
                    else:
                        # THÔNG BÁO NẾU CỘT TRỐNG TRƠN
                        st.warning(f"⚠️ Thông số '{m}' KHÔNG CÓ DỮ LIỆU. Thiết bị của bạn không gửi thông số này hoặc đang bị null trong file.")
                
                fig.update_layout(hovermode="x unified", template="plotly_white", height=550)
                st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("🔍 Bảng dữ liệu gốc")
            st.dataframe(df_filtered, use_container_width=True)
        else:
            st.error("Khoảng thời gian này không có dữ liệu. Hãy chỉnh lại 'Từ ngày' ở cột bên trái.")
else:
    st.info("Hãy tải file JSON lên sidebar.")
